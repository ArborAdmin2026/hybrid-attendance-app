import streamlit as st
import pandas as pd
import io
import re

# Set up page configurations with a modern layout
st.set_page_config(
    page_title="Hybrid Attendance Tracker", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize an internal session-safe storage database for the automated form
if 'automated_form_database' not in st.session_state:
    st.session_state['automated_form_database'] = []

# Custom CSS Injection for professional styling
st.markdown("""
    <style>
    .header-banner {
        background: linear-gradient(135deg, #4A00E0 0%, #8E2DE2 100%);
        padding: 30px;
        border-radius: 12px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px !important;
        font-weight: 700 !important;
        color: #4A00E0 !important;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 14px !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    </style>
""", unsafe_allow_html=True)

# Application Top Header Hero Block
st.markdown("""
    <div class="header-banner">
        <h1 style='margin:0; font-size: 32px;'>📊 Hybrid Attendance Data Studio</h1>
        <p style='margin:5px 0 0 0; opacity: 0.9; font-size: 16px;'>
            Consolidate Teams digital exports and manual in-person logs into an elegant, deduplicated master list.
        </p>
    </div>
""", unsafe_allow_html=True)

# Professional Name Cleaning Engine Function
def professional_name_cleaner(name_val):
    if pd.isna(name_val):
        return "Unknown Student"
    text = str(name_val).strip()
    text = re.sub(r'\s*[\(\[][^\]\)]*unverified[^\]\)]*[\)\]]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*[\(\[][^\]\)]*guest[^\]\)]*[\)\]]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*[\(\[][^\]\)]*external[^\]\)]*[\)\]]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    text = " ".join(text.split())
    return text.title()

# Sidebar Area Configuration Panels
st.sidebar.header("⚙️ App Configurations")
class_duration = st.sidebar.number_input("Total Class Duration (mins):", min_value=1, value=60, step=5)
min_benchmark_pct = st.sidebar.slider("Minimum Attendance Threshold (%):", min_value=0, max_value=100, value=75, step=5)

# Step-by-Step Tab Layout Engine Setup
tab1, tab2, tab3, tab4 = st.tabs([
    "📁 Upload & Process", 
    "📝 Automated Check-In Form",
    "📊 Analytics Dashboard", 
    "📋 Master Data Roster"
])

# --- TAB 1: UPLOAD AND CONSOLIDATION HUB ---
with tab1:
    st.subheader("Drag & Drop Attendance Documents")
    st.markdown("Drop **both** your Microsoft Teams report logs and your downloaded Automated Form files here together.")
    uploaded_files = st.file_uploader("Upload files:", type=["xlsx", "csv"], accept_multiple_files=True, label_visibility="collapsed")

    all_dataframes = []
    
    if uploaded_files:
        for file in uploaded_files:
            try:
                fname_lower = file.name.lower()
                if "offline" in fname_lower or "form" in fname_lower or "kiosk" in fname_lower:
                    df = pd.read_csv(file, encoding='utf-8', on_bad_lines='skip')
                    df.columns = df.columns.str.strip().str.title()
                    df['Duration (Minutes)'] = float(class_duration)
                    df['Attendance Type'] = 'In-Person (Automated Form)'
                else:
                    if file.name.endswith('.xlsx'):
                        df = pd.read_excel(file)
                    else:
                        try:
                            raw_bytes = file.read()
                            file_text = raw_bytes.decode('utf-8')
                        except UnicodeDecodeError:
                            file_text = raw_bytes.decode('utf-16')
                        
                        lines = file_text.splitlines()
                        start_row = 0
                        for idx, line in enumerate(lines):
                            if "In-Meeting Activities" in line or "3. In-Meeting Activities" in line:
                                start_row = idx + 1
                                break
                        clean_csv_text = "\n".join(lines[start_row:])
                        sep_char = '\t' if start_row < len(lines) and '\t' in lines[start_row] else ','
                        df = pd.read_csv(io.StringIO(clean_csv_text), sep=sep_char, on_bad_lines='skip')
                    
                    df.columns = df.columns.str.strip().str.title()
                    df['Attendance Type'] = 'Digital (Teams)'
                
                rename_dict = {
                    'Full Name': 'Name', 'Display Name': 'Name', 'User Name': 'Name',
                    'User Email': 'Email', 'Email Address': 'Email',
                    'Join Time': 'Join Time', 'Leave Time': 'Leave Time'
                }
                df.rename(columns=rename_dict, inplace=True)
                all_dataframes.append(df)
                st.success(f"**Loaded Successfully:** {file.name}")
            except Exception as e:
                st.error(f"❌ **Error parsing {file.name}:** {e}")

# --- TAB 2: THE AUTOMATICALLY GENERATED 2-QUESTION FORM ---
with tab2:
    st.subheader("📝 Automated Student Check-In Form")
    st.markdown("Students sitting in the offline classroom fill out these **2 fields** to log their attendance instantly.")
    
    with st.form("automated_2_question_form", clear_on_submit=True):
        student_name = st.text_input("1. What is your Full Name?")
        student_email = st.text_input("2. What is your Email Address?")
        submit_form = st.form_submit_with_button_state("Submit Response")
        
        if submit_form:
            if student_name.strip() != "":
                new_submission = {
                    "Name": student_name.strip(),
                    "Email": student_email.strip().lower(),
                    "Join Time": "In-Person Check-In",
                    "Leave Time": "In-Person Check-In",
                    "Duration": f"{class_duration}m"
                }
                st.session_state['automated_form_database'].append(new_submission)
                st.success(f"🎉 Thank you, {student_name}! Your response has been recorded automatically.")
            else:
                st.error("⚠️ Please fill in your name before submitting.")

    if st.session_state['automated_form_database']:
        st.markdown("---")
        st.markdown("### 📥 Instructor Control Panel")
        form_df = pd.DataFrame(st.session_state['automated_form_database'])
        
        # Download button to instantly extract the generated data matrix
        form_csv = form_df.to_csv(index=False).encode('utf-8')
        c_dl, c_clr = st.columns(2)
        with c_dl:
            st.download_button(
                label="📥 Download Generated Offline Roster (.csv)",
                data=form_csv,
                file_name="offline_form_responses.csv",
                mime="text/csv",
                use_container_width=True
            )
        with c_clr:
            if st.button("🗑️ Reset Form Database", use_container_width=True):
                st.session_state['automated_form_database'] = []
                st.rerun()

# --- DOWNSTREAM CENTRAL PROCESSING PIPELINES ---
if uploaded_files and all_dataframes:
    master_df = pd.concat(all_dataframes, ignore_index=True)
    if 'Name' not in master_df.columns: master_df['Name'] = "Unknown Student"
    master_df['Name'] = master_df['Name'].apply(professional_name_cleaner)
    master_df = master_df[master_df['Name'].str.strip() != ""]
    if 'Email' in master_df.columns: master_df['Email'] = master_df['Email'].astype(str).str.strip().str.lower()
        
    id_col = st.sidebar.selectbox("Deduplication Key:", options=master_df.columns.tolist(), index=0)
    initial_count = len(master_df)
    master_df.dropna(subset=[id_col], inplace=True)
    
    if 'Duration (Minutes)' not in master_df.columns: master_df['Duration (Minutes)'] = 0.0
    if 'Duration' in master_df.columns:
        def clean_duration_to_mins(val):
            if pd.isna(val): return 0
            val_str = str(val).lower().strip()
            mins = 0
            try:
                h = re.search(r'(\d+)\s*h', val_str)
                m = re.search(r'(\d+)\s*m', val_str)
                s = re.search(r'(\d+)\s*s', val_str)
                if h: mins += int(h.group(1)) * 60
                if m: mins += int(m.group(1))
                if s: mins += int(s.group(1)) / 60.0
                return mins
            except: return 0
        master_df['Duration (Minutes)'] = master_df['Duration (Minutes)'].fillna(0) + master_df['Duration'].apply(clean_duration_to_mins).fillna(0)

    agg_rules = {col: 'first' for col in master_df.columns if col != id_col}
    if 'Duration (Minutes)' in agg_rules: agg_rules['Duration (Minutes)'] = 'sum'
    master_df = master_df.groupby(id_col, as_index=False).agg(agg_rules)

    master_df['Attendance %'] = ((master_df['Duration (Minutes)'] / class_duration) * 100).clip(upper=100.0).round(1)
    master_df['Participation Status'] = master_df['Attendance %'].apply(lambda x: "🟢 Present" if x >= min_benchmark_pct else "🟡 Partial / Late Leave")
    
    with tab3:
        st.subheader("📈 Quick Roster Insights")
        st.bar_chart(master_df['Attendance Type'].value_counts(), color="#4A00E0")
    with tab4:
        st.subheader("📋 Master Data Roster")
        st.dataframe(master_df, use_container_width=True)
        st.download_button(label="📥 Download Combined Master Roster (CSV File)", data=master_df.to_csv(index=False).encode('utf-8'), file_name="final_hybrid_attendance.csv", mime="text/csv", use_container_width=True)
