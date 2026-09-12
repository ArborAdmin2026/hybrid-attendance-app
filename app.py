import pandas as pd
import streamlit as st
import sqlite3
import re
from io import StringIO
from datetime import datetime

# Database Configuration
DB_NAME = "hybrid_attendance_clean.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Roster table to hold student profile information
    c.execute('''CREATE TABLE IF NOT EXISTS roster 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)''')
    # Offline presence log for a specific date
    c.execute('''CREATE TABLE IF NOT EXISTS offline_logs 
                 (date TEXT, name TEXT, status TEXT)''')
    conn.commit()
    conn.close()

init_db()

def parse_teams_duration(duration_str):
    """Converts standard Teams text frames ('1h 24m 42s', '47m 48s', '3m 22s') into clean integer minutes."""
    if pd.isna(duration_str) or not str(duration_str).strip():
        return 0
    duration_str = str(duration_str).lower().strip()
    
    hours = 0
    minutes = 0
    
    # Trace hour and minute metrics via explicit regex matching groups
    h_match = re.search(r'(\d+)\s*h', duration_str)
    m_match = re.search(r'(\d+)\s*m', duration_str)
    
    if h_match:
        hours = int(h_match.group(1))
    if m_match:
        minutes = int(m_match.group(1))
    elif 'h' not in duration_str and 's' in duration_str:
        # Check if single integer represents minutes or seconds safely
        digit_match = re.search(r'^\s*(\d+)\s*s', duration_str)
        if not digit_match:
            digits = re.findall(r'\d+', duration_str)
            if digits:
                minutes = int(digits[0])
                
    return (hours * 60) + minutes

st.set_page_config(page_title="Hybrid Attendance Hub", layout="wide")
st.title("📊 Hybrid Class Attendance Dashboard")
st.caption("A clean tool built from scratch to clean complex Microsoft Teams file exports and log offline students.")

# Main Application Menu Router
menu = st.tabs(["🚶‍♂️ Offline Student Check-In", "💻 Teams Log Processor & Merger", "🗃️ Master Class Roster"])

# --- TAB 1: OFFLINE CHECK-IN PORTAL ---
with menu[0]:
    st.header("🚶‍♂️ Classroom Attendance Registry")
    st.markdown("Use this panel to mark attendance for students physically sitting in your classroom today.")
    
    selected_date = st.date_input("Target Attendance Date", datetime.now(), key="offline_date_picker").strftime("%Y-%m-%d")
    
    conn = sqlite3.connect(DB_NAME)
    roster_list = pd.read_sql_query("SELECT name FROM roster ORDER BY name ASC", conn)['name'].tolist()
    saved_offline_today = pd.read_sql_query("SELECT name FROM offline_logs WHERE date=?", conn, params=(selected_date,))['name'].tolist()
    conn.close()
    
    if not roster_list:
        st.info("💡 The master student roster directory is completely empty. Please add your students in the 'Master Class Roster' tab first.")
    else:
        st.write("### Check the box for each student present in the room:")
        
        # Build 3 columns for balanced UI visualization
        grid_cols = st.columns(3)
        current_classroom_present = []
        
        for idx, student_name in enumerate(roster_list):
            with grid_cols[idx % 3]:
                is_checked = student_name in saved_offline_today
                if st.checkbox(student_name, value=is_checked, key=f"check_{student_name}_{selected_date}"):
                    current_classroom_present.append(student_name)
                    
        st.markdown("---")
        if st.button("💾 Save Offline Attendance Logs", type="primary", use_container_width=True):
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            # Clear previous entries for this date to support live data updates
            c.execute("DELETE FROM offline_logs WHERE date=?", (selected_date,))
            for name in current_classroom_present:
                c.execute("INSERT INTO offline_logs (date, name, status) VALUES (?, ?, 'Present (Offline)')", (selected_date, name))
            conn.commit()
            conn.close()
            st.success(f"Recorded {len(current_classroom_present)} offline students for session date: {selected_date}!")
            st.rerun()

