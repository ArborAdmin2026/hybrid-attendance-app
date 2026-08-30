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
            Consolidate Teams digital exports and your Google Form responses into an elegant master list.
        </p>
    </div>
""", unsafe_allow_html=True)

# Professional Name Cleaning Engine Function
def professional_name_cleaner(name_val):
    if pd.isna(name_val):
        return "Unknown Student"
    text = str(name_val).strip()
    text = re.sub(r'\s*[\(\\[][^\\]\)]*unverified[^\\]\)]*[\)\\]]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*[\(\\[][^\\]\)]*guest[^\\]\)]*[\)\\]]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*[\(\\[][^\\]\)]*external[^\\]\)]*[\)\\]]', '', text, flags=re.IGNORECASE)
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
    "🎟️ Google Form QR Kiosk",
    "📊 Analytics Dashboard", 
    "📋 Master Data Roster"
])

# --- TAB 1: UPLOAD AND CONSOLIDATION HUBS ---
with tab1:
    st.subheader("Drag & Drop Attendance Documents")
    st.markdown("Drop **both** your Microsoft Teams report logs and your Google Form response sheet (.csv/.xlsx) here together.")
    uploaded_files = st.file_uploader("Upload files:", type=["xlsx", "csv"], accept_multiple_files=True, label_visibility="collapsed")

    all_dataframes = []
    
    if uploaded_files:
        for file in uploaded_files:
            try:
                fname_lower = file.name.lower()
                
                # Check if it's the offline Google Form response file
                if "offline" in fname_lower or "form" in fname_lower or "response" in fname_lower:
                    if file.name.endswith('.xlsx'):
                        df = pd.read_excel(file)
                    else:
                        df = pd.read_csv(file, encoding='utf-8', on_bad_lines='skip')
                    
                    df.columns = df.columns.str.strip().str.title()
                    # Apply baseline full attendance metrics to offline students
                    df['Duration (Minutes)'] = float(class_duration)
                    df['Attendance Type'] = 'In-Person (Google Form)'
                else:
                    # Execute Microsoft Teams structural parser engine
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
                
                # Global smart alignment dictionary maps
                rename_dict = {
                    'Full Name': 'Name', 'Display Name': 'Name', 'User Name': 'Name',
                    'User Email': 'Email', 'Email Address': 'Email',
                    'Join Time': 'Join Time', 'Leave Time': 'Leave Time', 
                    'Phone': 'Phone Number', 'Phone Number': 'Phone Number'
                }
                df.rename(columns=rename_dict, inplace=True)
                all_dataframes.append(df)
                st.success(f"**Loaded Successfully:** {file.name}")
            except Exception as e:
                st.error(f"❌ **Error parsing {file.name}:** {e}")

# --- TAB 2: STATIC GOOGLE FORM QR INTERFACE DISPATCH ---
with tab2:
    st.subheader("🎟️ Google Form In-Class Room Kiosk")
    st.markdown("Project this tab onto your classroom screen. Students scan the QR code to load your form instantly.")
    
    # ⚠️ CRITICAL EDIT: Paste your actual, full live Google Form sharing link inside the quotes below:
    google_form_url = "https://forms.gle/v1ps237MJPncdQty8"
    
    st.markdown("#### 📢 Classroom Display Scanner")
    
    col_screen_1, col_screen_2 = st.columns(2)
    with col_screen_1:
        try:
            # NATIVE LOADING: Reads your custom uploaded image file right from your GitHub folder
            st.image("classroom_qr.png", caption="Scan with Phone Camera to open Google Form", width=280)
        except Exception as e:
            st.error("⚠️ Local QR code file 'classroom_qr.png' not found in GitHub repository directory.")
            st.markdown(f"🔗 **Backup Form Hyperlink:** [Open Google Form Manually]({google_form_url})")

    with col_screen_2:
        st.markdown("##### 📝 Instructions for the Instructor:")
        st.markdown("""
        1. Overwrite the placeholder url in the code with your actual Google Form link.
        2. Ensure your Google Form contains exactly **Name**, **Email**, and **Phone Number** fields.
        3. Project this tab onto the classroom wall so physical students can check in.
        4. Download your responses from the Google Forms panel as a CSV/Excel file, make sure the file name contains the word **'form'** or **'offline'**, and drop it into **Tab 1**!
        """)
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
        chart_df = master_df.groupby('Attendance Type').size().reset_index(name='Total Count')
        st.bar_chart(chart_df, x='Attendance Type', y='Total Count', color="#4A00E0")
        
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
