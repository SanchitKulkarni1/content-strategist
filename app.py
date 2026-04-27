import re
import time
from datetime import datetime

import streamlit as st
from agents import regenerate_post_prompts_node
from orchestrator.graph import build_graph


# UI: Page setup
st.set_page_config(page_title="Content Strategy Agent", page_icon="✨", layout="wide")


# UI: Visual styling
st.markdown(
    """
<style>
.main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 2.5rem;
}

[data-testid="stSidebar"] {
    display: none;
}

.hero-wrap {
    max-width: 1100px;
    margin: 1.5rem auto 1.5rem auto;
    text-align: center;
}

.hero-title {
    font-size: 2.6rem;
    font-weight: 800;
    line-height: 1.15;
    margin-bottom: 0.6rem;
    background: linear-gradient(135deg, #60a5fa, #a78bfa, #f472b6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.hero-subtitle {
    color: #94a3b8;
    font-size: 1.05rem;
    line-height: 1.6;
    margin-bottom: 1.5rem;
}

.hero-card {
    border: 1px solid rgba(148, 163, 184, 0.2);
    border-radius: 14px;
    background: rgba(30, 41, 59, 0.4);
    padding: 1.3rem 1rem 1rem 1rem;
    min-height: 152px;
    text-align: center;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.hero-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(96, 165, 250, 0.12);
}

.hero-card-icon {
    font-size: 2rem;
    margin-bottom: 0.5rem;
}

.hero-card-title {
    font-size: 1.05rem;
    font-weight: 700;
    margin-bottom: 0.35rem;
    color: #e2e8f0;
}

.hero-card-text {
    color: #94a3b8;
    font-size: 0.9rem;
    line-height: 1.5;
}

/* How it works flow */
.how-it-works {
    max-width: 900px;
    margin: 1.5rem auto 0.5rem auto;
    text-align: center;
}

.how-it-works-title {
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #64748b;
    margin-bottom: 0.9rem;
}

.how-steps-row {
    display: flex;
    align-items: flex-start;
    justify-content: center;
    gap: 0.5rem;
}

.how-step {
    flex: 1;
    max-width: 220px;
    text-align: center;
}

.how-step-num {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    border-radius: 50%;
    background: linear-gradient(135deg, #3b82f6, #6366f1);
    color: #ffffff;
    font-weight: 700;
    font-size: 0.95rem;
    margin-bottom: 0.4rem;
}

.how-step-label {
    font-weight: 700;
    font-size: 0.95rem;
    color: #e2e8f0;
    margin-bottom: 0.2rem;
}

.how-step-desc {
    font-size: 0.82rem;
    color: #94a3b8;
    line-height: 1.4;
}

.how-step-arrow {
    color: #475569;
    font-size: 1.4rem;
    padding-top: 0.5rem;
    font-weight: 700;
}

/* Brand handle variant */
.handle-brand {
    background: #1e3a5f !important;
    border-color: #60a5fa !important;
    color: #93c5fd !important;
}

.section-card {
    border: 1px solid rgba(30, 41, 59, 0.12);
    border-radius: 12px;
    background: linear-gradient(180deg, #ffffff 0%, #fafbfc 100%);
    padding: 1.1rem 1.2rem 0.6rem 1.2rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.section-title {
    font-size: 1.1rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
    padding-bottom: 0.35rem;
    border-bottom: 2px solid #e2e8f0;
    color: #0f172a;
}

.section-card ul, .section-card ol {
    margin-top: 0.3rem;
    margin-bottom: 0.3rem;
    padding-left: 1.2rem;
}

.section-card li {
    margin-bottom: 0.35rem;
    line-height: 1.5;
}

/* Expander cards inside tabs — tighter spacing */
.stTabs [data-testid="stExpander"] {
    margin-bottom: 0.5rem;
}

/* Blockquote styling for hook/concept/why-this-wins */
.stTabs blockquote {
    border-left: 3px solid #60a5fa;
    padding: 0.4rem 0.8rem;
    margin: 0.3rem 0 0.6rem 0;
    background: #f8fafc;
    border-radius: 0 6px 6px 0;
    color: #1e293b;
    font-size: 0.95rem;
}

.complete-banner {
    border: 1px solid #86efac;
    border-left: 6px solid #22c55e;
    background: #f0fdf4;
    border-radius: 10px;
    padding: 0.9rem 1rem;
}

.progress-steps {
    border: 1px solid rgba(30, 41, 59, 0.14);
    border-radius: 10px;
    background: #f8fafc;
    padding: 0.75rem;
    margin-bottom: 0.6rem;
}

.step-chip {
    display: inline-block;
    margin: 0.18rem 0.2rem;
    padding: 0.28rem 0.55rem;
    border-radius: 20px;
    font-size: 0.84rem;
    border: 1px solid #d1d5db;
    color: #374151;
    background: #ffffff;
}

.step-chip.active {
    background: #dbeafe;
    border-color: #60a5fa;
    color: #1d4ed8;
    font-weight: 700;
}

.step-chip.done {
    background: #dcfce7;
    border-color: #4ade80;
    color: #166534;
    font-weight: 700;
}

.rating-badge {
    display: inline-block;
    border-radius: 999px;
    padding: 0.2rem 0.6rem;
    font-size: 0.82rem;
    font-weight: 700;
    margin-top: 0.15rem;
}

.rating-strong {
    color: #065f46;
    background: #d1fae5;
}

.rating-mid {
    color: #92400e;
    background: #fef3c7;
}

.rating-low {
    color: #991b1b;
    background: #fee2e2;
}

.active-trend-badge {
    display: inline-block;
    border: 1px solid #93c5fd;
    background: #eff6ff;
    color: #1d4ed8;
    border-radius: 999px;
    padding: 0.22rem 0.66rem;
    font-size: 0.84rem;
    font-weight: 700;
}

.input-shell {
    max-width: 960px;
    margin: 0.2rem auto 1.2rem auto;
    padding: 1rem;
    border: 1px solid rgba(148, 163, 184, 0.35);
    border-radius: 12px;
    background: rgba(15, 23, 42, 0.4);
}

.input-shell-title {
    color: #e5e7eb;
    font-size: 0.95rem;
    font-weight: 700;
    margin-bottom: 0.4rem;
}

.handle-chip {
    display: inline-block;
    margin: 0.15rem 0.2rem;
    padding: 0.2rem 0.55rem;
    border-radius: 999px;
    background: #111827;
    border: 1px solid #374151;
    color: #e5e7eb;
    font-size: 0.82rem;
    font-weight: 600;
}

.action-shell {
    max-width: 960px;
    margin: 0.4rem auto 1.3rem auto;
    text-align: center;
}

.action-caption {
    color: #94a3b8;
    font-size: 0.9rem;
    margin-top: 0.35rem;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 0.35rem;
}

.stTabs [data-baseweb="tab"] {
    background: #111827;
    color: #e5e7eb;
    border-radius: 10px 10px 0 0;
    padding: 0.5rem 0.85rem;
}

.stTabs [aria-selected="true"] {
    background: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #e5e7eb;
    border-bottom: none;
}
</style>
""",
    unsafe_allow_html=True,
)


