import streamlit as st
import pandas as pd
import io

# Set up page configurations with a modern layout
st.set_page_config(
    page_title="Hybrid Attendance Tracker", 
    page_icon="📊", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS Injection to make the app look beautiful and professional
st.markdown("""
    <style>
    /* Gradient banner for the application header */
    .header-banner {
        background: linear-gradient(135deg, #4A00E0 0%, #8E2DE2 100%);
        padding: 30px;
        border-radius: 12px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    /* Style cards for KPI metrics block */
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
    /* Add padding to sidebar items */
    .css-1d391kg {
        padding-top: 3rem;
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

# User Help Documentation Expander Box
with st.expander("ℹ️ How to use this application"):
    st.markdown("""
    1. **Configure Parameters:** Use the left sidebar to enter class duration and required attendance threshold.
    2. **Upload Sheets:** Drop your Teams `.csv`/`.xlsx` files or manual physical lists in the upload box.
    3. **Analyze & Filter:** Use **Tab 2** to view visual counts, or **Tab 3** to isolate specific student profiles.
    4. **Download:** Click the action button at the bottom to download a clean, polished Excel summary report.
    """)

# Sidebar Area Configuration Panels
st.sidebar.header("⚙️ App Configurations")

# Classroom Participation Benchmark Setup
st.sidebar.subheader("⏱️ Session Parameters")
class_duration = st.sidebar.number_input(
    "Total Class Duration (mins):", 
    min_value=1, 
    value=60, 
    step=5,
    help="The nominal duration of your scheduled class lecture."
)
min_benchmark_pct = st.sidebar.slider(
    "Minimum Attendance Threshold (%):", 
    min_value=0, 
    max_value=100, 
    value=75, 
    step=5,
    help="Students below this active time percentage mark will be flagged as Partial Attendance."
)

# Step-by-Step Tab Layout Engine Setup
tab1, tab2, tab3 = st.tabs(["📁 Upload & Process", "📊 Analytics Dashboard", "📋 Master Data Roster"])

with tab1:
    st.subheader("Drag & Drop Attendance Documents")
    uploaded_files = st.file_uploader(
        "Upload raw Microsoft Teams attendance rosters or manual entry sheets here:", 
        type=["xlsx", "csv"], 
        accept_multiple_files=True,
        label_visibility="collapsed"
    )

    all_dataframes = []
    
    if uploaded_files:
        st.markdown("### 📋 File Upload Status Tracking")
        for file in uploaded_files:
            try:
                # Read file based on extension with automatic encoding fallbacks
                if file.name.endswith('.xlsx'):
                    df = pd.read_excel(file)
                else:
                    try:
                        df = pd.read_csv(file, encoding='utf-8')
                    except UnicodeDecodeError:
                        file.seek(0)
                        df = pd.read_csv(file, encoding='utf-16')
                
                # Standardize column names (Title Case, trim spaces)
                df.columns = df.columns.str.strip().str.title()
                
                # Smart automatic column mapping structure for Teams defaults
                rename_dict = {
                    'Full Name': 'Name', 'Display Name': 'Name', 'User Name': 'Name',
                    'User Email': 'Email', 'Email Address': 'Email',
                    'Join Time': 'Join Time', 'Leave Time': 'Leave Time'
                }
                df.rename(columns=rename_dict, inplace=True)
                
                # Determine class source profile by checking string name pattern
                fname_lower = file.name.lower()
                if any(x in fname_lower for x in ["team", "meeting", "online", "chat"]):
                    df['Attendance Type'] = 'Digital (Teams)'
                else:
                    df['Attendance Type'] = 'In-Person (Manual)'
                    
                all_dataframes.append(df)
                st.toast(f"Loaded: {file.name}", icon="✅")
                st.success(f"**Loaded Successfully:** {file.name} ({len(df)} rows found)")
            except Exception as e:
                st.error(f"❌ **Error parsing {file.name}:** {e}")
    else:
        st.info("💡 Please upload one or more CSV or Excel attendance logs to populate the dynamic dashboard view panels.")

# Execute downstream calculations only if files exist in session memory
if uploaded_files and all_dataframes:
    master_df = pd.concat(all_dataframes, ignore_index=True)
    
    # Ensure baseline critical key fields exist structurally
    if 'Name' not in master_df.columns:
        master_df['Name'] = "Unknown Student"
        
    available_columns = master_df.columns.tolist()
    
    # Dynamically select deduplication ID column in sidebar context safely
    id_col = st.sidebar.selectbox(
        "Deduplication Target Key:",
        options=available_columns,
        index=available_columns.index("Email") if "Email" in available_columns else (available_columns.index("Name") if "Name" in available_columns else 0),
        help="The database column used to isolate unique students (Email address is highly recommended)."
    )
    
    # --- CORE AUTOMATED PIPELINE PROCESSOR ---
    initial_count = len(master_df)
    master_df.dropna(subset=[id_col], inplace=True)
    
    # Convert duration blocks to standard float point minutes metrics
    if 'Duration' in master_df.columns:
        def clean_duration_to_mins(val):
            if pd.isna(val): return 0
            val_str = str(val).lower().strip()
            if 'h' in val_str or 'm' in val_str:
                mins = 0
                try:
                    import re
                    hours_match = re.search(r'(\d+)\s*h', val_str)
                    mins_match = re.search(r'(\d+)\s*m', val_str)
                    if hours_match: mins += int(hours_match.group(1)) * 60
                    if mins_match: mins += int(mins_match.group(1))
                    return mins
                except: return 0
            try: return float(val)
            except: return 0
        master_df['Duration (Minutes)'] = master_df['Duration'].apply(clean_duration_to_mins)
    elif 'Join Time' in master_df.columns and 'Leave Time' in master_df.columns:
        try:
            master_df['Join Time'] = pd.to_datetime(master_df['Join Time'], errors='coerce')
            master_df['Leave Time'] = pd.to_datetime(master_df['Leave Time'], errors='coerce')
            master_df['Duration (Minutes)'] = (master_df['Leave Time'] - master_df['Join Time']).dt.total_seconds() / 60.0
            master_df['Duration (Minutes)'] = master_df['Duration (Minutes)'].fillna(0).clip(lower=0)
        except:
            master_df['Duration (Minutes)'] = float(class_duration)
    else:
        master_df['Duration (Minutes)'] = float(class_duration)

    # Compile data across unique identifier indices
    agg_rules = {}
    for col in master_df.columns:
        if col == id_col: continue
        if col == 'Duration (Minutes)': agg_rules[col] = 'sum'
        elif col in ['Join Time', 'Leave Time', 'Attendance Type', 'Name', 'Email']: agg_rules[col] = 'first'
    
    if agg_rules:
        master_df = master_df.groupby(id_col, as_index=False).agg(agg_rules)
    else:
        master_df.drop_duplicates(subset=[id_col], keep='first', inplace=True)

    # Compute final percentage performance profiles
    master_df['Attendance %'] = (master_df['Duration (Minutes)'] / class_duration) * 100
    master_df['Attendance %'] = master_df['Attendance %'].clip(upper=100.0).round(1)
    master_df['Participation Status'] = master_df['Attendance %'].apply(
        lambda x: "🟢 Present" if x >= min_benchmark_pct else "🟡 Partial / Late Leave"
    )
    
    final_count = len(master_df)
    removed_count = initial_count - final_count

    # Populate Tab 2: Visual Insights & Summary Indicators
    with tab2:
        st.subheader("📈 Quick Roster Insights")
        
        # Draw metric visual component badges inside clean container borders
        with st.container():
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Total Logs Extracted", initial_count)
            kpi2.metric("Redundant Items Cleaned", removed_count)
            kpi3.metric("Passed Attendance Benchmark", len(master_df[master_df['Participation Status'] == "🟢 Present"]))
            kpi4.metric("Flagged Attendance (Under Threshold)", len(master_df[master_df['Participation Status'] == "🟡 Partial / Late Leave"]))
        
        st.markdown("---")
        
        # Split analytics visually using column graphs layout structure
        g_col1, g_col2 = st.columns(2)
        with g_col1:
            st.markdown("##### Attendance Location Source Breakdown")
            source_counts = master_df['Attendance Type'].value_counts()
            st.bar_chart(source_counts, color="#4A00E0")
        with g_col2:
            st.markdown("##### Classroom Participation Status Ratios")
            status_counts = master_df['Participation Status'].value_counts()
            st.bar_chart(status_counts, color="#8E2DE2")
