# Life OS — Session 6 Part 2: Insights Visualisation Redesign (2026-05-14)

## Overview

This session focused on making the Insights dashboard (`/insights`) visually polished and fully functional. Work covered three areas:
1. **Fix blank charts** — Nivo charts weren't rendering due to a height collapse issue
2. **Visual redesign** — Complete overhaul of the Insights page with cyberpunk-themed components, custom chart layers, and glowing neon aesthetics
3. **Data pipeline fix** — Demo data wasn't reaching the logged-in user; goal schemas rejected seeded data

---

## Fix 1: Blank Nivo Charts

### Problem

All four Nivo charts (Vitals Timeline, Task Velocity, Task Categories, Goal Progress) rendered as empty containers with no visible chart content.

### Root Cause

Nivo's `Responsive*` components render at `100%` height of their parent. The `CyberCard` content wrapper `<div class="p-5">` had no height constraint, collapsing to ~40px (just padding). Charts had 0 effective height.

### Fix

Wrapped each Nivo chart in `<div className="h-[300px]">` inside the card to give an explicit height container.

---

## Fix 2: Insights Page Visual Redesign

### What Changed

Completely rewrote `frontend/app/(app)/insights/page.tsx` with new custom components and improved Nivo chart configuration.

### New Components (defined inline)

| Component | Purpose |
|-----------|---------|
| `StatCard` | Glowing metric cards with color-tinted icon badges, radial gradient hover backgrounds, text-shadow numbers |
| `ChartHeader` | Chart card headers with colored icon badges instead of plain text |
| `PatternCard` | Discovered pattern cards with icons, descriptions, and subtle glow effects |
| `EmptyState` | Icon + text placeholder when no data exists |

### Stat Cards (Top Row)

- 7-Day Mood (magenta), Energy (green), Sleep (cyan)
- Large glowing numbers with `textShadow` matching their accent color
- Color-tinted icon badge in top-right corner
- Subtle `radial-gradient` background that intensifies on hover
- Descriptive subtext ("Average daily mood score", etc.)

### Vitals Timeline (Line Chart)

- **Custom SVG point layer** — Nivo v0.99's `pointColor: { from: "serieColor" }` didn't resolve correctly. Built a custom layer that reads `point.color` directly and renders triple-circle glowing dots (outer glow ring at 15% opacity, solid fill, dark center pinhole)
- **Auto y-scale** — Changed from `max: 6` to `max: "auto"` so sleep hours (7-8+) aren't clipped off the chart
- **`catmullRom` curves** — Smoother than `monotoneX`
- **Area fills** — `areaOpacity: 0.08` with `screen` blend mode for depth
- **Softer grid** — `strokeDasharray: "2 6"` for subtle dotted lines
- **Colors** — Explicit array `[mood=#ff00ff, energy=#00ff88, sleep=#00d4ff]` instead of `{ datum: "color" }`

### Task Velocity (Bar Chart)

- Stacked bars with `completed` (green) and `pending` (orange — changed from dark gray for visibility)
- `borderRadius: 2` on bars
- Labels hidden (`enableLabel: false`) for cleaner look
- Square legend symbols

### Task Categories (Pie/Donut Chart)

- **Centered total count** — Absolute-positioned `<div>` showing total task count inside the donut hole
- Arc labels and link labels disabled for cleaner look
- `activeOuterRadiusOffset: 4` for hover pop effect
- Circle legend symbols in a column on the right

### Goal Progress (Radial Bar Chart)

- Each goal rendered as its own series (one bar per goal) instead of all goals in one series
- Neon color palette: `[#00ff88, #00d4ff, #ff00ff, #ffcc00]`
- Track color set to `#1a1a2e` (subtle dark)

### Discovered Patterns Section

- Each pattern gets its own `PatternCard` with:
  - Colored icon (Clock for time bias, TrendingUp for completion rate, Moon for mood-sleep, Dumbbell for mood-exercise, Flame for streak, AlertTriangle for deferrals)
  - Descriptive subtext (e.g., "7-day average task completion", "r = 0.22 correlation")
  - Subtle radial gradient glow on hover
