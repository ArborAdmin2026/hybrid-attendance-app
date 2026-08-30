import streamlit as st
import pandas as pd
import io
import re
import qrcode

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
            Consolidate Teams digital exports and manual in-person logs into an elegant, deduplicated master list.
        </p>
    </div>
""", unsafe_allow_html=True)

# Professional Name Cleaning Engine Function
def professional_name_cleaner(name_val):
    if pd.isna(name_val):
        return "Unknown Student"
    
    # Convert to string and strip surrounding whitespace
    text = str(name_val).strip()
    
    # 1. Strip out unverified tags, guest tags, or external identifiers inside brackets
    text = re.sub(r'\s*[\(\[][^\]\)]*unverified[^\]\)]*[\)\]]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*[\(\[][^\]\)]*guest[^\]\)]*[\)\]]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*[\(\[][^\]\)]*external[^\]\)]*[\)\]]', '', text, flags=re.IGNORECASE)
    
    # 2. Strip numbers and trailing punctuation strings
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    
    # 3. Collapse double/triple blank spaces down into a single space, then Title Case it
    text = " ".join(text.split())
    return text.title()

# Sidebar Area Configuration Panels
st.sidebar.header("⚙️ App Configurations")
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

# Step-by-Step Tab Layout Engine Setup - "🎟️ Offline Check-in (QR)" moved to 2nd position
tab1, tab2, tab3, tab4 = st.tabs([
    "📁 Upload & Process", 
    "🎟️ Offline Check-in (QR)",
    "📊 Analytics Dashboard", 
    "📋 Master Data Roster"
])

with tab1:
    st.subheader("Drag & Drop Attendance Documents")
    st.markdown("Drop **both** your Microsoft Teams report logs and your Offline Check-In files here simultaneously.")
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
                fname_lower = file.name.lower()
                
                # Check if it's an offline roster file
                if "offline" in fname_lower or "manual" in fname_lower or "qr" in fname_lower:
                    if file.name.endswith('.xlsx'):
                        df = pd.read_excel(file)
                    else:
                        df = pd.read_csv(file, encoding='utf-8', on_bad_lines='skip')
                    
                    df.columns = df.columns.str.strip().str.title()
                    # Pad duration for offline students since they are physically present
                    df['Duration (Minutes)'] = float(class_duration)
                    df['Attendance Type'] = 'In-Person (Offline QR)'
                    
                else:
                    # Parse standard Teams files from Section 3
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
                
                # Global structural formatting maps
                rename_dict = {
                    'Full Name': 'Name', 'Display Name': 'Name', 'User Name': 'Name',
                    'User Email': 'Email', 'Email Address': 'Email',
                    'Join Time': 'Join Time', 'Leave Time': 'Leave Time'
                }
                df.rename(columns=rename_dict, inplace=True)
                all_dataframes.append(df)
                st.success(f"**Loaded Successfully:** {file.name} ({len(df)} rows detected)")
            except Exception as e:
                st.error(f"❌ **Error parsing {file.name}:** {e}")
    else:
        st.info("💡 Please upload your CSV/Excel files to populate the layout dashboards.")

# Initialize an empty master dataframe to avoid processing failures if no files are uploaded yet
master_df = pd.DataFrame()

if uploaded_files and all_dataframes:
    master_df = pd.concat(all_dataframes, ignore_index=True)
    
    if 'Name' not in master_df.columns:
        master_df['Name'] = "Unknown Student"
    
    master_df['Name'] = master_df['Name'].apply(professional_name_cleaner)
    master_df = master_df[master_df['Name'].str.strip() != ""]
    
    if 'Email' in master_df.columns:
        master_df['Email'] = master_df['Email'].astype(str).str.strip().str.lower()
        
    available_columns = master_df.columns.tolist()
    id_col = st.sidebar.selectbox(
        "Deduplication Target Key:",
        options=available_columns,
        index=available_columns.index("Name") if "Name" in available_columns else 0
    )
    
    initial_count = len(master_df)
    master_df.dropna(subset=[id_col], inplace=True)
    
    # Calculate durations for items without manual preset values
    if 'Duration (Minutes)' not in master_df.columns:
        master_df['Duration (Minutes)'] = 0.0

    if 'Duration' in master_df.columns:
        def clean_duration_to_mins(val):
            if pd.isna(val): return 0
            val_str = str(val).lower().strip()
            if 'h' in val_str or 'm' in val_str or 's' in val_str:
                mins = 0
                try:
                    hours_match = re.search(r'(\d+)\s*h', val_str)
                    mins_match = re.search(r'(\d+)\s*m', val_str)
                    secs_match = re.search(r'(\d+)\s*s', val_str)
                    if hours_match: mins += int(hours_match.group(1)) * 60
                    if mins_match: mins += int(mins_match.group(1))
                    if secs_match: mins += int(secs_match.group(1)) / 60.0
                    return mins
                except: return 0
            try: return float(val)
            except: return 0
        
        # Combine calculated logs safely
        teams_mins = master_df['Duration'].apply(clean_duration_to_mins)
        master_df['Duration (Minutes)'] = master_df['Duration (Minutes)'].fillna(0) + teams_mins.fillna(0)

    agg_rules = {}
    for col in master_df.columns:
        if col == id_col: continue
        if col == 'Duration (Minutes)': agg_rules[col] = 'sum'
        elif col in ['Join Time', 'Leave Time', 'Attendance Type', 'Name', 'Email', 'Role']: agg_rules[col] = 'first'
    
    if agg_rules:
        master_df = master_df.groupby(id_col, as_index=False).agg(agg_rules)
    else:
        master_df.drop_duplicates(subset=[id_col], keep='first', inplace=True)

    master_df['Attendance %'] = (master_df['Duration (Minutes)'] / class_duration) * 100
    master_df['Attendance %'] = master_df['Attendance %'].clip(upper=100.0).round(1)
    master_df['Participation Status'] = master_df['Attendance %'].apply(
        lambda x: "🟢 Present" if x >= min_benchmark_pct else "🟡 Partial / Late Leave"
    )
    
    final_count = len(master_df)
    removed_count = initial_count - final_count

# Populate Tab 2: QR Code Check-In Generator
with tab2:
    st.subheader("🎟️ Physical Classroom QR Code Check-In Engine")
    st.markdown("""
    Provide this QR code to your offline classroom attendees. When scanned, it opens your custom check-in form.
    Save the responses as an Excel/CSV file with the word **'offline'** in the filename so the application can merge it correctly.
    """)
    
    # Input field to link your Google Forms or Microsoft Forms check-in sheet link URL
    form_url = st.text_input(
        "Paste your Microsoft/Google Check-In Form URL Link here:",
        value="https://forms.office.com"
    )
    
    if form_url:
        # Generate the QR Code Matrix
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(form_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save to buffer bytes to show in Streamlit framework
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        byte_im = buf.getvalue()
        
        col_q1, col_q2 = st.columns(2)
        with col_q1:
            st.image(byte_im, caption="Scan to Check-In Offline", width=250)
        with col_q2:
            st.markdown("#### 📢 Steps for the Instructor:")
            st.markdown("""
            1. Create a 2-question form (asking for **Name** and **Email**).
            2. Paste that form link above to generate the custom room QR code.
            3. Project this screen or print the code for physical students to scan.
            4. At the end of class, export the responses, name the file `offline_roster.csv`, and drop it into **Tab 1**!
            """)

# Populate Tab 3: Visual Insights & Summary Indicators
with tab3:
    st.subheader("📈 Quick Roster Insights")
    if not master_df.empty:
        with st.container():
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Total Logs Extracted", initial_count)
            kpi2.metric("Redundant Items Cleaned", removed_count)
            kpi3.metric("Passed Benchmark", len(master_df[master_df['Participation Status'] == "🟢 Present"]))
            kpi4.metric("Flagged Attendance", len(master_df[master_df['Participation Status'] == "🟡 Partial / Late Leave"]))
        
        st.markdown("---")
        g_col1, g_col2 = st.columns(2)
        with g_col1:
            st.markdown("##### Attendance Location Source Breakdown")
            st.bar_chart(master_df['Attendance Type'].value_counts(), color="#4A00E0")
        with g_col2:
            st.markdown("##### Classroom Participation Status Ratios")
            st.bar_chart(master_df['Participation Status'].value_counts(), color="#8E2DE2")
    else:
        st.info("💡 Please upload files in the 'Upload & Process' tab to check analytics summary panels.")

# Populate Tab 4: Sorting, Deep Search Data Queries, and Export Core Engines
with tab4:
    st.subheader("🔍 Interactive Roster Grid Control Deck")
    if not master_df.empty:
        c1, c2, c3 = st.columns(3)
        with c1:
            selected_type = st.selectbox("Isolate Class Medium Source:", options=["All Sources"] + list(master_df['Attendance Type'].unique()))
        with c2:
            selected_status = st.selectbox("Isolate Engagement Status:", options=["All Statuses", "🟢 Present", "🟡 Partial / Late Leave"])
        with c3:
            sort_options = {
                "Alphabetical (Name A-Z)": ('Name', True),
                "Alphabetical (Name Z-A)": ('Name', False),
                "Highest Attendance %": ('Attendance %', False),
                "Lowest Attendance %": ('Attendance %', True)
            }
            selected_sort = st.selectbox("Re-Sort Roster Layout Target:", options=list(sort_options.keys()))

        filtered_df = master_df.copy()
        if selected_type != "All Sources":
            filtered_df = filtered_df[filtered_df['Attendance Type'] == selected_type]
        if selected_status != "All Statuses":
            filtered_df = filtered_df[filtered_df['Participation Status'] == selected_status]
            
        sort_col, sort_ascending = sort_options[selected_sort]
        filtered_df.sort_values(by=sort_col, ascending=sort_ascending, inplace=True)

        st.dataframe(
            filtered_df, 
            use_container_width=True, 
            column_config={
                "Attendance %": st.column_config.ProgressColumn("Attendance Percent %", format="%.1f%%", min_value=0, max_value=100),
                "Duration (Minutes)": st.column_config.NumberColumn("Active Time (Mins)", format="%.1f min")
            }
        )
        
        try:
            processed_data = filtered_df.to_csv(index=False).encode('utf-8')
            mime_type = "text/csv"
        except Exception as e:
            st.error(f"Error preparing download file: {e}")
            processed_data = b""
        
        st.markdown("<br>", unsafe_allow_html=True)
        if processed_data:
            st.download_button(
                label="📥 Download Cleaned & Sorted Master Roster (CSV File)",
                data=processed_data,
                file_name="cleaned_hybrid_attendance_report.csv",
                mime=mime_type,
                use_container_width=True
            )
    else:
        st.info("💡 Please upload files in the 'Upload & Process' tab to build the master dataset roster grid view control deck.")
