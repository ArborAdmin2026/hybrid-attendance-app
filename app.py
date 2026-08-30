import streamlit as st
import pandas as pd
import io

# Set up page configurations
st.set_page_config(page_title="Hybrid Attendance Tracker", page_icon="📊", layout="wide")

st.title("📊 Hybrid Attendance Data Cleaner & Analytics App")
st.markdown("""
Upload your raw Microsoft Teams attendance exports or manual in-person sheets. 
This web app automatically merges records, strips duplicate logs, calculates custom participation metrics, and filters rows instantly.
""")

# File uploader widget supporting multiple files
uploaded_files = st.file_uploader(
    "Choose Excel (.xlsx) or CSV files", 
    type=["xlsx", "csv"], 
    accept_multiple_files=True
)

if uploaded_files:
    all_dataframes = []
    
    for file in uploaded_files:
        try:
            # Read file based on extension
            if file.name.endswith('.xlsx'):
                df = pd.read_excel(file)
            else:
                df = pd.read_csv(file)
            
            # Standardize column names (Title Case, trim spaces)
            df.columns = df.columns.str.strip().str.title()
            
            # Smart automatic formatting for Microsoft Teams default columns
            rename_dict = {
                'Full Name': 'Name',
                'Display Name': 'Name',
                'User Name': 'Name',
                'User Email': 'Email',
                'Email Address': 'Email',
                'Join Time': 'Join Time',
                'Leave Time': 'Leave Time'
            }
            df.rename(columns=rename_dict, inplace=True)
            
            # Determine source tag based on filename
            fname_lower = file.name.lower()
            if "team" in fname_lower or "meeting" in fname_lower or "online" in fname_lower:
                df['Attendance Type'] = 'Digital (Teams)'
            else:
                df['Attendance Type'] = 'In-Person (Manual)'
                
            all_dataframes.append(df)
            st.success(f"Successfully loaded: {file.name}")
        except Exception as e:
            st.error(f"Error processing {file.name}: {e}")

    if all_dataframes:
        # Merge all uploaded sheets into one master list
        master_df = pd.concat(all_dataframes, ignore_index=True)
        
        # Ensure critical columns exist safely
        if 'Name' not in master_df.columns:
            master_df['Name'] = "Unknown Student"
        
        st.sidebar.header("⚙️ Configuration & Cleaning Options")
        
        # User dynamic selection for deduplication key
        available_columns = master_df.columns.tolist()
        id_col = st.sidebar.selectbox(
            "Select unique identifier column for deduplication:",
            options=available_columns,
            index=available_columns.index("Email") if "Email" in available_columns else (available_columns.index("Name") if "Name" in available_columns else 0)
        )
        
        # Classroom Participation Benchmark Setup
        st.sidebar.subheader("⏱️ Participation Parameters")
        class_duration = st.sidebar.number_input(
            "Total Class Duration (minutes):", 
            min_value=1, 
            value=60, 
            step=5
        )
        min_benchmark_pct = st.sidebar.slider(
            "Minimum Required Attendance Percentage (%):", 
            min_value=0, 
            max_value=100, 
            value=75, 
            step=5
        )
        
        # --- DATA CLEANING PIPELINE ---
        initial_count = len(master_df)
        master_df.dropna(subset=[id_col], inplace=True) # drop records missing the unique identifier
        
        # Try to parse Duration column if it exists or calculate it from Join/Leave times
        if 'Duration' in master_df.columns:
            # Clean up duration field if it's text (e.g. '45m' or '1h 5m')
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
                    except:
                        return 0
                try:
                    return float(val) # If it's already a clean number
                except:
                    return 0
            master_df['Duration (Minutes)'] = master_df['Duration'].apply(clean_duration_to_mins)
        elif 'Join Time' in master_df.columns and 'Leave Time' in master_df.columns:
            try:
                master_df['Join Time'] = pd.to_datetime(master_df['Join Time'], errors='coerce')
                master_df['Leave Time'] = pd.to_datetime(master_df['Leave Time'], errors='coerce')
                master_df['Duration (Minutes)'] = (master_df['Leave Time'] - master_df['Join Time']).dt.total_seconds() / 60.0
                master_df['Duration (Minutes)'] = master_df['Duration (Minutes)'].fillna(0).clip(lower=0)
            except:
                master_df['Duration (Minutes)'] = class_duration # Fallback for structural safety
        else:
            # If no time data exists (like a pure manual checklist file), assume present students get full duration
            master_df['Duration (Minutes)'] = float(class_duration)

        # Deduplicate based on selected ID column
        # Group by the student and aggregate values intelligently
        agg_rules = {}
        for col in master_df.columns:
            if col == id_col:
                continue
            if col == 'Duration (Minutes)':
                agg_rules[col] = 'sum' # Add total minutes across accidental disconnections
            elif col in ['Join Time', 'Leave Time', 'Attendance Type', 'Name', 'Email']:
                agg_rules[col] = 'first' # Pick the first recorded entry details
        
        if agg_rules:
            master_df = master_df.groupby(id_col, as_index=False).agg(agg_rules)
        else:
            master_df.drop_duplicates(subset=[id_col], keep='first', inplace=True)

        # Calculate participation metrics
        master_df['Attendance %'] = (master_df['Duration (Minutes)'] / class_duration) * 100
        master_df['Attendance %'] = master_df['Attendance %'].clip(upper=100.0).round(1)
        
        master_df['Participation Status'] = master_df['Attendance %'].apply(
            lambda x: "🟢 Present" if x >= min_benchmark_pct else "🟡 Partial / Late Leave"
        )
        
        final_count = len(master_df)
        removed_count = initial_count - final_count
        
        # --- SORTING AND FILTERING INTERFACE ---
        st.subheader("🔍 Filtering and Sorting Dashboard")
        
        col_f1, col_f2, col_f3 = st.columns(3)
        
        with col_f1:
            # Filter by Attendance Type (Hybrid Source)
            type_options = ["All Sources"] + list(master_df['Attendance Type'].unique())
            selected_type = st.selectbox("Filter by Attendance Source:", options=type_options)
            
        with col_f2:
            # Filter by Status
            status_options = ["All Statuses", "🟢 Present", "🟡 Partial / Late Leave"]
            selected_status = st.selectbox("Filter by Participation Status:", options=status_options)
            
        with col_f3:
            # Dynamic Sorting Choice
            sort_options = {
                "Alphabetical (Name A-Z)": ('Name', True),
                "Alphabetical (Name Z-A)": ('Name', False),
                "Highest Attendance %": ('Attendance %', False),
                "Lowest Attendance %": ('Attendance %', True)
            }
            selected_sort = st.selectbox("Sort Table Records By:", options=list(sort_options.keys()))

        # Apply Filters to the Dataframe
        filtered_df = master_df.copy()
        if selected_type != "All Sources":
            filtered_df = filtered_df[filtered_df['Attendance Type'] == selected_type]
        if selected_status != "All Statuses":
            filtered_df = filtered_df[filtered_df['Participation Status'] == selected_status]
            
        # Apply Sorting
        sort_col, sort_ascending = sort_options[selected_sort]
        filtered_df.sort_values(by=sort_col, ascending=sort_ascending, inplace=True)

        # Main KPI Metrics Cards
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Records Processed", initial_count)
        kpi2.metric("Duplicates Merged", removed_count)
        kpi3.metric("Fully Present (Benchmark Passed)", len(filtered_df[filtered_df['Participation Status'] == "🟢 Present"]))
        kpi4.metric("Partial Attendance (Below Benchmark)", len(filtered_df[filtered_df['Participation Status'] == "🟡 Partial / Late Leave"]))
        
        # Display Preview Window
        st.subheader("📋 Filtered Master Attendance Roster")
        st.dataframe(filtered_df, use_container_width=True)
        
        # Conversion Block for unified Excel Output
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            filtered_df.to_excel(writer, index=False, sheet_name='Master Roster Summary')
        processed_data = output.getvalue()
        
        st.download_button(
            label="📥 Download Sorted & Cleaned Excel Master Roster",
            data=processed_data,
            file_name="cleaned_hybrid_attendance_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
