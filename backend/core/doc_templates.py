"""Document templates for the Worker Agent.

Each template defines the structure, recommended format, and styling
for a common document type.
"""

TEMPLATES = {
    "travel_guide": {
        "format": "docx",
        "title_suffix": "Travel Guide",
        "sections": [
            "Cover",
            "Trip Overview",
            "Itinerary",
            "Budget Breakdown",
            "Accommodations",
            "Transportation",
            "Tips & Recommendations",
        ],
        "style": "modern_clean",
        "description": "A complete travel guide with itinerary, budget, and tips.",
    },
    "budget_tracker": {
        "format": "xlsx",
        "title_suffix": "Budget Tracker",
        "sheets": ["Summary", "Expenses", "Income", "Charts"],
        "style": "colorful_professional",
        "description": "A formatted spreadsheet with budget tracking, formulas, and charts.",
    },
    "research_report": {
        "format": "pdf",
        "title_suffix": "Research Report",
        "sections": [
            "Cover Page",
            "Executive Summary",
            "Key Findings",
            "Comparison",
            "Detailed Analysis",
            "Sources",
        ],
        "style": "academic_formal",
        "description": "A professional research report with citations and comparison tables.",
    },
    "project_plan": {
        "format": "docx",
        "title_suffix": "Project Plan",
        "sections": [
            "Cover",
            "Overview",
            "Goals & Objectives",
            "Timeline",
            "Tasks & Responsibilities",
            "Budget",
            "Risks & Mitigation",
        ],
        "style": "modern_clean",
        "description": "A structured project plan with timeline, tasks, and budget.",
    },
    "modern_report": {
        "format": "docx",
        "title_suffix": "Report",
        "sections": [
            "Cover",
            "Executive Summary",
            "Main Content",
            "Conclusion",
            "Appendix",
        ],
        "style": "modern_clean",
        "description": "A general-purpose professional report.",
    },
    "comparison_sheet": {
        "format": "xlsx",
        "title_suffix": "Comparison",
        "sheets": ["Comparison", "Details", "Scores"],
        "style": "colorful_professional",
        "description": "A side-by-side comparison spreadsheet with scoring.",
    },
}


def detect_template(user_message: str, context: str = "") -> str:
    """Detect the best template based on user request keywords."""
    msg = (user_message + " " + context).lower()

    if any(w in msg for w in ["travel", "trip", "itinerary", "vacation", "hotel", "flight", "journey"]):
        return "travel_guide"
    if any(w in msg for w in ["budget", "expense", "finance", "cost", "spending", "tracker", "money"]):
        return "budget_tracker"
    if any(w in msg for w in ["research", "compare", "comparison", "review", "best", "vs", "versus"]):
        return "research_report"
    if any(w in msg for w in ["project", "plan", "schedule", "timeline", "milestone", "roadmap"]):
        return "project_plan"
    if any(w in msg for w in ["spreadsheet", "excel", "sheet", "csv", "table", "data"]):
        return "comparison_sheet"

    return "modern_report"


def get_template(name: str) -> dict:
    """Get a template by name, falling back to modern_report."""
    return TEMPLATES.get(name, TEMPLATES["modern_report"])