# --- TAB 2: TEAMS PIPELINE ENGINE ---
with menu[1]:
    st.header("💻 Microsoft Teams CSV Processing Pipeline")
    st.markdown("Drop your multi-section Teams attendance export text or CSV file here to remove duplicate entries, strip noise, and compile classroom data columns.")
    
    target_date = st.date_input("Match Session Date", datetime.now(), key="pipeline_date_picker").strftime("%Y-%m-%d")
    noise_threshold = st.slider("Online Noise Aggregation Filter (Minimum Minutes Required)", 0, 60, 10, help="Any student whose total combined login duration is less than this value will be labeled absent/noise.")
    
    uploaded_file = st.file_uploader("Upload Raw Teams CSV / TXT File", type=["csv", "txt"])
    
    if uploaded_file is not None:
        try:
            # Parse file text string framework
            raw_text_data = uploaded_file.read().decode("utf-8", errors="ignore")
            lines = raw_text_data.splitlines()
            
            # Find bounds for '2. Participants'
            section_start_idx = None
            section_end_idx = None
            
            for index, current_line in enumerate(lines):
                if "2. Participants" in current_line:
                    section_start_idx = index
                elif "3. In-Meeting Activities" in current_line or "3. In-meeting activities" in current_line:
                    section_end_idx = index
                    
            if section_start_idx is None:
                st.error("❌ Invalid Layout Structure: Could not locate section '2. Participants' within the file matrix.")
            else:
                # Segment section text lines safely
                end_bound = section_end_idx if section_end_idx else len(lines)
                participant_lines = lines[section_start_idx + 1 : end_bound]
                clean_csv_string = "\n".join([line for line in participant_lines if line.strip()])
                
                # Load section into dataframe using tab or fallback comma delimiters
                df_teams = pd.read_csv(StringIO(clean_csv_string), sep='\t')
                if df_teams.shape[0] <= 1:
                    df_teams = pd.read_csv(StringIO(clean_csv_string), sep=',')
                    
                # Clean structural headers
                df_teams.columns = [str(col).strip() for col in df_teams.columns]
                
                # Check for Name and Duration fields
                name_col = next((c for c in df_teams.columns if 'name' in c.lower()), None)
                duration_col = next((c for c in df_teams.columns if 'dur' in c.lower()), None)
                
                if not name_col or not duration_col:
                    st.error(f"❌ Matching Fields Failed. Ensure 'Name' and 'In-Meeting Duration' fields exist. Columns found: {list(df_teams.columns)}")
                else:
                    parsed_rows_accumulator = []
                    
                    for _, row in df_teams.iterrows():
                        raw_name_string = str(row[name_col]).strip()
                        
                        # Strip default Teams unverified flags and brackets
                        clean_student_name = re.sub(r'\s*\(unverified\)\s*', '', raw_name_string, flags=re.IGNORECASE).strip()
                        
                        # Filter out internal organization session name labels
                        if "meeting with data analytics" in clean_student_name.lower() or not clean_student_name or clean_student_name == "nan":
                            continue
                            
                        raw_duration_string = str(row[duration_col])
                        total_minutes = parse_teams_duration(raw_duration_string)
                        
                        parsed_rows_accumulator.append({
                            "Student Name": clean_student_name,
                            "Online Duration (Mins)": total_minutes
                        })
                        
                    raw_dataframe = pd.DataFrame(parsed_rows_accumulator)
                    
                    # Group by Name to fix connection dropdown duplicates
                    online_summary = raw_dataframe.groupby("Student Name").agg({
                        "Online Duration (Mins)": "sum"
                    }).reset_index()
                    
                    # Mark online thresholds
                    online_summary["Status"] = online_summary["Online Duration (Mins)"].apply(
                        lambda x: "Present (Online)" if x >= noise_threshold else "Absent (Dropped/Noise)"
                    )
                    
                    # Isolate actual present online students
                    valid_online_only = online_summary[online_summary["Status"] == "Present (Online)"].copy()
                    
                    st.subheader("🟢 Cleaned Online Attendance Records")
                    st.dataframe(valid_online_only, use_container_width=True)
                    
                    # --- CONSOLIDATE MASTER DATA STREAMS ---
                    st.markdown("---")
                    st.subheader("🔀 Merged Master Attendance Report Sheet")
                    
                    # Pull offline logs from local database storage matrix
                    conn = sqlite3.connect(DB_NAME)
                    offline_df = pd.read_sql_query(
                        "SELECT name as 'Student Name', status as 'Status' FROM offline_logs WHERE date=?", 
                        conn, params=(target_date,)
                    )
                    # Pull full structural roster to check for absent profiles
                    master_class_roster = pd.read_sql_query("SELECT name as 'Student Name' FROM roster", conn)
                    conn.close()
                    
                    offline_df["Online Duration (Mins)"] = 0
                    offline_df = offline_df[["Student Name", "Online Duration (Mins)", "Status"]]
                    
                    # Concatenate datasets
                    all_present_records = pd.concat([valid_online_only, offline_df], ignore_index=True)
                    
                    # Resolve cross-platform duplicate checks if a user connected via phone while in the classroom
                    final_presence_summary = all_present_records.groupby("Student Name").agg({
                        "Online Duration (Mins)": "max",
                        "Status": lambda flags: "Present (Hybrid/Both)" if len(set(flags)) > 1 else list(flags)[0]
                    }).reset_index()
                    
                    # Merge against total structural roster to uncover true absent users
                    compiled_master_report = pd.merge(master_class_roster, final_presence_summary, on="Student Name", how="left")
                    compiled_master_report["Status"] = compiled_master_report["Status"].fillna("Absent")
                    compiled_master_report["Online Duration (Mins)"] = compiled_master_report["Online Duration (Mins)"].fillna(0).astype(int)
                    compiled_master_report.insert(0, "Session Date", target_date)
                    
                    st.dataframe(compiled_master_report, use_container_width=True)
                    
                    # Download Action Controller
                    final_csv_output = compiled_master_report.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Master Hybrid Attendance CSV Sheet",
                        data=final_csv_output,
                        file_name=f"Unified_Hybrid_Attendance_{target_date}.csv",
                        mime="text/csv",
                        type="primary",
                        use_container_width=True
                    )
        except Exception as e:
            st.error(f"Execution Error Parsing Script: {str(e)}")

