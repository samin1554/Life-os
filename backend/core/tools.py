"""Tool registry for agent tool-use."""
from dataclasses import dataclass
from typing import Callable, Any


@dataclass
class Tool:
    name: str
    description: str
    func: Callable
    parameters: dict  # JSON schema for LLM tool-calling


TOOLS_REGISTRY: dict[str, Tool] = {}


def register_tool(name: str, description: str, parameters: dict):
    def decorator(func):
        TOOLS_REGISTRY[name] = Tool(
            name=name, description=description, func=func, parameters=parameters
        )
        return func

    return decorator


def get_tools_for_agent(tool_names: list[str]) -> list[Tool]:
    return [TOOLS_REGISTRY[name] for name in tool_names if name in TOOLS_REGISTRY]


def format_tools_for_prompt(tools: list[Tool]) -> str:
    """Format tool descriptions for inclusion in an LLM system prompt."""
    lines = []
    for t in tools:
        param_parts = []
        for k, v in t.parameters.get("properties", {}).items():
            if isinstance(v, dict):
                desc = v.get("description", v.get("type", ""))
                param_parts.append(f"{k}: {desc}")
            else:
                param_parts.append(f"{k}: {v}")
        params = ", ".join(param_parts)
        lines.append(f"- {t.name}({params}): {t.description}")
    return "\n".join(lines)


def format_tools_for_api(tools: list[Tool]) -> list[dict]:
    """Convert Tool objects to OpenAI function calling format for the tools API parameter."""
    api_tools = []
    for t in tools:
        # Build proper JSON schema properties
        properties = {}
        # Use explicit required list from schema, or default to all params
        explicit_required = t.parameters.get("required")
        required = []
        for k, v in t.parameters.get("properties", {}).items():
            if isinstance(v, dict):
                properties[k] = {
                    "type": v.get("type", "string"),
                    "description": v.get("description", ""),
                }
            else:
                properties[k] = {"type": "string", "description": str(v)}
            # Only add to required if no explicit list, or if in explicit list
            if explicit_required is None or k in explicit_required:
                required.append(k)

        api_tools.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        })
    return api_tools
