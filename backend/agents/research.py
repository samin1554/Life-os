"""Research Agent — searches the web and compiles structured findings."""
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from core.tools import get_tools_for_agent
from core.tool_runner import run_agent_with_tools

logger = logging.getLogger(__name__)

RESEARCH_TOOLS = ["web_search", "search_multiple", "scrape_page", "extract_data_points"]

RESEARCH_NUDGE = (
    "STOP. You are NOT using your tools. Do NOT write a research report from memory. "
    "You MUST call web_search or search_multiple RIGHT NOW to find real, current information. "
    "DO NOT make up facts. CALL A SEARCH TOOL NOW."
)

SYSTEM_PROMPT = """You are the Research Agent for Life OS.

Your job is to research topics by searching the web and compiling findings into a structured, citation-rich research report.

RESEARCH STRATEGY:
1. Start with `search_multiple` using 2-3 query variants for broader coverage
2. Scrape the most promising pages for detailed content
3. Use `extract_data_points` to pull structured data (prices, ratings, dates, specs) from scraped content
4. Compile everything into the structured format below

OUTPUT FORMAT — you MUST follow this exact structure:

## Executive Summary
2-3 sentence overview of what you found.

## Key Findings
- Finding 1 [Confidence: High/Medium/Low]
- Finding 2 [Confidence: High/Medium/Low]
- Finding 3 [Confidence: High/Medium/Low]

## Comparison Table
| Name/Option | Price | Rating | Key Feature | Source |
|-------------|-------|--------|-------------|--------|
| ...         | ...   | ...    | ...         | [1]    |
| ...         | ...   | ...    | ...         | [2]    |

## Detailed Analysis
### [Topic 1]
...paragraph with inline citations [1][2]...

### [Topic 2]
...paragraph with inline citations [3]...

## Sources
[1] Title — URL
[2] Title — URL
[3] Title — URL

CONFIDENCE LEGEND:
- High: Multiple independent sources agree
- Medium: Limited sources or some disagreement
- Low: Single source or speculative

GUIDELINES:
- Always include a Comparison Table when researching products, services, or options
- Use [1], [2], [3] inline citations that map to the Sources section
- Include specific data points: prices, dates, ratings, URLs
- If you receive context from a previous agent (e.g., an execution plan), use it to guide your research focus
- Be thorough but concise — quality over quantity
"""


async def run_research_agent(
    user_message: str, user_id: str, db: AsyncSession
) -> dict:
    tools = get_tools_for_agent(RESEARCH_TOOLS)
    response = await run_agent_with_tools(
        system_prompt=SYSTEM_PROMPT,
        user_message=user_message,
        tools=tools,
        max_iterations=5,
        user_id=user_id,
        db=db,
        nudge_message=RESEARCH_NUDGE,
    )
    return {"agent": "research", "response": response}