# UI: Session state defaults
DEFAULT_STATE = {
    "pipeline_state": {},
    "final_recommendations": {},
    "available_trends": [],
    "selected_trend": "",
    "regeneration_error": "",
    "custom_trend_value": "",
    "run_complete": False,
    "active_trend": "",
    "cached_results": {},
    "dismissed_banner": False,
    "market_trends": [],
    "last_run_time": "",
    "cache_status": "N/A",
    "primary_url_input": "",
    "competitor_urls_input": "",
    "links_locked": False,
    "committed_primary_url": "",
    "committed_competitors": [],
}
for _key, _value in DEFAULT_STATE.items():
    if _key not in st.session_state:
        st.session_state[_key] = _value


# UI: Cached pipeline invocation for scraped/fetched result payloads
@st.cache_data(show_spinner=False)
def _run_pipeline_cached(primary_url: str, competitors_tuple: tuple):
    app_graph = build_graph()
    initial_state = {
        "primary_ig_url": primary_url,
        "competitor_ig_urls": list(competitors_tuple),
        "errors": [],
    }
    return app_graph.invoke(initial_state)


def _extract_numeric_rating(value):
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"(\d+(?:\.\d+)?)", value)
        if match:
            return float(match.group(1))
    return None


def _extract_competitor_avg(text_value):
    if not isinstance(text_value, str):
        return None

    pattern_ratio = re.search(r"(\d+(?:\.\d+)?)\s*/\s*10", text_value)
    if pattern_ratio:
        return float(pattern_ratio.group(1))

    pattern_avg = re.search(r"average[^\d]*(\d+(?:\.\d+)?)", text_value.lower())
    if pattern_avg:
        return float(pattern_avg.group(1))

    return None


