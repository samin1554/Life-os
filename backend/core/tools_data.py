"""Data analysis and visualization tools for the Worker Agent — pandas + matplotlib."""
import os
import uuid
import json

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from core.tools import register_tool

GENERATED_FILES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "generated_files"
)
os.makedirs(GENERATED_FILES_DIR, exist_ok=True)

CHART_COLORS = ["#00ff88", "#00d4ff", "#ff00ff", "#ff3366", "#ffcc00", "#ff8800", "#8b5cf6", "#00aaff"]
DARK_BG = "#0a0a0f"
GRID_COLOR = "#2a2a3a"
TEXT_COLOR = "#e0e0e0"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA ANALYSIS (pandas)
# ═══════════════════════════════════════════════════════════════════════════════

@register_tool(
    name="analyze_data",
    description="Analyze data using pandas. Takes headers + rows, runs operations (describe, group_by, sort, filter, add_column), returns analysis results as structured data.",
    parameters={
        "properties": {
            "headers": {"type": "array", "description": "column names, e.g. ['Name', 'Price', 'Category']"},
            "rows": {"type": "array", "description": "list of row arrays, e.g. [['A', 10, 'X'], ['B', 20, 'Y']]"},
            "operations": {"type": "array", "description": "list of operation objects to apply sequentially"},
        }
    },
)
async def analyze_data(headers: list, rows: list, operations: list) -> dict:
    """Run pandas operations on tabular data.

    Supported operations:
    - {"op": "describe"} — summary statistics for numeric columns
    - {"op": "group_by", "by": "col", "agg": {"col2": "sum"}} — group and aggregate
    - {"op": "sort", "by": "col", "ascending": false}
    - {"op": "filter", "column": "col", "condition": ">", "value": 100}
    - {"op": "add_column", "name": "new_col", "expression": "Price * Quantity"}
    - {"op": "pivot", "index": "col", "columns": "col2", "values": "col3", "agg": "sum"}
    - {"op": "top_n", "n": 5, "by": "col", "ascending": false}
    - {"op": "value_counts", "column": "col"}
    """
    df = pd.DataFrame(rows, columns=headers)

    # Auto-convert numeric columns
    for col in df.columns:
        try:
            df[col] = pd.to_numeric(df[col])
        except (ValueError, TypeError):
            pass

    results = []
    for op_def in operations:
        op = op_def.get("op", "")
        try:
            if op == "describe":
                desc = df.describe(include="all").round(2)
                results.append({
                    "op": "describe",
                    "result": {
                        "headers": ["stat"] + list(desc.columns),
                        "rows": [[idx] + [_safe_val(v) for v in row] for idx, row in zip(desc.index, desc.values)],
                    }
                })

            elif op == "group_by":
                by = op_def["by"]
                agg = op_def.get("agg", {})
                if not agg:
                    agg = {c: "sum" for c in df.select_dtypes(include=[np.number]).columns if c != by}
                grouped = df.groupby(by).agg(agg).reset_index().round(2)
                results.append({
                    "op": "group_by",
                    "by": by,
                    "result": {
                        "headers": list(grouped.columns),
                        "rows": grouped.values.tolist(),
                    }
                })

            elif op == "sort":
                by = op_def["by"]
                ascending = op_def.get("ascending", True)
                df = df.sort_values(by=by, ascending=ascending).reset_index(drop=True)
                results.append({
                    "op": "sort",
                    "by": by,
                    "result": {
                        "headers": list(df.columns),
                        "rows": df.values.tolist(),
                    }
                })

            elif op == "filter":
                col = op_def["column"]
                cond = op_def["condition"]
                val = op_def["value"]
                if cond == ">":
                    df = df[df[col] > val]
                elif cond == "<":
                    df = df[df[col] < val]
                elif cond == ">=":
                    df = df[df[col] >= val]
                elif cond == "<=":
                    df = df[df[col] <= val]
                elif cond == "==":
                    df = df[df[col] == val]
                elif cond == "!=":
                    df = df[df[col] != val]
                elif cond == "contains":
                    df = df[df[col].astype(str).str.contains(str(val), case=False, na=False)]
                df = df.reset_index(drop=True)
                results.append({
                    "op": "filter",
                    "rows_remaining": len(df),
                    "result": {
                        "headers": list(df.columns),
                        "rows": df.values.tolist(),
                    }
                })

            elif op == "add_column":
                name = op_def["name"]
                expr = op_def["expression"]
                df[name] = df.eval(expr)
                results.append({
                    "op": "add_column",
                    "column": name,
                    "result": {
                        "headers": list(df.columns),
                        "rows": df.head(5).values.tolist(),
                        "total_rows": len(df),
                    }
                })

            elif op == "pivot":
                pivot = pd.pivot_table(
                    df,
                    index=op_def["index"],
                    columns=op_def.get("columns"),
                    values=op_def.get("values"),
                    aggfunc=op_def.get("agg", "sum"),
                ).round(2).reset_index()
                pivot.columns = [str(c) if not isinstance(c, tuple) else "_".join(str(x) for x in c) for c in pivot.columns]
                results.append({
                    "op": "pivot",
                    "result": {
                        "headers": list(pivot.columns),
                        "rows": pivot.values.tolist(),
                    }
                })

            elif op == "top_n":
                n = op_def.get("n", 5)
                by = op_def["by"]
                ascending = op_def.get("ascending", False)
                top = df.nlargest(n, by) if not ascending else df.nsmallest(n, by)
                results.append({
                    "op": "top_n",
                    "result": {
                        "headers": list(top.columns),
                        "rows": top.values.tolist(),
                    }
                })

            elif op == "value_counts":
                col = op_def["column"]
                counts = df[col].value_counts().reset_index()
                counts.columns = [col, "count"]
                results.append({
                    "op": "value_counts",
                    "column": col,
                    "result": {
                        "headers": list(counts.columns),
                        "rows": counts.values.tolist(),
                    }
                })

        except Exception as e:
            results.append({"op": op, "error": str(e)})

    # Summary stats
    summary = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "numeric_columns": list(df.select_dtypes(include=[np.number]).columns),
        "text_columns": list(df.select_dtypes(include=["object"]).columns),
    }

    return {
        "summary": summary,
        "operations": results,
        "final_data": {
            "headers": list(df.columns),
            "rows": df.values.tolist(),
        }
    }