- New patterns surfaced: Mood-Exercise correlation, Average Deferrals
- Avoidance categories get a wide card with chamfered badge pills

### Overall Page

- `animate-fade-in-up` with staggered `animationDelay` on sections
- Better spacing (`space-y-8`)
- Consistent `cyber-chamfer` on all chart cards
- Hover transitions (`hover:border-[#2a2a4a]`) on chart cards
- Improved loading state with "Loading analytics..." text
- Page header with Brain icon badge

### Nivo Theme Updates

```js
{
  background: "transparent",
  grid: { line: { stroke: "#1a1a2e", strokeDasharray: "2 6" } },
  tooltip: { container: { background: "#12121a", borderRadius: "4px", boxShadow: "0 4px 20px rgba(0,0,0,0.5)" } },
  crosshair: { line: { stroke: "#00ff88", strokeOpacity: 0.5, strokeDasharray: "4 4" } },
}
```

---

## Fix 3: Demo Data Pipeline

### Problem

The `seed_demo_data.py` script created data under a "Test User" (`clerk_id: None`), not the actual Clerk-authenticated user. The Insights page showed only 1 real check-in instead of 30 days of demo data.

### Fix

Reassigned all demo data (25 check-ins, 25 tasks, 4 goals) from the test user to the real Clerk user via SQL UPDATE. Deleted the orphaned `UserPattern` row to avoid unique constraint violation, then recomputed patterns via `run_pattern_learning()`.

**Result:** User account now has 27 check-ins, 27 tasks, 4 goals — all visualizations fully populated.

---

## Fix 4: Goal Schema Validation Errors

### Problem

The Goals page (`/goals`) threw a `loadGoals` error. The `GET /goals` endpoint returned 500 because Pydantic validation failed when serializing goals from the database.

### Root Causes (3 issues in `backend/schemas/goal.py`)

1. **`milestones` type mismatch** — DB stored milestones as a dict (`{"m1": {...}, "m2": {...}}`), but the schema expected `List[dict]`. Pydantic rejected the dict with "Input should be a valid list".

2. **`domain` pattern too restrictive** — Allowed: `health|career|relationships|learning|personal|finance`. The seed script used `"work"` which was rejected.

3. **`timeframe` pattern too restrictive** — Allowed: `this_week|this_month|this_year|long_term`. The seed script used `"annual"` which was rejected.

### Fixes

```python
# Before
milestones: Optional[List[dict]] = None
domain: pattern=r"^(health|career|relationships|learning|personal|finance)$"
timeframe: pattern=r"^(this_week|this_month|this_year|long_term)$"

# After
milestones: Optional[Union[list[dict[str, Any]], dict[str, Any]]] = None
domain: pattern=r"^(health|career|work|relationships|learning|personal|finance)$"
timeframe: pattern=r"^(this_week|this_month|this_year|annual|long_term)$"
```

---

## Files Modified

| File | Change |
|------|--------|
| `frontend/app/(app)/insights/page.tsx` | Complete rewrite — new components (StatCard, ChartHeader, PatternCard, EmptyState), custom Nivo point layer, redesigned layout |
| `backend/schemas/goal.py` | Added `work` to domain pattern, `annual` to timeframe pattern, made `milestones` accept both list and dict |

---

## Verification

```bash
# Frontend build
cd frontend && npm run build

# Check insights page
# Navigate to /insights — all 4 charts render with 30 days of demo data
# Vitals: colored neon dots with glow, smooth curves, area fills
# Task Velocity: stacked green/orange bars
# Categories: donut with centered total count
# Goal Progress: 4 radial bars with neon colors
# Patterns: 5+ metric cards with icons and descriptions

# Check goals page
# Navigate to /goals — 4 goals render with progress bars
# No console errors
```