def _extract_strategy_sections(report_text: str):
    sections = {
        "Executive Summary": "",
        "Top 3 Fixes": "",
        "Double Down On": "",
        "30-Day Plan": "",
    }

    if not report_text:
        return sections

    lines = report_text.splitlines()
    current = "Executive Summary"
    for line in lines:
        cleaned = line.strip().lower().lstrip("#").strip()
        if "executive summary" in cleaned:
            current = "Executive Summary"
            continue
        if "top 3" in cleaned and "fix" in cleaned:
            current = "Top 3 Fixes"
            continue
        if "double down" in cleaned:
            current = "Double Down On"
            continue
        if "30-day" in cleaned or "30 day" in cleaned:
            current = "30-Day Plan"
            continue
        sections[current] = f"{sections[current]}\n{line}".strip()

    if not any(sections.values()):
        sections["Executive Summary"] = report_text

    return sections


def _extract_handle(url_value: str) -> str:
    raw = (url_value or "").strip().rstrip("/")
    if not raw:
        return ""

    if "instagram.com/" in raw.lower():
        tail = raw.split("instagram.com/")[-1]
        handle = tail.split("/")[0].split("?")[0].strip("@")
        return handle.lower()

    return raw.replace("@", "").split("/")[-1].lower()


def _render_step_indicator(placeholder, active_idx: int):
    steps = ["Scraping IG", "Fetching Trends", "Analyzing", "Generating Posts", "Done"]
    chips = []
    for idx, step in enumerate(steps):
        if idx < active_idx:
            css_class = "step-chip done"
            label = f"{step}"
        elif idx == active_idx:
            css_class = "step-chip active"
            label = f"{step}"
        else:
            css_class = "step-chip"
            label = f"{step}"
        chips.append(f'<span class="{css_class}">{label}</span>')

    placeholder.markdown(
        f"<div class='progress-steps'>{''.join(chips)}</div>",
        unsafe_allow_html=True,
    )


def _run_post_regeneration(trend_value: str) -> None:
    trend = (trend_value or "").strip()
    if not trend:
        st.session_state.regeneration_error = "Please select or enter a trend first."
        return

    base_state = st.session_state.pipeline_state
    if not base_state:
        st.session_state.regeneration_error = "Run the full analysis first."
        return

    regen_state = dict(base_state)
    regen_state["selected_trend"] = trend
    regen_state["final_recommendations"] = st.session_state.final_recommendations

    with st.spinner(f"Regenerating curated posts for trend: {trend}"):
        node_output = regenerate_post_prompts_node(regen_state)

    regen_error = node_output.get("regeneration_error", "")
    if regen_error:
        st.session_state.regeneration_error = regen_error
        return

    st.session_state.regeneration_error = ""
    st.session_state.selected_trend = trend
    st.session_state.active_trend = trend
    st.session_state.final_recommendations = node_output.get(
        "final_recommendations", st.session_state.final_recommendations
    )
    st.session_state.pipeline_state.update(
        {
            "selected_trend": trend,
            "final_recommendations": st.session_state.final_recommendations,
            "regenerated_post_prompts": node_output.get("regenerated_post_prompts", {}),
        }
    )

    existing = st.session_state.available_trends
    normalized = {item.lower() for item in existing}
    if trend.lower() not in normalized:
        st.session_state.available_trends = [trend, *existing]

    st.session_state.market_trends = st.session_state.available_trends


