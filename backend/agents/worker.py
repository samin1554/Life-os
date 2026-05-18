"""Worker Agent — generates professional documents, spreadsheets, and visualizations."""
import json
import logging
import os
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from core.tools import get_tools_for_agent
from core.tool_runner import run_agent_with_tools
from core.doc_templates import detect_template, get_template
from core.storage import get_storage
from models.models import GeneratedFile
import core.tools_docs  # noqa: F401 — registers doc generation tools
import core.tools_data  # noqa: F401 — registers data analysis + chart tools

WORKER_TOOLS = ["analyze_data", "generate_chart", "generate_docx", "generate_xlsx", "generate_pdf"]

WORKER_NUDGE = (
    "STOP. You are NOT using your tools. Do NOT describe a document in text. "
    "You MUST call generate_docx, generate_xlsx, or generate_pdf RIGHT NOW. "
    "Provide all data in the tool arguments — title, sections/sheets with real content. "
    "DO NOT output markdown or explain what you would do. CALL THE TOOL NOW."
)

SYSTEM_PROMPT = """You are the Worker Agent for Life OS. You analyze data, create visualizations, and generate downloadable documents.

CRITICAL RULES:
1. You MUST call tools to produce output. Do NOT describe documents in text.
2. Do NOT output markdown tables instead of calling a tool.
3. Do NOT explain what you're going to do — call tools immediately.
4. Include ALL data from the user's request — don't summarize away details.
5. You can call multiple tools in sequence: analyze → chart → export.
6. NEVER return a standalone chart image. Charts/graphs MUST always be embedded inside a document (docx, pdf) or spreadsheet (xlsx). generate_chart is ONLY an intermediate step — you MUST always follow it with generate_docx, generate_pdf, or generate_xlsx to embed the chart.
7. Your final output MUST always be a document (docx, xlsx, or pdf). Never end with just a chart PNG.

AVAILABLE TOOLS:
- analyze_data: Run pandas operations on data (describe, group_by, sort, filter, add_column, pivot, top_n, value_counts)
- generate_chart: Create chart images — INTERMEDIATE STEP ONLY, must always be followed by a document export tool
- generate_xlsx: Create Excel spreadsheets with optional summary rows and built-in charts
- generate_docx: Create Word documents with embedded chart images
- generate_pdf: Create PDF documents with embedded chart images

WORKFLOW OPTIONS:

SIMPLE — Direct export (no analysis needed):
Just call generate_xlsx, generate_docx, or generate_pdf directly.

ANALYSIS — Data needs processing first:
1. Call analyze_data with operations like group_by, sort, filter, etc.
2. Use the results to call generate_xlsx or generate_docx/pdf.

WITH CHARTS — Visualizations requested:
1. Optionally call analyze_data first.
2. Call generate_chart to create a chart image (intermediate PNG).
3. ALWAYS call generate_docx or generate_pdf with chart_image in sections to embed it.
   OR call generate_xlsx which has built-in chart_type support (no separate generate_chart needed).

TEMPLATE SELECTION:
- Travel/itinerary → "travel_guide"
- Budget/finance → "budget_tracker"
- Research/compare → "research_report"
- Project/plan → "project_plan"
- Spreadsheet/data → "comparison_sheet"
- Generic → "modern_report"

EXAMPLE 1 — Simple spreadsheet:
{"tool": "generate_xlsx", "args": {"title": "Monthly Budget", "template": "budget_tracker", "sheets": [{"name": "Budget", "headers": ["Category", "Amount", "Notes"], "rows": [["Rent", 1200, "Due 1st"], ["Groceries", 400, "Weekly"]], "summary": "totals"}]}}

EXAMPLE 2 — Spreadsheet with built-in chart (no separate generate_chart needed):
{"tool": "generate_xlsx", "args": {"title": "Revenue Analysis", "template": "comparison_sheet", "sheets": [{"name": "By Product", "headers": ["Product", "Revenue"], "rows": [["A", 700], ["B", 300]], "chart_type": "bar", "summary": "totals"}]}}

EXAMPLE 3 — Chart embedded in a PDF report (2-step):
Step 1: {"tool": "generate_chart", "args": {"chart_type": "bar", "title": "Sales by Region", "data": {"labels": ["East", "West", "North"], "datasets": [{"label": "Revenue", "values": [500, 300, 200]}]}, "options": {"y_label": "Revenue ($)"}}}
Step 2 (REQUIRED — embed chart in document): {"tool": "generate_pdf", "args": {"title": "Sales Report", "template": "research_report", "sections": [{"heading": "Regional Sales", "content": "Analysis of Q1 sales performance by region.", "chart_image": "/path/from/step1/chart.png", "table": {"headers": ["Region", "Revenue"], "rows": [["East", "$500"], ["West", "$300"], ["North", "$200"]]}}]}}

EXAMPLE 4 — Document:
{"tool": "generate_docx", "args": {"title": "Tokyo Travel Guide", "template": "travel_guide", "sections": [{"heading": "Overview", "content": "Tokyo is Japan's capital city."}, {"heading": "Budget", "content": "Daily costs:", "table": {"headers": ["Item", "Cost"], "rows": [["Hotel", "$80-120"], ["Food", "$30-50"]]}}]}}

After the final tool returns a result, respond with a brief JSON summary including the filename.
"""


