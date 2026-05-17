"""Web search and scraping tools for agents."""
import asyncio
import logging

import httpx
from bs4 import BeautifulSoup

from core.tools import register_tool
from core.config import get_settings
from core.llm import extract_structured

logger = logging.getLogger(__name__)


def _deduplicate_results(results: list[dict]) -> list[dict]:
    """Keep only the best result per domain."""
    seen_domains = set()
    deduped = []
    for r in results:
        url = r.get("url", "")
        domain = url.split("/")[2] if len(url.split("/")) > 2 else url
        if domain not in seen_domains:
            seen_domains.add(domain)
            deduped.append(r)
    return deduped


@register_tool(
    name="web_search",
    description="Search the web for current information. Returns titles, URLs, and snippets.",
    parameters={
        "properties": {
            "query": "search query string",
            "max_results": "number of results (default 5)",
        }
    },
)
async def web_search(query: str, max_results: int = 5) -> dict:
    """Search using Tavily (primary) or DuckDuckGo (fallback)."""
    settings = get_settings()

    if settings.tavily_api_key:
        try:
            from tavily import AsyncTavilyClient

            client = AsyncTavilyClient(api_key=settings.tavily_api_key)
            result = await client.search(
                query=query, max_results=max_results, include_answer=True
            )
            results = [
                {
                    "title": r["title"],
                    "url": r["url"],
                    "content": r["content"][:2000],
                }
                for r in result.get("results", [])[:max_results]
            ]
            results = _deduplicate_results(results)
            return {
                "answer": result.get("answer", ""),
                "results": results,
            }
        except Exception as e:
            logger.warning("Tavily search failed, falling back to DuckDuckGo: %s", e)

    # DuckDuckGo fallback (no API key needed)
    try:
        from ddgs import DDGS

        def _ddgs_search(q: str, limit: int):
            with DDGS() as ddgs:
                return list(ddgs.text(q, max_results=limit))

        raw_results = await asyncio.to_thread(_ddgs_search, query, max_results)
        results = []
        for r in raw_results:
            results.append(
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "content": r.get("body", "")[:2000],
                }
            )
        results = _deduplicate_results(results)
        return {"answer": "", "results": results}
    except Exception as e:
        logger.error("DuckDuckGo search failed: %s", e)
        return {
            "answer": "",
            "results": [],
            "error": f"Search failed: {e}",
        }


@register_tool(
    name="search_multiple",
    description="Run multiple search queries and merge/deduplicate results. Better coverage than a single search.",
    parameters={
        "properties": {
            "queries": "list of search query strings",
            "max_results_per_query": "max results per query (default 5)",
        }
    },
)
async def search_multiple(queries: list[str], max_results_per_query: int = 5) -> dict:
    """Run multiple searches in parallel and merge results."""
    tasks = [web_search(q, max_results_per_query) for q in queries]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_results = []
    combined_answer = ""

    for r in results:
        if isinstance(r, Exception):
            logger.warning("Search query failed: %s", r)
            continue
        if r.get("answer"):
            combined_answer += r["answer"] + " "
        all_results.extend(r.get("results", []))

    # Deduplicate across all queries
    deduped = _deduplicate_results(all_results)

    return {
        "answer": combined_answer.strip(),
        "results": deduped,
        "queries_used": queries,
    }


@register_tool(
    name="scrape_page",
    description="Fetch and extract the main text content from a URL.",
    parameters={"properties": {"url": "the URL to scrape"}},
)
async def scrape_page(url: str) -> dict:
    """Fetch a web page and extract text content."""
    try:
        async with httpx.AsyncClient(
            timeout=15, follow_redirects=True
        ) as client:
            resp = await client.get(
                url, headers={"User-Agent": "LifeOS-Agent/1.0"}
            )
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)
        return {
            "url": url,
            "content": text[:4000],
            "title": soup.title.string if soup.title else "",
        }
    except Exception as e:
        logger.warning("Failed to scrape %s: %s", url, e)
        return {"url": url, "content": "", "title": "", "error": str(e)}


@register_tool(
    name="extract_data_points",
    description="Extract structured data (prices, ratings, dates, specs) from text content using AI.",
    parameters={
        "properties": {
            "text": "the text content to analyze",
            "fields": "list of field names to extract, e.g. ['price', 'rating', 'brand']",
        }
    },
)
async def extract_data_points(text: str, fields: list[str], user_id=None, db=None) -> dict:
    """Use LLM to extract structured data from scraped text."""
    from core.llm import extract_structured

    prompt = f"""Extract the following fields from the text below.
Return a JSON object where each field maps to its extracted value.
If a field is not found, use null.

Fields to extract: {', '.join(fields)}

Text:
{text[:4000]}
"""
    try:
        result = await extract_structured(
            system_prompt="You extract structured data from text. Return ONLY valid JSON.",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
            user_id=user_id,
            db=db,
        )
        return {"extracted": result, "fields_requested": fields}
    except Exception as e:
        logger.warning("Data extraction failed: %s", e)
        return {"extracted": {}, "fields_requested": fields, "error": str(e)}
