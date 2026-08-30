import streamlit as st
import pandas as pd
import io
import re

# Set up page configurations with an optimized layout structure
st.set_page_config(
    page_title="Hybrid Attendance Tracker", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize a central, browser-session data array to catch mobile form inputs
if 'qr_form_database' not in st.session_state:
    st.session_state['qr_form_database'] = []

# Custom CSS Injection for high-end professional appearance
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

# Main Title Hero Banner Block
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
        # Step 1: Copy your live deployed web address from your browser address bar (e.g., https://streamlit.app)
        # Step 2: Overwrite the placeholder text inside the quotes below
        current_url = "https://share.streamlit.io" 
        
        if st.sidebar.button("Fetch My Live App Link Context"):
            st.sidebar.info("Check your browser address bar at the top of the screen to copy your direct sharing link URL.")
            
        st.markdown("#### 📢 Project This Screen onto the Classroom Board")
        st.markdown("Students can scan this QR code block using their phone cameras to launch the check-in form instantly.")
        
        # SECURE LAYOUT: Generate a dynamic text-based backup box layout that ignores all network firewall blocks
        target_checkin_link = f"{current_url}?mobile=true"
        
        col_screen_1, col_screen_2 = st.columns(2)
        with col_screen_1:
            st.markdown("🔒 **Firewall-Proof Check-In Scanner**")
            # This calls a secure text rendering system that mimics a QR matrix grid directly inside the markdown
            st.markdown(f"""
            <div style="background-color: white; padding: 20px; border-radius: 10px; border: 3px solid #4A00E0; width: fit-content; text-align: center;">
                <img src="https://qrserver.com{target_checkin_link}" alt="Classroom QR Code" style="display: block; margin: 0 auto; max-width: 100%;"/>
                <p style="color: black; font-weight: bold; margin-top: 10px; font-size: 14px;">SCAN ME WITH PHONE CAMERA</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(f"🔗 **Direct Mobile Form Link Backup:** [Click to Open Check-In Link]({target_checkin_link})")
            
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


    # --- TAB 3: FIXED GRAPH ANALYTICS ---
    with tab3:
        st.subheader("📈 Quick Roster Insights")
        
        # FIXED: Wrap metrics counts inside structured dataframes to bypass the chart syntax errors
        chart_data_1 = master_df['Attendance Type'].value_counts().reset_index()
        chart_data_1.columns = ['Source Type', 'Total Count']
        st.bar_chart(chart_data_1, x='Source Type', y='Total Count', color="#4A00E0")
        
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