async def run_worker_agent(
    user_message: str, user_id: str, db: AsyncSession
) -> dict:
    # Detect template early so the LLM knows what format to produce
    template_name = detect_template(user_message)
    template = get_template(template_name)

    # Prepend template hint to user message
    augmented_message = (
        f"[TEMPLATE DETECTED: {template_name} — format: {template['format']}]\n\n"
        f"{user_message}"
    )

    tools = get_tools_for_agent(WORKER_TOOLS)
    response, tool_results = await run_agent_with_tools(
        system_prompt=SYSTEM_PROMPT,
        user_message=augmented_message,
        tools=tools,
        max_iterations=6,
        collect_results=True,
        max_tokens=4000,
        user_id=user_id,
        db=db,
        nudge_message=WORKER_NUDGE,
    )

    # If no document was generated, retry with a stronger forced prompt
    has_document = any(
        tr.get("result", {}).get("format") in ("docx", "xlsx", "pdf")
        for tr in tool_results
    )
    if not has_document and not tool_results:
        logger.warning("Worker agent produced no tool calls, retrying with forced prompt")
        forced_message = (
            f"YOU MUST GENERATE A FILE. The user asked: {user_message}\n\n"
            "Call generate_docx, generate_xlsx, or generate_pdf with COMPLETE data. "
            "Do NOT respond with text. Your ONLY job is to call a tool."
        )
        response, tool_results = await run_agent_with_tools(
            system_prompt=SYSTEM_PROMPT,
            user_message=forced_message,
            tools=tools,
            max_iterations=4,
            collect_results=True,
            max_tokens=4000,
            user_id=user_id,
            db=db,
            nudge_message=WORKER_NUDGE,
        )

    # Extract metadata from LLM response
    metadata = _extract_metadata(response)

    # Persist GeneratedFile records — only track documents (docx/xlsx/pdf), not
    # intermediate chart PNGs (those are embedded inside the documents).
    file_info = None
    chart_files = []  # track chart PNGs for cleanup
    for tr in tool_results:
        result = tr.get("result", {})
        if "filename" in result and "filepath" in result:
            fmt = result.get("format", "")
            if fmt in ("docx", "xlsx", "pdf"):
                file_info = result  # always take the latest document
            else:
                chart_files.append(result)  # intermediate chart PNG

    # Fallback: if tool result not captured but metadata has filename, look up file
    if not file_info and metadata.get("filename"):
        from core.tools_docs import GENERATED_FILES_DIR

        filepath = os.path.join(GENERATED_FILES_DIR, metadata["filename"])
        if os.path.exists(filepath):
            file_info = {
                "filename": metadata["filename"],
                "filepath": filepath,
                "format": metadata.get("format", "docx"),
                "title": metadata.get("title", "Document"),
                "template": metadata.get("template", template_name),
                "file_size": os.path.getsize(filepath),
            }

    if file_info:
        # Upload to S3 if configured, otherwise keep local path
        storage = get_storage()
        stored_path = file_info["filepath"]
        if storage.is_s3:
            s3_key = f"{user_id}/{file_info['filename']}"
            await storage.upload(file_info["filepath"], s3_key)
            stored_path = s3_key

        gen_file = GeneratedFile(
            user_id=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
            filename=file_info["filename"],
            original_name=metadata.get("title", file_info.get("title", "Document"))
            + "."
            + file_info.get("format", "docx"),
            file_path=stored_path,
            file_format=file_info.get("format", "docx"),
            file_size_bytes=file_info.get("file_size", 0),
            template_used=file_info.get("template", template_name),
            source_agent="worker",
            task_description=user_message[:500],
        )
        db.add(gen_file)
        await db.commit()
        await db.refresh(gen_file)

        # Clean up local temp file after S3 upload
        if storage.is_s3 and os.path.exists(file_info["filepath"]):
            os.remove(file_info["filepath"])

        # Clean up intermediate chart PNGs (already embedded in the document)
        for chart in chart_files:
            chart_path = chart.get("filepath", "")
            if chart_path and os.path.exists(chart_path):
                os.remove(chart_path)

        # Enrich metadata with DB ID for clean download URLs
        metadata["file_id"] = str(gen_file.id)
        metadata["download_url"] = f"/files/{gen_file.id}/download"

    return {
        "agent": "worker",
        "response": response,
        "template": template_name,
        "metadata": metadata,
    }


def _extract_metadata(response: str) -> dict:
    """Extract JSON metadata block from worker response."""
    import re

    # Look for ```json block
    match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Look for raw JSON object
    match = re.search(r'\{[\s\S]*?"filename"[\s\S]*?\}', response)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {}