# ── UI: Landing hero (only when no results yet) ──────────────────────────────
if not st.session_state.final_recommendations:
    st.markdown(
        """
<div class="hero-wrap">
  <div class="hero-title">✨ Content Strategy Agent</div>
  <div class="hero-subtitle">
    Enter your Instagram handle and competitors — get a full competitive analysis,<br/>
    actionable post briefs, and a 30-day content plan in one click.
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    col_l, col_mid, col_r = st.columns([0.2, 6, 0.2])
    with col_mid:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(
                """
<div class="hero-card">
  <div class="hero-card-icon">📊</div>
  <div class="hero-card-title">Competitive Snapshot</div>
  <div class="hero-card-text">Scores your profile against competitors and surfaces the highest-impact gaps to close.</div>
</div>
""",
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                """
<div class="hero-card">
  <div class="hero-card-icon">🔍</div>
  <div class="hero-card-title">Trend-Aware Planning</div>
  <div class="hero-card-text">Fetches live market trends and weaves them into your content strategy automatically.</div>
</div>
""",
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                """
<div class="hero-card">
  <div class="hero-card-icon">📝</div>
  <div class="hero-card-title">Ready-To-Post Briefs</div>
  <div class="hero-card-text">Delivers 5 complete post briefs with hooks, captions, hashtags, timing, and CTAs.</div>
</div>
""",
                unsafe_allow_html=True,
            )

    # How it works steps
    st.markdown(
        """
<div class="how-it-works">
  <div class="how-it-works-title">How It Works</div>
  <div class="how-steps-row">
    <div class="how-step">
      <div class="how-step-num">1</div>
      <div class="how-step-label">Enter Links</div>
      <div class="how-step-desc">Add your Instagram URL and competitor URLs below</div>
    </div>
    <div class="how-step-arrow">→</div>
    <div class="how-step">
      <div class="how-step-num">2</div>
      <div class="how-step-label">AI Analysis</div>
      <div class="how-step-desc">Our LLM council scrapes, analyzes, and synthesizes insights</div>
    </div>
    <div class="how-step-arrow">→</div>
    <div class="how-step">
      <div class="how-step-num">3</div>
      <div class="how-step-label">Get Results</div>
      <div class="how-step-desc">Review your strategy report, gap analysis, and post prompts</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


# ── UI: URL capture and handle summary ────────────────────────────────────────
run_btn = False  # Default; set by the generate/re-run buttons below
if not st.session_state.links_locked:
    st.markdown("<div class='input-shell'>", unsafe_allow_html=True)
    st.markdown("<div class='input-shell-title'>📎 Instagram Links</div>", unsafe_allow_html=True)
    with st.form("url-entry-form", clear_on_submit=False):
        st.text_input(
            "Your Instagram URL",
            key="primary_url_input",
            placeholder="https://instagram.com/your_handle",
        )
        st.text_area(
            "Competitor URLs (one per line)",
            key="competitor_urls_input",
            placeholder="https://instagram.com/competitor1\nhttps://instagram.com/competitor2",
            height=100,
        )
        enter_urls = st.form_submit_button("Lock Links & Continue →", type="primary")

    if enter_urls:
        entered_primary = st.session_state.primary_url_input.strip()
        entered_competitors = [
            item.strip()
            for item in st.session_state.competitor_urls_input.split("\n")
            if item.strip()
        ]
        if not entered_primary:
            st.error("Please provide your Instagram URL before pressing Enter.")
        elif not entered_competitors:
            st.error("Please provide at least one competitor URL before pressing Enter.")
        else:
            st.session_state.committed_primary_url = entered_primary
            st.session_state.committed_competitors = entered_competitors
            st.session_state.links_locked = True
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
else:
    your_handle = _extract_handle(st.session_state.committed_primary_url)
    comp_handles = [_extract_handle(url) for url in st.session_state.committed_competitors]

    if st.session_state.final_recommendations:
        # Compact inline bar when results are already showing
        handles_html = ""
        if your_handle:
            handles_html += f"<span class='handle-chip handle-brand'>@{your_handle}</span>"
        for handle in comp_handles:
            if handle:
                handles_html += f"<span class='handle-chip'>@{handle}</span>"
        bar_left, bar_right = st.columns([5, 1.5])
        with bar_left:
            st.markdown(
                f"<div style='padding: 0.4rem 0'>{handles_html}</div>",
                unsafe_allow_html=True,
            )
        with bar_right:
            edit_col, rerun_col = st.columns(2)
            with edit_col:
                if st.button("✏️ Edit", key="edit-links-btn", use_container_width=True):
                    st.session_state.links_locked = False
                    st.rerun()
            with rerun_col:
                run_btn = st.button("🔄 Re-run", key="generate-strategy-main", use_container_width=True)
    else:
        # Full locked-handles display before first run
        st.markdown("<div class='input-shell'>", unsafe_allow_html=True)
        st.markdown("<div class='input-shell-title'>✅ Locked Handles</div>", unsafe_allow_html=True)
        handles_html = ""
        if your_handle:
            handles_html += f"<span class='handle-chip handle-brand'>@{your_handle}</span>"
        for handle in comp_handles:
            if handle:
                handles_html += f"<span class='handle-chip'>@{handle}</span>"
        st.markdown(f"<div style='margin: 0.3rem 0 0.5rem 0'>{handles_html}</div>", unsafe_allow_html=True)

        if st.button("✏️ Edit links", key="edit-links-btn"):
            st.session_state.links_locked = False
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


if st.session_state.links_locked:
    primary_url = st.session_state.committed_primary_url.strip()
    competitors = [item.strip() for item in st.session_state.committed_competitors if item.strip()]
else:
    primary_url = st.session_state.primary_url_input.strip()
    competitors = [
        item.strip()
        for item in st.session_state.competitor_urls_input.split("\n")
        if item.strip()
    ]


# ── UI: Generate action button (only prominent before first results) ──────────
if not st.session_state.final_recommendations:
    st.markdown("<div class='action-shell'>", unsafe_allow_html=True)
    run_col_left, run_col_center, run_col_right = st.columns([2.7, 2, 2.7])
    with run_col_center:
        run_btn = st.button(
            "🚀 Generate Strategy",
            key="generate-strategy-main",
            type="primary",
            use_container_width=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


# ── UI: Running state with progress updates ──────────────────────────────────
if run_btn:
    if not st.session_state.links_locked:
        st.warning("Press 'Lock Links & Continue' in the form above before running the pipeline.")
        st.stop()

    if not primary_url:
        st.error("Please provide your Instagram URL.")
        st.stop()

    if not competitors:
        st.error("Please provide at least one competitor URL.")
        st.stop()

    progress_bar = st.progress(0)
    steps_placeholder = st.empty()
    eta_placeholder = st.empty()

    _render_step_indicator(steps_placeholder, 0)
    eta_placeholder.caption("~5 min remaining")
    progress_bar.progress(12)
    time.sleep(0.1)

    _render_step_indicator(steps_placeholder, 1)
    eta_placeholder.caption("~4 min remaining")
    progress_bar.progress(26)
    time.sleep(0.1)

    _render_step_indicator(steps_placeholder, 2)
    eta_placeholder.caption("~3 min remaining")
    progress_bar.progress(42)
    time.sleep(0.1)

    _render_step_indicator(steps_placeholder, 3)
    eta_placeholder.caption("~2 min remaining")
    progress_bar.progress(60)

    cache_key = f"{primary_url}|{'|'.join(competitors)}"
    is_cache_hit = cache_key in st.session_state.cached_results

    try:
        result = _run_pipeline_cached(primary_url, tuple(competitors))
    except Exception as exc:
        st.error(f"Failed to run pipeline: {exc}")
        st.stop()

    if result.get("errors"):
        st.error("The pipeline encountered errors during execution:")
        for err in result["errors"]:
            st.write(f"- {err}")
        st.stop()

    recs = result.get("final_recommendations", {})
    if not recs:
        st.error("Pipeline finished but no recommendations were found.")
        st.stop()

    _render_step_indicator(steps_placeholder, 4)
    eta_placeholder.caption("Done")
    progress_bar.progress(100)

    st.session_state.pipeline_state = result
    st.session_state.final_recommendations = recs
    st.session_state.available_trends = result.get("available_trends", [])
    st.session_state.selected_trend = result.get("selected_trend", "")
    st.session_state.active_trend = st.session_state.selected_trend
    st.session_state.market_trends = st.session_state.available_trends
    st.session_state.regeneration_error = ""
    st.session_state.run_complete = True
    st.session_state.dismissed_banner = False
    st.session_state.last_run_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    st.session_state.cache_status = "Hit" if is_cache_hit else "Miss"
    st.session_state.cached_results[cache_key] = True


# UI: Results state with structured tabs
if st.session_state.final_recommendations:
    recs = st.session_state.final_recommendations
    report = recs.get("strategy_report", "")
    gap_analysis = recs.get("gap_analysis", {})
    prompts = recs.get("post_prompts", {}).get("posts", [])
    councilor_notes = recs.get("councilor_notes", "")

    if not st.session_state.dismissed_banner:
        banner_left, banner_right = st.columns([6, 1])
        with banner_left:
            st.markdown(
                """
<div class="complete-banner">
  <strong>✅ Analysis Complete</strong><br/>
  Your content strategy pipeline has finished successfully. Review results in the tabs below.
</div>
""",
                unsafe_allow_html=True,
            )
        with banner_right:
            if st.button("Dismiss", key="dismiss-analysis-banner", use_container_width=True):
                st.session_state.dismissed_banner = True
                st.rerun()

    st.divider()

    tab_report, tab_gaps, tab_posts, tab_notes = st.tabs(
        ["📋 Strategic Report", "📊 Gap Analysis", "📝 Post Prompts", "🧠 Councilor Notes"]
    )

    # ── Tab 1: Strategic Report ──────────────────────────────────────────────
    with tab_report:
        strategy_sections = _extract_strategy_sections(report)
        section_icons = {
            "Executive Summary": "📌",
            "Top 3 Fixes": "🔧",
            "Double Down On": "🚀",
            "30-Day Plan": "📅",
        }
        for title in ["Executive Summary", "Top 3 Fixes", "Double Down On", "30-Day Plan"]:
            icon = section_icons.get(title, "•")
            st.markdown(
                f"<div class='section-card'><div class='section-title'>{icon}  {title}</div>",
                unsafe_allow_html=True,
            )
            section_content = strategy_sections.get(title, "")
            if section_content:
                # Ensure bullet-point formatting for lines that look like list items
                formatted_lines = []
                for line in section_content.splitlines():
                    stripped = line.strip()
                    if not stripped:
                        continue
                    # Already a markdown list item or heading — keep as-is
                    if stripped.startswith(("-", "*", "•", "#", "1", "2", "3", "4", "5", "6", "7", "8", "9")):
                        formatted_lines.append(line)
                    else:
                        formatted_lines.append(line)
                st.markdown("\n".join(formatted_lines))
            else:
                st.info("No details provided for this section in the current report.")
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Tab 2: Gap Analysis ──────────────────────────────────────────────────
    with tab_gaps:
        score_data = gap_analysis.get("overall_score", {})
        brand_raw = score_data.get("brand_rating", "N/A")
        vs_comp_text = score_data.get("vs_competitors", "No comparison data available.")

        brand_num = _extract_numeric_rating(brand_raw)
        comp_avg = _extract_competitor_avg(vs_comp_text)

        metric_delta = None
        if brand_num is not None and comp_avg is not None:
            metric_delta = f"{brand_num - comp_avg:+.1f} vs competitor avg"

        # ── Score header ──
        metric_col, badge_col = st.columns([1.2, 3])
        with metric_col:
            st.metric(
                "Brand Rating",
                f"{brand_raw}/10" if brand_raw != "N/A" else "N/A",
                delta=metric_delta,
            )
        with badge_col:
            if brand_num is None:
                badge_class, badge_label = "rating-mid", "Rating unavailable"
            elif brand_num >= 8:
                badge_class, badge_label = "rating-strong", "Strong Position"
            elif brand_num >= 6:
                badge_class, badge_label = "rating-mid", "Competitive — room to improve"
            else:
                badge_class, badge_label = "rating-low", "Needs immediate attention"

            st.markdown(
                f"<span class='rating-badge {badge_class}'>{badge_label}</span>",
                unsafe_allow_html=True,
            )
            st.caption(vs_comp_text)

        st.divider()

        # ── Strengths & Weaknesses side-by-side ──
        strengths_col, weaknesses_col = st.columns(2)
        with strengths_col:
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>💪 Strengths</div>", unsafe_allow_html=True)
            strengths = gap_analysis.get("strengths", [])
            if strengths:
                for strength in strengths:
                    area = strength.get("area", "Strength")
                    score = strength.get("score", "-")
                    evidence = strength.get("evidence", "No detail provided.")
                    st.markdown(
                        f"""
- **{area}** — Score: `{score}/10`
  - {evidence}
""",
                    )
            else:
                st.info("No strengths data available.")
            st.markdown("</div>", unsafe_allow_html=True)

        with weaknesses_col:
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>⚠️ Weaknesses</div>", unsafe_allow_html=True)
            weaknesses = gap_analysis.get("weaknesses", [])
            if weaknesses:
                for weakness in weaknesses:
                    area = weakness.get("area", "Weakness")
                    impact = weakness.get("impact", "unknown").upper()
                    evidence = weakness.get("evidence", "No detail provided.")
                    impact_color = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(impact, "⚪")
                    st.markdown(
                        f"""
- **{area}** — Impact: {impact_color} `{impact}`
  - {evidence}
""",
                    )
            else:
                st.info("No weaknesses data available.")
            st.markdown("</div>", unsafe_allow_html=True)

        st.divider()

        # ── Competitor Advantages ──
        competitor_advantages = gap_analysis.get("competitor_advantages", [])
        if competitor_advantages:
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            st.markdown(
                "<div class='section-title'>🏆 Competitor Advantages</div>",
                unsafe_allow_html=True,
            )
            for adv in competitor_advantages:
                competitor = adv.get("competitor", "Competitor")
                advantage = adv.get("advantage", "N/A")
                counter = adv.get("how_to_counter", "N/A")
                st.markdown(
                    f"""
- **@{competitor}** — {advantage}
  - 🎯 *Counter-strategy:* {counter}
""",
                )
            st.markdown("</div>", unsafe_allow_html=True)
            st.divider()

        # ── Quick Wins ──
        quick_wins = gap_analysis.get("quick_wins", [])
        if quick_wins:
            st.markdown("<div class='section-card'>", unsafe_allow_html=True)
            st.markdown(
                "<div class='section-title'>⚡ Quick Wins</div>",
                unsafe_allow_html=True,
            )
            for qw in quick_wins:
                action = qw.get("action", "Action")
                expected_impact = qw.get("expected_impact", "N/A")
                effort = qw.get("effort", "unknown").upper()
                effort_icon = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(effort, "⚪")
                st.markdown(
                    f"""
- **{action}**
  - 📈 *Expected impact:* {expected_impact}
  - {effort_icon} *Effort:* `{effort}`
""",
                )
            st.markdown("</div>", unsafe_allow_html=True)
            st.divider()

        # ── Market Opportunities ──
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown(
            "<div class='section-title'>🌐 Market Opportunities</div>",
            unsafe_allow_html=True,
        )
        opportunities = gap_analysis.get("market_opportunities", [])
        if opportunities:
            for opp in opportunities:
                opportunity = opp.get("opportunity", "Opportunity")
                signal = opp.get("trend_signal", "N/A")
                urgency = opp.get("urgency", "unknown").upper()
                urgency_icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(urgency, "⚪")
                st.markdown(
                    f"""
- **{opportunity}**
  - 📡 *Trend signal:* {signal}
  - {urgency_icon} *Urgency:* `{urgency}`
""",
                )
        else:
            st.info("No market opportunities provided.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Tab 3: Post Prompts ──────────────────────────────────────────────────
    with tab_posts:
        st.markdown(
            "<div class='section-title'>🎯 Filter by Trend</div>",
            unsafe_allow_html=True,
        )
        market_trends = st.session_state.market_trends
        active_trend = st.session_state.active_trend or st.session_state.selected_trend

        if market_trends:
            for i in range(0, len(market_trends), 4):
                row = market_trends[i : i + 4]
                trend_cols = st.columns(4)
                for j, trend in enumerate(row):
                    is_active = trend == active_trend
                    button_label = f"✅ {trend}" if is_active else trend
                    button_type = "primary" if is_active else "secondary"
                    with trend_cols[j]:
                        if st.button(
                            button_label,
                            key=f"trend-pill-{i}-{j}",
                            type=button_type,
                            use_container_width=True,
                        ):
                            _run_post_regeneration(trend)
        else:
            st.info("No detected trends yet. Use the custom trend field below.")

        regen_left, regen_right = st.columns([3, 1])
        with regen_left:
            st.text_input(
                "Custom trend",
                key="custom_trend_value",
                placeholder="e.g. behind-the-scenes product demos",
            )
        with regen_right:
            st.markdown("<div style='height: 1.65rem'></div>", unsafe_allow_html=True)
            if st.button("Regenerate", key="custom-trend-regenerate", type="primary", use_container_width=True):
                _run_post_regeneration(st.session_state.custom_trend_value)

        if st.session_state.regeneration_error:
            st.warning(st.session_state.regeneration_error)
        elif active_trend:
            st.markdown(
                f"<span class='active-trend-badge'>Active trend: {active_trend}</span>",
                unsafe_allow_html=True,
            )

        st.divider()

        if prompts:
            for idx, post in enumerate(prompts):
                post_num = post.get("post_number", idx + 1)
                post_format = post.get("format", "Post")
                gap = post.get("gap_addressed", "No gap summary")

                format_icons = {"Reel": "🎬", "Carousel": "🖼️", "Static Image": "📸"}
                fmt_icon = format_icons.get(post_format, "📝")

                expander_title = f"{fmt_icon}  Post #{post_num}  ·  {post_format}  ·  {gap}"

                with st.expander(expander_title, expanded=idx == 0):
                    # Top row: format + timing
                    meta_left, meta_right = st.columns(2)
                    with meta_left:
                        st.markdown(f"**📋 Format:** `{post_format}`")
                        st.markdown(f"**🎯 Gap Addressed:** {post.get('gap_addressed', 'N/A')}")
                    with meta_right:
                        st.markdown(f"**🕐 Best Time to Post:** {post.get('posting_time', 'N/A')}")
                        st.markdown(f"**📣 CTA:** {post.get('call_to_action', 'N/A')}")

                    st.divider()

                    # Creative details
                    st.markdown(f"**🪝 Hook:**  \n> {post.get('hook', 'N/A')}")
                    st.markdown(f"**💡 Concept:**  \n> {post.get('concept', 'N/A')}")
                    st.markdown(f"**🏆 Why This Wins:**  \n> {post.get('why_this_wins', 'N/A')}")

                    st.divider()

                    # Caption
                    st.markdown("**✍️ Caption:**")
                    st.code(post.get("caption", ""), language="markdown")

                    # Hashtags
                    hashtags = post.get("hashtags", [])
                    if hashtags:
                        tags_html = " ".join(
                            f"<span class='handle-chip'>#{tag}</span>" for tag in hashtags
                        )
                        st.markdown(f"**#️⃣ Hashtags:**", unsafe_allow_html=True)
                        st.markdown(tags_html, unsafe_allow_html=True)
        else:
            st.info("No post prompts available.")

    # ── Tab 4: Councilor Notes ───────────────────────────────────────────────
    with tab_notes:
        st.markdown(
            "<div class='section-card'>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='section-title'>🧠 AI Council Synthesis Notes</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            "These notes explain how the AI council resolved disagreements "
            "between GPT and Gemini models to produce the final strategy."
        )

        if isinstance(councilor_notes, dict):
            # Structured dict path (unlikely with current schema, but kept for safety)
            confidence = councilor_notes.get("confidence_scores", {})
            if confidence:
                st.markdown("**📊 Confidence Scores:**")
                st.table(
                    [
                        {"Councilor": name, "Confidence": score}
                        for name, score in confidence.items()
                    ]
                )
                st.divider()

            deliberations = councilor_notes.get("deliberations", [])
            if deliberations:
                for idx, note in enumerate(deliberations, start=1):
                    title = note.get("councilor", f"Councilor {idx}")
                    with st.expander(title, expanded=False):
                        st.markdown(note.get("note", "No note provided."))
            elif councilor_notes:
                # Dict but no known keys — render key-value pairs cleanly
                for key, value in councilor_notes.items():
                    st.markdown(f"- **{key}:** {value}")

        elif isinstance(councilor_notes, list):
            for idx, note in enumerate(councilor_notes, start=1):
                st.markdown(f"**Point {idx}:**")
                st.markdown(f"> {note}")

        elif isinstance(councilor_notes, str) and councilor_notes.strip():
            # Primary path: the MasterReport schema defines councilor_notes as a string.
            # Parse into bullet points for clean presentation.
            note_lines = councilor_notes.strip().splitlines()
            cleaned_points = []
            for line in note_lines:
                stripped = line.strip()
                if not stripped:
                    continue
                # Strip existing bullet markers for uniform formatting
                if stripped.startswith(("-", "•", "*")):
                    stripped = stripped.lstrip("-•* ").strip()
                cleaned_points.append(stripped)

            if len(cleaned_points) <= 1:
                # Single paragraph — render as a blockquote
                st.markdown(f"> {councilor_notes.strip()}")
            else:
                for point in cleaned_points:
                    st.markdown(f"- {point}")
        else:
            st.info("No councilor notes available for this analysis.")

        st.markdown("</div>", unsafe_allow_html=True)
