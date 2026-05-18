"""ReAct execution loop — agent reasons, calls tools, observes results, repeats.

Uses native function calling (tools API) for reliable tool invocation,
with text-based JSON parsing as fallback.
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

    Falls back to text-based parsing if native function calling isn't available.

    Args:
        collect_results: If True, returns (response_text, tool_results_list)
        max_tokens: Max tokens for LLM responses (increase for agents with complex tool args)
    """
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
            parsed = _extract_tool_call(content)
            if parsed:
                tool_name, args = parsed
                tool_calls = [{"id": f"text_{iteration}", "name": tool_name, "arguments": args}]
                logger.info("ReAct iteration %d — found tool call via text parsing: %s", iteration, tool_name)

        # No tool calls at all — this is the final answer
        if not tool_calls:
            # If no tools have been used yet, nudge to actually use tools (up to 2 attempts)
            # This catches both API errors and LLM hallucinating tool usage in text
            if iteration <= 1 and not tool_results:
                logger.warning("ReAct iteration %d — no tool call, nudging (attempt %d)", iteration, iteration + 1)
                messages.append({"role": "assistant", "content": content})
                nudge = nudge_message or (
                    "STOP. You are NOT using your tools. Do NOT write text describing what tools do. "
                    "You MUST actually invoke a tool function right now. "
                    "Call search_and_draft_reply if the user wants to reply to an email, "
                    "or call read_inbox / search_emails to find emails. DO IT NOW."
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
        # Add assistant message with tool_calls to conversation
        # Build manually to avoid unsupported fields like 'refusal' that break some providers
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
                error_msg = f"Unknown tool '{tool_name}'. Available: {[t.name for t in tools]}"
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


def _extract_tool_call(text: str):
    """Extract a tool call JSON from LLM response text (fallback for non-native tool calling)."""
    # Try ```json code blocks first (most common LLM behavior)
    for match in re.finditer(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL):
        try:
            parsed = json.loads(match.group(1).strip())
            if "tool" in parsed and "args" in parsed:
                return parsed["tool"], parsed["args"]
        except json.JSONDecodeError:
            continue

    # Try each line
    for line in text.strip().split("\n"):
        line = line.strip()
        if line.startswith("{") and '"tool"' in line:
            try:
                parsed = json.loads(line)
                if "tool" in parsed and "args" in parsed:
                    return parsed["tool"], parsed["args"]
            except json.JSONDecodeError:
                continue

    # Try finding a JSON object with "tool" key embedded in prose
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

    # Try entire response as JSON
    try:
        parsed = json.loads(text.strip())
        if "tool" in parsed and "args" in parsed:
            return parsed["tool"], parsed["args"]
    except json.JSONDecodeError:
        pass

    # Try Python function-call syntax: tool_name("arg1", "arg2") or tool_name(key="val")
    # This handles LLMs that write tool calls as text instead of using the API
    # Order matters: prefer combined tools (search_and_draft_reply) over individual ones
    func_match = re.search(
        r'(search_and_draft_reply|draft_reply|read_inbox|search_emails|get_thread)\s*\(',
        text
    )
    if func_match:
        tool_name = func_match.group(1)
        # Find the full call including parentheses
        start = func_match.end() - 1  # include the opening paren
        depth = 0
        end = start
        for i in range(start, len(text)):
            if text[i] == '(':
                depth += 1
            elif text[i] == ')':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        args_text = text[start + 1:end - 1].strip()

        # Parse arguments — try keyword args first, then positional
        args = {}
        # Try keyword: key="value", key="value"
        kw_matches = re.findall(r'(\w+)\s*=\s*"((?:[^"\\]|\\.)*)"|(\w+)\s*=\s*\'((?:[^\'\\]|\\.)*)\'', args_text)
        if kw_matches:
            for m in kw_matches:
                if m[0]:
                    args[m[0]] = m[1].replace('\\n', '\n').replace('\\"', '"')
                elif m[2]:
                    args[m[2]] = m[3].replace('\\n', '\n').replace("\\'", "'")
        else:
            # Positional args — extract quoted strings
            positional = re.findall(r'"((?:[^"\\]|\\.)*)"|\'((?:[^\'\\]|\\.)*)\'', args_text)
            positional_values = [p[0] or p[1] for p in positional]
            positional_values = [v.replace('\\n', '\n').replace('\\"', '"') for v in positional_values]

            # Map positional args to tool parameter names
            param_map = {
                "search_and_draft_reply": ["search_query", "body"],
                "draft_reply": ["email_id", "body"],
                "search_emails": ["query"],
                "read_inbox": ["filter"],
                "get_thread": ["thread_id"],
            }
            param_names = param_map.get(tool_name, [])
            for i, val in enumerate(positional_values):
                if i < len(param_names):
                    args[param_names[i]] = val

        if args or not args_text:
            logger.info("Parsed Python function-call syntax: %s(%s)", tool_name, list(args.keys()))
            return tool_name, args

    return None
