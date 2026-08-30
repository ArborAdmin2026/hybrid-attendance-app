import streamlit as st
import pandas as pd
import io
import re

# 1. Set up page configurations with a modern layout
st.set_page_config(
    page_title="Hybrid Attendance Tracker", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize a central browser session memory bank to catch mobile form inputs
if 'qr_form_database' not in st.session_state:
    st.session_state['qr_form_database'] = []

# Custom CSS Injection for clean professional appearance
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

# Main Title Header Hero Banner Block
st.markdown("""
    <div class="header-banner">
        <h1 style='margin:0; font-size: 32px;'>📊 Hybrid Attendance Data Studio</h1>
        <p style='margin:5px 0 0 0; opacity: 0.9; font-size: 16px;'>
            Consolidate Teams digital exports and automated mobile check-ins into an elegant master list.
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

# Sidebar Control Options Deck
st.sidebar.header("⚙️ App Configurations")
class_duration = st.sidebar.number_input("Total Class Duration (mins):", min_value=1, value=60, step=5)
min_benchmark_pct = st.sidebar.slider("Minimum Attendance Threshold (%):", min_value=0, max_value=100, value=75, step=5)

# Step-by-Step Tab Layout Management
tab1, tab2, tab3, tab4 = st.tabs([
    "📁 Upload & Process", 
    "🎟️ QR Code Form Kiosk",
    "📊 Analytics Dashboard", 
    "📋 Master Data Roster"
])

# --- TAB 1: UPLOAD AND CONSOLIDATION PIPELINE ---
with tab1:
    st.subheader("Drag & Drop Attendance Documents")
    st.markdown("Drop **both** your Microsoft Teams report logs and your downloaded mobile response files here together.")
    uploaded_files = st.file_uploader("Upload files:", type=["xlsx", "csv"], accept_multiple_files=True, label_visibility="collapsed")

    all_dataframes = []
    
    if uploaded_files:
        for file in uploaded_files:
            try:
                fname_lower = file.name.lower()
                if "offline" in fname_lower or "form" in fname_lower or "qr" in fname_lower:
                    df = pd.read_csv(file, encoding='utf-8', on_bad_lines='skip')
                    df.columns = df.columns.str.strip().str.title()
                    df['Duration (Minutes)'] = float(class_duration)
                    df['Attendance Type'] = 'In-Person (Mobile QR Form)'
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
                    'Join Time': 'Join Time', 'Leave Time': 'Leave Time', 'Phone': 'Phone Number'
                }
                df.rename(columns=rename_dict, inplace=True)
                all_dataframes.append(df)
                st.success(f"**Loaded Successfully:** {file.name}")
            except Exception as e:
                st.error(f"❌ **Error parsing {file.name}:** {e}")

# --- TAB 2: LIVE IN-CLASSROOM QR SCREEN & EMBEDDED FORM LINK ---
with tab2:
    st.subheader("🎟️ Live Mobile Check-In Workspace")
    
    try:
        query_params = st.query_params
        is_mobile_view = "mobile" in query_params
    except Exception:
        is_mobile_view = False

    if is_mobile_view:
        st.markdown("### 📱 Mobile Check-In Form")
        st.info("Fill out these 3 details to log your attendance for today's session.")
        
        with st.form("mobile_input_form", clear_on_submit=True):
            m_name = st.text_input("1. Full Name:")
            m_email = st.text_input("2. Email Address:")
            m_phone = st.text_input("3. Phone Number:")
            submit_m = st.form_submit_with_button_state("Submit Attendance")
            
            if submit_m:
                if m_name.strip() != "":
                    new_log = {
                        "Name": m_name.strip(),
                        "Email": m_email.strip().lower(),
                        "Phone Number": m_phone.strip(),
                        "Join Time": "Mobile Check-In",
                        "Leave Time": "Mobile Check-In",
                        "Duration": f"{class_duration}m"
                    }
                    st.session_state['qr_form_database'].append(new_log)
                    st.success("🎉 Check-in successful! You may now close this browser tab.")
                else:
                    st.error("⚠️ Full Name is a required field.")
    else:
        current_url = "https://share.streamlit.io" 
        if st.sidebar.button("Fetch My Live App Link Context"):
            st.sidebar.info("Make sure to check your browser address bar for your direct sharing link URL prefix.")
            
        st.markdown("#### 📢 Project This Screen onto the Classroom Board")
        st.markdown("Students can scan this QR code using their phone cameras to launch the mobile form instantly.")
        
        col_screen_1, col_screen_2 = st.columns(2)
        with col_screen_1:
            st.markdown("### 🔗 Scan or Click the Form")
            st.link_button("📱 Open Mobile Check-In Form Link", f"{current_url}?mobile=true", use_container_width=True)
            
            qr_target_url = f"https://quickchart.io/qr?text={current_url}?mobile=true&size=300"
            st.image(qr_target_url, caption="Classroom Projector View", width=280)
        with col_screen_2:
            st.markdown("##### ⚙️ Instructor Attendance Roster Controls")
            st.markdown(f"**Total Mobile Check-Ins Collected Today:** `{len(st.session_state['qr_form_database'])}` records")
            
            if st.session_state['qr_form_database']:
                form_df = pd.DataFrame(st.session_state['qr_form_database'])
                st.dataframe(form_df, use_container_width=True)
                
                csv_buffer = form_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Download Generated Offline Roster (offline_responses.csv)",
                    data=csv_buffer,
                    file_name="offline_responses.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
                if st.button("🗑️ Reset Session Database", use_container_width=True):
                    st.session_state['qr_form_database'] = []
                    st.rerun()
            else:
                st.warning("📌 Waiting for incoming student check-ins. Roster table and export options will lock into view here as soon as the first student scans and submits.")

# --- DOWNSTREAM CENTRAL DATA RECONSTRUCTION PIPELINE ---
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
    
    # --- TAB 3: INSIGHTS & GRAPH VISUALISERS ---
    with tab3:
        st.subheader("📈 Quick Roster Insights")
        try:
            chart_df = master_df.groupby('Attendance Type').size().reset_index(name='Total Count')
            st.bar_chart(chart_df, x='Attendance Type', y='Total Count', color="#4A00E0")
        except Exception as e:
            st.dataframe(master_df['Attendance Type'].value_counts())
        
    # --- TAB 4: UNIFIED GRID CONSOLE AND FINAL CONSOLIDATION DOWNLOAD ---
    with tab4:
        st.subheader("📋 Unified Master Hybrid Roster")
        st.dataframe(master_df, use_container_width=True)
        st.download_button(
            label="📥 Download Combined Master Roster (CSV File)", 
            data=master_df.to_csv(index=False).encode('utf-8'), 
            file_name="final_hybrid_attendance_report.csv", 
            mime="text/csv", 
            use_container_width=True
        )