# --- TAB 3: ROSTER PROFILES ---
with menu[2]:
    st.header("🗃️ Master Class Roster Management")
    st.markdown("Register your students here once. This allows the system to cross-reference your Microsoft Teams logs and offline registries to identify who is absent.")
    
    col_entry, col_preview = st.columns([1, 1])
    
    with col_entry:
        st.subheader("Bulk Import Roster")
        bulk_names_input = st.text_area("Paste Student Names (One full name per line):", height=200, placeholder="Example:\nJagtap Abhirucha\nSwapnil\nAjay gadade\nSaurabh Kumbhar")
        
        if st.button("Bulk Register Class List", type="primary"):
            if bulk_names_input.strip():
                formatted_lines = [line.strip() for line in bulk_names_input.split("\n") if line.strip()]
                new_records_counter = 0
                
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                for individual_name in formatted_lines:
                    try:
                        c.execute("INSERT INTO roster (name) VALUES (?)", (individual_name,))
                        new_records_counter += 1
                    except sqlite3.IntegrityError:
                        pass # Ignore names that already exist
                conn.commit()
                conn.close()
                st.success(f"Successfully processed database updates! Registered {new_records_counter} new students to the roster directory.")
                st.rerun()
            else:
                st.error("Please paste your student list context text box before clicking register.")
                
        st.markdown("---")
        if st.button("🗑️ Wipe Entire Master Roster Database", type="secondary", help="Deletes all registered students and historic presence logs from your local machine database"):
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("DELETE FROM roster")
            c.execute("DELETE FROM offline_logs")
            conn.commit()
            conn.close()
            st.warning("All master roster listings and recorded presence tables have been purged.")
            st.rerun()
            
    with col_preview:
        st.subheader("Registered Roster Database View")
        conn = sqlite3.connect(DB_NAME)
        current_db_roster = pd.read_sql_query("SELECT id as 'ID Index', name as 'Student Name' FROM roster ORDER BY name ASC", conn)
        conn.close()
        st.dataframe(current_db_roster, use_container_width=True, height=400)