def _safe_val(v):
    if pd.isna(v):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return round(float(v), 2)
    return v


# ═══════════════════════════════════════════════════════════════════════════════
# CHART GENERATION (matplotlib)
# ═══════════════════════════════════════════════════════════════════════════════

@register_tool(
    name="generate_chart",
    description="Generate a chart image (PNG) using matplotlib. Returns {filename, filepath, chart_type}. The image can be embedded in docx/pdf exports.",
    parameters={
        "properties": {
            "chart_type": {"type": "string", "description": "one of: bar, horizontal_bar, line, pie, scatter, histogram, stacked_bar"},
            "title": {"type": "string", "description": "chart title"},
            "data": {"type": "object", "description": "chart data: {labels: [string], datasets: [{label: string, values: [number]}]} — for pie: {labels: [...], values: [...]}"},
            "options": {"type": "object", "description": "optional: {x_label, y_label, figsize: [w,h], show_values: bool, stacked: bool}"},
        }
    },
)
async def generate_chart(
    chart_type: str, title: str, data: dict, options: dict = None
) -> dict:
    options = options or {}
    figsize = tuple(options.get("figsize", [10, 6]))
    x_label = options.get("x_label", "")
    y_label = options.get("y_label", "")
    show_values = options.get("show_values", True)

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(DARK_BG)
    ax.set_facecolor(DARK_BG)

    labels = data.get("labels", [])
    datasets = data.get("datasets", [])
    values = data.get("values", [])

    if chart_type == "pie":
        colors = CHART_COLORS[:len(labels)]
        wedges, texts, autotexts = ax.pie(
            values, labels=labels, colors=colors, autopct="%1.1f%%",
            textprops={"color": TEXT_COLOR, "fontsize": 10},
            pctdistance=0.85, startangle=90
        )
        for t in autotexts:
            t.set_fontsize(9)
            t.set_color("white")
        centre_circle = plt.Circle((0, 0), 0.55, fc=DARK_BG)
        ax.add_artist(centre_circle)

    elif chart_type == "histogram":
        if datasets:
            for i, ds in enumerate(datasets):
                ax.hist(ds["values"], bins=options.get("bins", 15),
                        color=CHART_COLORS[i % len(CHART_COLORS)], alpha=0.7,
                        label=ds.get("label", f"Series {i+1}"), edgecolor="#333")
        elif values:
            ax.hist(values, bins=options.get("bins", 15),
                    color=CHART_COLORS[0], alpha=0.7, edgecolor="#333")

    elif chart_type == "scatter":
        if datasets and len(datasets) >= 2:
            ax.scatter(datasets[0]["values"], datasets[1]["values"],
                       c=CHART_COLORS[0], alpha=0.7, s=60, edgecolors="#333")
            if len(datasets) > 0:
                ax.set_xlabel(datasets[0].get("label", "X"), color=TEXT_COLOR, fontsize=11)
            if len(datasets) > 1:
                ax.set_ylabel(datasets[1].get("label", "Y"), color=TEXT_COLOR, fontsize=11)

    elif chart_type in ("bar", "horizontal_bar", "stacked_bar"):
        x = np.arange(len(labels))
        n = len(datasets)
        width = 0.8 / max(n, 1)
        stacked = chart_type == "stacked_bar" or options.get("stacked", False)

        bottom = np.zeros(len(labels))
        for i, ds in enumerate(datasets):
            color = CHART_COLORS[i % len(CHART_COLORS)]
            vals = ds["values"]
            lbl = ds.get("label", f"Series {i+1}")

            if chart_type == "horizontal_bar":
                if stacked:
                    bars = ax.barh(x, vals, height=0.6, left=bottom, label=lbl, color=color, edgecolor="#333")
                    bottom = np.add(bottom, vals)
                else:
                    bars = ax.barh(x + i * width - (n - 1) * width / 2, vals, height=width, label=lbl, color=color, edgecolor="#333")
                ax.set_yticks(x)
                ax.set_yticklabels(labels, color=TEXT_COLOR)
            else:
                if stacked:
                    bars = ax.bar(x, vals, width=0.6, bottom=bottom, label=lbl, color=color, edgecolor="#333")
                    bottom = np.add(bottom, vals)
                else:
                    bars = ax.bar(x + i * width - (n - 1) * width / 2, vals, width=width, label=lbl, color=color, edgecolor="#333")
                ax.set_xticks(x)
                ax.set_xticklabels(labels, color=TEXT_COLOR, rotation=45 if len(labels) > 6 else 0, ha="right" if len(labels) > 6 else "center")

            if show_values and not stacked:
                for bar in bars:
                    if chart_type == "horizontal_bar":
                        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                                f"{bar.get_width():.0f}", va="center", color=TEXT_COLOR, fontsize=8)
                    else:
                        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                                f"{bar.get_height():.0f}", ha="center", va="bottom", color=TEXT_COLOR, fontsize=8)

        if n > 1:
            ax.legend(facecolor=DARK_BG, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR)

    elif chart_type == "line":
        for i, ds in enumerate(datasets):
            color = CHART_COLORS[i % len(CHART_COLORS)]
            ax.plot(labels, ds["values"], color=color, marker="o", markersize=5,
                    linewidth=2, label=ds.get("label", f"Series {i+1}"))
            if show_values:
                for j, v in enumerate(ds["values"]):
                    ax.annotate(f"{v}", (labels[j], v), textcoords="offset points",
                                xytext=(0, 10), ha="center", color=TEXT_COLOR, fontsize=8)
        if len(datasets) > 1:
            ax.legend(facecolor=DARK_BG, edgecolor=GRID_COLOR, labelcolor=TEXT_COLOR)
        if len(labels) > 6:
            plt.xticks(rotation=45, ha="right")

    ax.set_title(title, color=TEXT_COLOR, fontsize=14, fontweight="bold", pad=15)
    if x_label:
        ax.set_xlabel(x_label, color=TEXT_COLOR, fontsize=11)
    if y_label:
        ax.set_ylabel(y_label, color=TEXT_COLOR, fontsize=11)

    ax.tick_params(colors=TEXT_COLOR)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRID_COLOR)
    ax.spines["bottom"].set_color(GRID_COLOR)
    if chart_type != "pie":
        ax.grid(axis="y", color=GRID_COLOR, alpha=0.3, linestyle="--")

    plt.tight_layout()

    filename = f"{uuid.uuid4().hex[:8]}_chart_{title.replace(' ', '_')[:20]}.png"
    filepath = os.path.join(GENERATED_FILES_DIR, filename)
    fig.savefig(filepath, dpi=150, facecolor=DARK_BG, bbox_inches="tight")
    plt.close(fig)

    return {
        "filename": filename,
        "filepath": filepath,
        "chart_type": chart_type,
        "title": title,
    }
