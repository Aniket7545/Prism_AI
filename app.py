# app.py - Multi-page Streamlit Application for BrandGuard AI
import streamlit as st
import os, uuid, time, json
from datetime import datetime
from workflow import create_workflow
from utils.loaders import extract_text_from_file
from services.database import audit_db
import pandas as pd

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="BrandGuard AI - Enterprise Content Operations",
    layout="wide", initial_sidebar_state="expanded"
)

# --- CACHING ---
@st.cache_resource
def get_workflow_app():
    return create_workflow()

@st.cache_resource
def get_audit_db():
    return audit_db

app = get_workflow_app()
db = get_audit_db()

# --- SESSION STATE ---
st.session_state.setdefault("session_id", str(uuid.uuid4()))
st.session_state.setdefault("workflow_state", None)
st.session_state.setdefault("page", "create")

st.title("🤖 BrandGuard AI - Enterprise Content Operations")
st.markdown("**AI-Powered Content Automation with Compliance Guardrails**")

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.header("Navigation")
    page_select = st.radio(
        "Select Page",
        ["📝 Create Content", "📊 Analytics", "📚 Content Library", "🔍 Audit Trail", "⚙️ Settings"]
    )
    
    st.divider()
    st.info(f"**Active Session**: `{st.session_state.session_id[:12]}`")
    
    if st.button("🔄 New Session", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

# --- PAGE ROUTING ---
if page_select == "📝 Create Content":
    st.session_state.page = "create"
elif page_select == "📊 Analytics":
    st.session_state.page = "analytics"
elif page_select == "📚 Content Library":
    st.session_state.page = "library"
elif page_select == "🔍 Audit Trail":
    st.session_state.page = "audit"
else:
    st.session_state.page = "settings"

# ============================================
# PAGE 1: CREATE CONTENT
# ============================================
if st.session_state.page == "create":
    st.subheader("📝 Create & Process Content")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        channel = st.selectbox("📢 Channel", ["LinkedIn", "Blog", "Email", "Press Release", "Twitter"])
    with col2:
        region = st.selectbox("🌍 Region", ["Global", "India", "US", "EU", "APAC"])
    with col3:
        content_type = st.selectbox("📄 Type", ["Article", "Social", "Newsletter", "Release"])
    with col4:
        urgency = st.selectbox("⏰ Urgency", ["Low", "Medium", "High"])
    
    st.divider()
    
    col1, col2 = st.columns([2, 1])
    with col1:
        input_method = st.radio("Input", ["Paste Text", "Upload File"], horizontal=True)
        
        if input_method == "Paste Text":
            raw_content = st.text_area("Raw Content", height=250)
            input_file = "text_input"
        else:
            uploaded_file = st.file_uploader("Upload (TXT/PDF)", type=["txt", "pdf"])
            if uploaded_file:
                input_file = uploaded_file.name
                raw_content = extract_text_from_file(uploaded_file)
                st.success(f"✓ Loaded {len(raw_content)} characters")
            else:
                raw_content = ""
                input_file = ""
        
        topic = st.text_input("Topic", placeholder="E.g., 'AI in Enterprise'")
    
    with col2:
        st.metric("Words", len(raw_content.split()) if raw_content else 0)
        st.metric("Chars", len(raw_content) if raw_content else 0)
        st.metric("Read Time", f"~{max(1, len(raw_content.split()) // 200)}m" if raw_content else "0m")
    
    st.divider()
    
    if st.button("▶️ START WORKFLOW", type="primary", use_container_width=True):
        if not raw_content or not topic:
            st.error("Provide content and topic")
        else:
            st.info("⏳ Processing...")
            
            initial_state = {
                "session_id": st.session_state.session_id,
                "input_file_path": input_file,
                "raw_content": raw_content,
                "topic": topic,
                "target_channel": channel,
                "target_region": region,
                "draft_content": "",
                "compliance_report": {},
                "localization_content": "",
                "published_url": "",
                "audit_log": [],
                "iteration_count": 0,
                "human_approval": "pending",
                "human_feedback": "",
                "needs_revision": False,
                "start_time": time.time(),
                "end_time": 0.0,
                "content_metadata": {},
                "content_type": content_type,
                "structured_data": {},
                "engagement_metrics": {},
                "performance_analysis": {},
                "insights": {},
                "human_feedback_severity": "medium"
            }
            
            try:
                db.create_session(st.session_state.session_id, topic, channel, region, content_type)
                
                # Run workflow
                for step, state_dict in enumerate(app.stream(initial_state, {"recursion_limit": 25})):
                    st.session_state.workflow_state = state_dict
                    step_name = list(state_dict.keys())[0] if state_dict else "step"
                    st.write(f"✓ {step_name}")
                
                st.success("✅ Processing complete!")
                
                # Display results
                if st.session_state.workflow_state:
                    state_data = list(st.session_state.workflow_state.values())[0] if st.session_state.workflow_state else {}
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("📄 Content")
                        st.text_area("Draft", state_data.get("draft_content", ""), height=250, disabled=True)
                    with col2:
                        st.subheader("🛡️ Compliance")
                        report = state_data.get("compliance_report", {})
                        if report.get("passed"):
                            st.success("✅ PASSED")
                        else:
                            st.warning("⚠️ Issues")
                        
                        with st.expander("Details"):
                            st.json(report)
                    
                    st.divider()
                    st.subheader("👤 Approval")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("✅ Approve", type="primary"):
                            st.success("Approved!")
                    with col2:
                        if st.button("📝 Changes"):
                            st.info("Request submitted")
                    with col3:
                        if st.button("❌ Reject"):
                            st.warning("Rejected")
            
            except Exception as e:
                st.error(f"Error: {e}")

# ============================================
# PAGE 2: ANALYTICS
# ============================================
elif st.session_state.page == "analytics":
    st.subheader("📊 Performance Analytics")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Sessions", 12, delta=2)
    with col2:
        st.metric("Compliance Rate", "95%", delta="+5%")
    with col3:
        st.metric("Avg Time", "4m 32s", delta="-2m")
    with col4:
        st.metric("Engagement", "7.2%", delta="+1.5%")
    
    st.divider()
    
    st.info("📈 View detailed analytics, trends, and performance metrics")
    
    # Mock data
    analytics_df = pd.DataFrame({
        "Topic": ["AI Marketing", "Q4 Earnings", "Case Study"],
        "Channel": ["LinkedIn", "Blog", "Email"],
        "Status": ["Published", "Draft", "Approved"],
        "Score": ["92/100", "78/100", "85/100"],
        "Views": [1240, 0, 340]
    })
    
    st.dataframe(analytics_df, use_container_width=True)

# ============================================
# PAGE 3: CONTENT LIBRARY
# ============================================
elif st.session_state.page == "library":
    st.subheader("📚 Content Library")
    
    st.info("📋 Browse all content with versions and history")
    
    # Mock content
    library_items = [
        {"title": "AI Strategy", "channel": "LinkedIn", "status": "Published", "score": "92/100"},
        {"title": "Q4 Earnings", "channel": "Blog", "status": "Draft", "score": "78/100"},
    ]
    
    for item in library_items:
        with st.expander(f"📄 {item['title']} — {item['status']}"):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Score", item["score"])
            with col2:
                st.write(f"**Channel**: {item['channel']}")
            with col3:
                st.write(f"**Status**: {item['status']}")

# ============================================
# PAGE 4: AUDIT TRAIL
# ============================================
elif st.session_state.page == "audit":
    st.subheader("🔍 Audit Trail")
    
    try:
        logs = db.get_session_logs(st.session_state.session_id)
        if logs:
            log_df = pd.DataFrame(logs, columns=["ID", "Time", "Session", "Agent", "Action", "Input", "Output", "Status", "Details"])
            st.dataframe(log_df[["Time", "Agent", "Action", "Status"]], use_container_width=True)
        else:
            st.info("No logs yet")
    except:
        st.info("No logs available")

# ============================================
# PAGE 5: SETTINGS
# ============================================
elif st.session_state.page == "settings":
    st.subheader("⚙️ Settings & Configuration")
    
    tab1, tab2, tab3 = st.tabs(["Brand", "Channels", "System"])
    
    with tab1:
        st.markdown("**Brand Guidelines**")
        voice = st.text_area("Brand Voice", height=100)
        if st.button("Save Brand"):
            st.success("Saved!")
    
    with tab2:
        st.markdown("**Channel Config**")
        channel = st.selectbox("Channel", ["LinkedIn", "Email", "Blog"])
        max_length = st.number_input("Max Length", value=500)
        if st.button("Save Config"):
            st.success("Saved!")
    
    with tab3:
        st.markdown("**System Settings**")
        max_iter = st.slider("Max Iterations", 1, 10, 5)
        if st.button("Save Settings"):
            st.success("Saved!")