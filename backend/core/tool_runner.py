"""ReAct execution loop — agent reasons, calls tools, observes results, repeats.

Uses native function calling (tools API) for reliable tool invocation,
with aggressive text-based parsing as fallback for models that don't support
native tool calling (e.g., OpenRouter free tier models).
"""
import json
import logging
import re

from core.llm import chat_completion, chat_completion_with_tools
from core.tools import Tool, format_tools_for_prompt, format_tools_for_api

logger = logging.getLogger(__name__)

TOOL_USE_PROMPT = """You have access to the following tools:
{tool_descriptions}

To use a tool, respond with EXACTLY this JSON format on its own line:
{{"tool": "tool_name", "args": {{"param1": "value1"}}}}

After receiving tool results, continue reasoning. When you have a final answer, respond normally without any tool calls.

IMPORTANT: Only call one tool at a time. Wait for results before calling another."""


async def run_agent_with_tools(
    system_prompt: str,
    user_message: str,
    tools: list[Tool],
    max_iterations: int = 5,
    model: str = "llama-3.3-70b-versatile",
    collect_results: bool = False,
    max_tokens: int = 1500,
    user_id=None,
    db=None,
    nudge_message: str | None = None,
) -> str | tuple[str, list[dict]]:
    """ReAct loop using native function calling API.

    The LLM is given tools via the API's tools parameter. When it calls a tool,
    we execute it and feed the result back. This is more reliable than text-based
    JSON parsing because the API guarantees structured tool call output.

    Falls back to aggressive text-based parsing if native function calling
    isn't available or the model outputs tool calls as text.

    Args:
        collect_results: If True, returns (response_text, tool_results_list)
        max_tokens: Max tokens for LLM responses (increase for agents with complex tool args)
        nudge_message: Custom nudge message when model fails to call tools
    """
    tool_names = [t.name for t in tools]
    api_tools = format_tools_for_api(tools)
    messages = [{"role": "user", "content": user_message}]
    tool_results = []
    last_text_response = ""

    for iteration in range(max_iterations):
        result = await chat_completion_with_tools(
            system_prompt=system_prompt,
            messages=messages,
            tools=api_tools,
            model=model,
            max_tokens=max_tokens,
            temperature=0.3,
            user_id=user_id,
            db=db,
        )

        content = result.get("content") or ""
        tool_calls = result.get("tool_calls", [])

        logger.info(
            "ReAct iteration %d — content_len=%d, tool_calls=%d, first_200: %s",
            iteration, len(content), len(tool_calls),
            content[:200].replace("\n", "\\n") if content else "(none)"
        )

        # If no tool calls from native API, try text-based fallback parsing
        if not tool_calls and content:
            parsed = _extract_tool_call(content, tool_names)
            if parsed:
                tool_name, args = parsed
                tool_calls = [{"id": f"text_{iteration}", "name": tool_name, "arguments": args}]
                logger.info("ReAct iteration %d — found tool call via text parsing: %s", iteration, tool_name)

        # No tool calls at all — this is the final answer
        if not tool_calls:
            # If no tools have been used yet, nudge to actually use tools (up to 2 attempts)
            if iteration <= 1 and not tool_results:
                logger.warning("ReAct iteration %d — no tool call, nudging (attempt %d)", iteration, iteration + 1)
                messages.append({"role": "assistant", "content": content})
                nudge = nudge_message or (
                    "STOP. You are NOT using your tools. Do NOT write text describing what tools do. "
                    "You MUST actually invoke a tool function right now. "
                    f"Available tools: {tool_names}. "
                    "Respond ONLY with a JSON tool call like: "
                    '{"tool": "' + tool_names[0] + '", "args": {...}} '
                    "DO IT NOW."
                )
                messages.append({"role": "user", "content": nudge})
                continue

            # If we searched but never drafted, and the user wants a draft, nudge to draft
            has_search = any("emails" in str(tr.get("result", "")).lower() or "subject" in str(tr.get("result", "")).lower() for tr in tool_results)
            has_draft = any(tr.get("result", {}).get("status") == "draft_created" for tr in tool_results if isinstance(tr.get("result"), dict))
            if has_search and not has_draft and "draft" in user_message.lower() and iteration <= 3:
                logger.warning("ReAct iteration %d — searched but didn't draft, nudging to call draft_reply", iteration)
                messages.append({"role": "assistant", "content": content})
                messages.append({"role": "user", "content": "You searched emails but did NOT create a draft. You MUST now call draft_reply or search_and_draft_reply to actually create the draft in Gmail. DO IT NOW."})
                continue

            last_text_response = content
            logger.info("ReAct iteration %d — no tool call, returning final answer", iteration)
            if collect_results:
                return content, tool_results
            return content

        # Process tool calls (usually just one)
        assistant_msg = {"role": "assistant", "content": content or ""}
        if tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.get("id", f"call_{iteration}_{i}"),
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": json.dumps(tc["arguments"]),
                    },
                }
                for i, tc in enumerate(tool_calls)
            ]
        messages.append(assistant_msg)

        for tc in tool_calls:
            tool_name = tc["name"]
            args = tc["arguments"]
            tool_call_id = tc.get("id", f"call_{iteration}")

            tool = next((t for t in tools if t.name == tool_name), None)
            if tool is None:
                error_msg = f"Unknown tool '{tool_name}'. Available: {tool_names}"
                logger.warning("ReAct: %s", error_msg)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": json.dumps({"error": error_msg}),
                })
                continue

            # Execute tool
            try:
                logger.info("ReAct: executing %s with args keys=%s", tool_name, list(args.keys()))
                tool_result = await tool.func(**args)
                result_str = json.dumps(tool_result) if isinstance(tool_result, (dict, list)) else str(tool_result)
                if isinstance(tool_result, dict):
                    tool_results.append({"tool": tool_name, "result": tool_result})
                logger.info("ReAct: %s succeeded, result keys=%s",
                           tool_name, list(tool_result.keys()) if isinstance(tool_result, dict) else "non-dict")
            except Exception as e:
                result_str = json.dumps({"error": str(e)})
                logger.warning("Tool %s failed: %s", tool_name, e)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": result_str,
            })

    # Max iterations reached
    logger.warning("ReAct loop hit max iterations (%d)", max_iterations)
    if collect_results:
        return last_text_response or content, tool_results
    return last_text_response or content


