import streamlit as st
from orchestrator.graph import build_graph

# ---------------------------------------------------------
# PAGE SETUP
# ---------------------------------------------------------
st.set_page_config(
    page_title="Content Strategy Agent",
    page_icon="✨",
    layout="wide"
)

# Apply some custom CSS for styling
st.markdown("""
<style>
.stAlert { padding: 1rem; }
.metric-container {
    background-color: #1E1E1E;
    padding: 1.5rem;
    border-radius: 8px;
    margin-bottom: 1rem;
    color: white;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------
with st.sidebar:
    st.title("✨ Content Strategy Agent")
    st.markdown("Automate your Instagram research and content ideation using competitive intelligence and market trends.")
    
    st.header("Inputs")
    primary_url = st.text_input(
        "Your Instagram URL",
        placeholder="https://instagram.com/your_handle"
    )
    
    st.markdown("---")
    st.write("**Competitor URLs** (one per line)")
    competitor_input = st.text_area(
        "",
        placeholder="https://instagram.com/competitor1\nhttps://instagram.com/competitor2",
        height=150
    )
    
    run_btn = st.button("Generate Strategy", type="primary", use_container_width=True)

# ---------------------------------------------------------
# MAIN APP LOGIC
# ---------------------------------------------------------

if not run_btn:
    st.markdown("## 👋 Welcome!")
    st.info("Enter your Instagram URL and your competitors' URLs in the sidebar to generate a complete content strategy.")

else:
    # 1. Input Validation
    competitors = [u.strip() for u in competitor_input.split('\n') if u.strip()]
    
    if not primary_url:
        st.error("⚠️ Please provide your Instagram URL.")
        st.stop()
    if not competitors:
        st.error("⚠️ Please provide at least one competitor URL.")
        st.stop()
        
    initial_state = {
        "primary_ig_url": primary_url,
        "competitor_ig_urls": competitors,
        "errors": []
    }
    
    # 2. Run LangGraph Pipeline
    app_graph = build_graph()
    
    with st.spinner("Analyzing intelligence and generating strategy... this may take 1-3 minutes."):
        # We wrap in try to catch unexpected crashes, though the graph handles its own errors
        try:
            result = app_graph.invoke(initial_state)
        except Exception as e:
            st.error(f"Failed to run pipeline: {e}")
            st.stop()
            
    # 3. Handle Errors
    if result.get("errors"):
        st.error("The pipeline encountered errors during execution:")
        for err in result["errors"]:
            st.write(f"- {err}")
        st.stop()
        
    # 4. Display Results
    recs = result.get("final_recommendations", {})
    if not recs:
        st.error("Pipeline finished but no recommendations were found.")
        st.stop()
        
    st.success("Analysis Complete!")
    
    # Extract components
    report = recs.get("strategy_report", "")
    gap_analysis = recs.get("gap_analysis", {})
    prompts = recs.get("post_prompts", {}).get("posts", [])
    councilor_notes = recs.get("councilor_notes", "")
    
    tab_report, tab_gaps, tab_posts, tab_notes = st.tabs([
        "📄 Strategic Report", 
        "🔍 Gap Analysis", 
        "📸 Post Prompts",
        "🧠 Councilor Notes"
    ])
    
    # --- TAB 1: STRATEGIC REPORT ---
    with tab_report:
        st.markdown("### Executive Strategy")
        st.markdown(report)
        
    # --- TAB 2: GAP ANALYSIS ---
    with tab_gaps:
        # Top level scores
        score_data = gap_analysis.get('overall_score', {})
        st.markdown("### Overall Assessment")
        col1, col2 = st.columns([1, 3])
        with col1:
            st.metric("Brand Rating", f"{score_data.get('brand_rating', 'N/A')}/10")
        with col2:
            st.info(score_data.get('vs_competitors', 'No comparison data available.'))
            
        st.markdown("---")
        
        # Strengths & Weaknesses
        col_s, col_w = st.columns(2)
        with col_s:
            st.subheader("💪 Strengths")
            for s in gap_analysis.get('strengths', []):
                with st.expander(f"{s.get('area')} (Score: {s.get('score')}/10)"):
                    st.write(s.get('evidence'))
                    
        with col_w:
            st.subheader("⚠️ Weaknesses")
            for w in gap_analysis.get('weaknesses', []):
                with st.expander(f"{w.get('area')} (Impact: {w.get('impact', '').upper()})"):
                    st.write(w.get('evidence'))
                    
        st.markdown("---")
        
        # Competitor Advantages
        st.subheader("🏆 What Competitors Do Better")
        for adv in gap_analysis.get('competitor_advantages', []):
            st.markdown(f"**{adv.get('competitor')}**: {adv.get('advantage')}")
            st.markdown(f"👉 *How to counter:* {adv.get('how_to_counter')}")
            st.write("")
            
        st.markdown("---")
        
        # Quick Wins & Market Opps
        col_qw, col_opp = st.columns(2)
        with col_qw:
            st.subheader("🚀 Quick Wins")
            for qw in gap_analysis.get('quick_wins', []):
                st.markdown(f"**Action:** {qw.get('action')}")
                st.markdown(f"**Impact:** {qw.get('expected_impact')} (Effort: {qw.get('effort')})")
                st.write("")
                
        with col_opp:
            st.subheader("📈 Market Opportunities")
            for op in gap_analysis.get('market_opportunities', []):
                st.markdown(f"**Opportunity:** {op.get('opportunity')}")
                st.markdown(f"**Signal:** {op.get('trend_signal')} (Urgency: {op.get('urgency')})")
                st.write("")
                
    # --- TAB 3: POST PROMPTS ---
    with tab_posts:
        st.markdown("### Ready-to-Shoot Content Briefs")
        st.caption("These prompts are tailored specifically to exploit the identified market gaps.")
        
        for idx, post in enumerate(prompts):
            with st.container():
                st.markdown(f"#### Post #{post.get('post_number', idx+1)}: {post.get('format', 'Feed')}")
                
                col_a, col_b = st.columns([1, 1])
                
                with col_a:
                    st.write(f"**🎯 Gap Addressed:** {post.get('gap_addressed')}")
                    st.write(f"**🎬 Hook:** {post.get('hook')}")
                    st.write(f"**💡 Concept:** {post.get('concept')}")
                    
                with col_b:
                    st.write(f"**🏆 Why It Wins:** {post.get('why_this_wins')}")
                    st.write(f"**⏰ Best Time:** {post.get('posting_time')}")
                    st.write(f"**👇 CTA:** {post.get('call_to_action')}")
                    
                st.markdown("**Caption:**")
                st.code(post.get('caption'), language="markdown")
                
                st.markdown(f"**Hashtags:** `{'` `'.join(post.get('hashtags', []))}`")
                st.divider()

    # --- TAB 4: COUNCILOR NOTES ---
    with tab_notes:
        st.markdown("### Opus Council Meta-Commentary")
        st.info("This section shows Claude Opus's internal thought process as the council chairman, explaining how it resolved disagreements between GPT-OSS and Claude Sonnet.")
        st.markdown(councilor_notes)