def _extract_tool_call(text: str, available_tools: list[str] | None = None):
    """Extract a tool call from LLM response text.

    Handles ALL common formats models use when they don't use native tool calling:
    1. JSON code blocks: ```json {"tool": ..., "args": ...} ```
    2. Inline JSON: {"tool": ..., "args": ...}
    3. XML-style: <tool_call>tool_name\n<arg>value</arg></tool_call>
    4. Function-call syntax: tool_name(arg1="val1", arg2="val2")
    5. Embedded JSON with nested braces
    """
    if not available_tools:
        available_tools = []

    # === Strategy 1: JSON code blocks ===
    for match in re.finditer(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL):
        try:
            parsed = json.loads(match.group(1).strip())
            if "tool" in parsed and "args" in parsed:
                return parsed["tool"], parsed["args"]
            # Some models use "name" + "arguments" format
            if "name" in parsed and "arguments" in parsed:
                return parsed["name"], parsed["arguments"]
        except json.JSONDecodeError:
            continue

    # === Strategy 2: Line-by-line JSON ===
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("{") and ('"tool"' in line or '"name"' in line):
            try:
                parsed = json.loads(line)
                if "tool" in parsed and "args" in parsed:
                    return parsed["tool"], parsed["args"]
                if "name" in parsed and "arguments" in parsed:
                    return parsed["name"], parsed["arguments"]
            except json.JSONDecodeError:
                continue

    # === Strategy 3: XML-style tool calls ===
    # Handles: <tool_call>tool_name\n<arg_key>key</arg_key>\n<arg_value>value</arg_value></tool_call>
    # Also: <tool_call>\ntool_name(args)\n</tool_call>
    xml_match = re.search(r'<tool_call>\s*(.*?)\s*</tool_call>', text, re.DOTALL)
    if xml_match:
        xml_content = xml_match.group(1).strip()

        # Try to find tool name as first word/line
        lines = [l.strip() for l in xml_content.split("\n") if l.strip()]
        if lines:
            # Check if first line is a tool name
            potential_tool = lines[0].split("(")[0].strip()
            if potential_tool in available_tools:
                # Parse XML-style args: <arg_key>key</arg_key>\n<arg_value>value</arg_value>
                args = {}
                arg_keys = re.findall(r'<arg_key>(.*?)</arg_key>', xml_content)
                arg_values = re.findall(r'<arg_value>(.*?)</arg_value>', xml_content, re.DOTALL)

                if arg_keys and arg_values:
                    # Paired key-value format
                    for k, v in zip(arg_keys, arg_values):
                        args[k.strip()] = v.strip()
                else:
                    # Try key=value or key: value in remaining lines
                    for line in lines[1:]:
                        kv = re.match(r'(\w+)\s*[=:]\s*(.+)', line)
                        if kv:
                            args[kv.group(1)] = kv.group(2).strip().strip('"\'')

                return potential_tool, args

    # === Strategy 4: Embedded JSON with nested braces ===
    for match in re.finditer(r'\{[^{}]*"tool"\s*:\s*"[^"]+"\s*,\s*"args"\s*:\s*\{', text):
        start = match.start()
        depth = 0
        for i in range(start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    try:
                        parsed = json.loads(text[start:i + 1])
                        if "tool" in parsed and "args" in parsed:
                            return parsed["tool"], parsed["args"]
                    except json.JSONDecodeError:
                        break

    # === Strategy 5: Entire response as JSON ===
    try:
        parsed = json.loads(text.strip())
        if "tool" in parsed and "args" in parsed:
            return parsed["tool"], parsed["args"]
        if "name" in parsed and "arguments" in parsed:
            return parsed["name"], parsed["arguments"]
    except json.JSONDecodeError:
        pass

    # === Strategy 6: Generic function-call syntax for ANY registered tool ===
    # Matches: tool_name(key="value", key2="value2") or tool_name("positional")
    if available_tools:
        # Sort by length descending so longer names match first (e.g., search_and_draft_reply before search_emails)
        sorted_tools = sorted(available_tools, key=len, reverse=True)
        pattern = r'(' + '|'.join(re.escape(t) for t in sorted_tools) + r')\s*\('
        func_match = re.search(pattern, text)

        if func_match:
            tool_name = func_match.group(1)
            start = func_match.end() - 1  # opening paren
            depth = 0
            end = start
            for i in range(start, min(start + 2000, len(text))):
                if text[i] == '(':
                    depth += 1
                elif text[i] == ')':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            args_text = text[start + 1:end - 1].strip()

            args = _parse_function_args(args_text)
            if args is not None:
                logger.info("Parsed function-call syntax: %s(%s)", tool_name, list(args.keys()) if args else "empty")
                return tool_name, args

    # === Strategy 7: Look for tool names mentioned with structured args nearby ===
    if available_tools:
        for tool_name in available_tools:
            if tool_name in text:
                # Look for JSON-like args after the tool name mention
                after_tool = text[text.index(tool_name) + len(tool_name):]
                json_match = re.search(r'\{[^{}]+\}', after_tool[:500])
                if json_match:
                    try:
                        args = json.loads(json_match.group(0))
                        if isinstance(args, dict) and args:
                            logger.info("Parsed tool name + nearby JSON: %s", tool_name)
                            return tool_name, args
                    except json.JSONDecodeError:
                        pass

    return None


def _parse_function_args(args_text: str) -> dict | None:
    """Parse function arguments from text like: key="value", key2="value2" or "positional"."""
    if not args_text:
        return {}

    args = {}

    # Try as JSON first (some models write tool_name({"key": "val"}))
    args_text_stripped = args_text.strip()
    if args_text_stripped.startswith("{"):
        try:
            return json.loads(args_text_stripped)
        except json.JSONDecodeError:
            pass

    # Try keyword arguments: key="value" or key='value'
    kw_matches = re.findall(
        r'(\w+)\s*=\s*"((?:[^"\\]|\\.)*)"|(\w+)\s*=\s*\'((?:[^\'\\]|\\.)*)\'',
        args_text
    )
    if kw_matches:
        for m in kw_matches:
            if m[0]:
                args[m[0]] = m[1].replace('\\n', '\n').replace('\\"', '"')
            elif m[2]:
                args[m[2]] = m[3].replace('\\n', '\n').replace("\\'", "'")
        return args

    # Try keyword with unquoted values: key=value
    kw_unquoted = re.findall(r'(\w+)\s*=\s*([^,\)]+)', args_text)
    if kw_unquoted:
        for k, v in kw_unquoted:
            v = v.strip().strip('"\'')
            # Try to parse numbers/bools
            if v.lower() == 'true':
                args[k] = True
            elif v.lower() == 'false':
                args[k] = False
            elif re.match(r'^-?\d+$', v):
                args[k] = int(v)
            elif re.match(r'^-?\d+\.\d+$', v):
                args[k] = float(v)
            else:
                args[k] = v
        if args:
            return args

    # Positional quoted strings
    positional = re.findall(r'"((?:[^"\\]|\\.)*)"|\'((?:[^\'\\]|\\.)*)\'', args_text)
    if positional:
        values = [p[0] or p[1] for p in positional]
        # Return as a generic args dict with indexed keys
        if len(values) == 1:
            return {"query": values[0]}  # Most common single-arg case
        return {f"arg_{i}": v for i, v in enumerate(values)}

    return {}
