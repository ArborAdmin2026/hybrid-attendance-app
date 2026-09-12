import pandas as pd
import streamlit as st
import sqlite3
import re
from datetime import datetime

# Database Configuration Context
DB_NAME = "hybrid_attendance.db"

def init_db():
    """Initializes local storage loops for persistence."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS roster 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS offline_logs 
                 (date TEXT, name TEXT, status TEXT)''')
    conn.commit()
    conn.close()

init_db()

def parse_teams_duration(duration_str):
    """Converts standard Teams text frames ('1h 24m 42s' or '3m 22s') into clean integer minutes."""
    if pd.isna(duration_str) or not str(duration_str).strip():
        return 0
    duration_str = str(duration_str).lower().strip()
    
    hours = 0
    minutes = 0
    
    # Trace component sequences using regex loops
    h_match = re.search(r'(\d+)\s*h', duration_str)
    m_match = re.search(r'(\d+)\s*m', duration_str)
    
    if h_match:
        hours = int(h_match.group(1))
    if m_match:
        minutes = int(m_match.group(1))
    elif 'h' not in duration_str and 's' in duration_str:
        # Check if single value exists representing minutes explicitly
        digit_match = re.search(r'^\s*(\d+)\s*s', duration_str)
        if not digit_match:
            # Fallback to general integer tracing loops
            m_fallback = re.findall(r'\d+', duration_str)
            if m_fallback:
                minutes = int(m_fallback[0])
                
    return (hours * 60) + minutes

st.set_page_config(page_title="Data Analytics Attendance Console", layout="wide")
st.title("📊 Data Analytics Hybrid Attendance Engine")

# --- SIDEBAR CONTROL MECHANISMS ---
st.sidebar.header("🗓️ Session Parameters")
selected_date = st.sidebar.date_input("Class Session Date", datetime.now()).strftime("%Y-%m-%d")
noise_filter = st.sidebar.slider("Minimum Online Minutes (Noise Threshold)", 0, 45, 10)

# Main Application Menu Loop
menu = st.tabs(["🚶‍♂️ Classroom Check-In", "💻 Process Teams File & Merge", "🗃️ Student Roster Setup"])

# --- TAB 1: CLASSROOM REGISTRY ---
with menu[0]:
    st.header("🚶‍♂️ Physical Classroom Presence Check-In")
    st.caption("Mark offline students attending live in the room.")
    
    conn = sqlite3.connect(DB_NAME)
    roster_list = pd.read_sql_query("SELECT name FROM roster ORDER BY name ASC", conn)['name'].tolist()
    
    # Load today's presence hashes to keep selections active
    saved_offline = pd.read_sql_query("SELECT name FROM offline_logs WHERE date=?", conn, params=(selected_date,))['name'].tolist()
    conn.close()
    
    if not roster_list:
        st.info("⚠️ Master student database profile is empty. Please navigate to the 'Student Roster Setup' tab first.")
    else:
        st.write("Select the boxes next to students physically present in class:")
        
        # Build multi-column grids for clean rendering
        cols = st.columns(3)
        current_present = []
        
        for idx, student in enumerate(roster_list):
            with cols[idx % 3]:
                # Automatically check the box if they were already saved for this date
                is_checked = student in saved_offline
                if st.checkbox(student, value=is_checked, key=f"off_{student}_{selected_date}"):
                    current_present.append(student)
        
        if st.button("💾 Save Classroom Attendance Logs", type="primary"):
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            # Clear previous offline states for this day to write clean updates
            c.execute("DELETE FROM offline_logs WHERE date=?", (selected_date,))
            for name in current_present:
                c.execute("INSERT INTO offline_logs (date, name, status) VALUES (?, ?, 'Present (Offline)')", (selected_date, name))
            conn.commit()
            conn.close()
            st.success(f"Successfully recorded {len(current_present)} classroom students for {selected_date}!")

# --- TAB 2: TEAMS PIPELINE ENGINE ---
with menu[1]:
    st.header("💻 Teams Log Cleaner & Multi-Stream Data Joiner")
    st.markdown("Upload the messy text/CSV dump exported directly from your Microsoft Teams session.")
    
    uploaded_file = st.file_uploader("Upload Raw Teams CSV / TXT File", type=["csv", "txt"])
    
    if uploaded_file is not None:
        try:
            # Read files as raw strings to locate section markers programmatically
            raw_bytes = uploaded_file.read()
            raw_text = raw_bytes.decode("utf-8", errors="ignore")
            lines = raw_text.splitlines()
            
            # Locate section bounds dynamically
            participant_line_idx = None
            activity_line_idx = None
            
            for index, line in enumerate(lines):
                if "2. Participants" in line:
                    participant_line_idx = index
                elif "3. In-Meeting Activities" in line or "3. In-meeting activities" in line:
                    activity_line_idx = index
            
            if participant_line_idx is None:
                st.error("Error: Could not locate Section 2 ('2. Participants') inside the file.")
            else:
                # Segment section text lines safely
                end_idx = activity_line_idx if activity_line_idx else len(lines)
                section_2_lines = lines[participant_line_idx+1 : end_idx]
                
                # Reconstruct localized clean string frames
                clean_section_2 = "\n".join([l for l in section_2_lines if l.strip()])
                
                # Convert segmented TSV/CSV array frames into Pandas DataFrames
                from io import StringIO
                df_participants = pd.read_csv(StringIO(clean_section_2), sep='\t')
                
                # Handle layout variations gracefully if fields default to comma formats
                if df_participants.shape[0] <= 1:
                    df_participants = pd.read_csv(StringIO(clean_section_2), sep=',')
                
                # Standardize headers to handle hidden whitespaces
                df_participants.columns = [str(c).strip() for c in df_participants.columns]
                
                # Verify structural integrity criteria
                name_field = next((c for c in df_participants.columns if 'name' in c.lower()), None)
                duration_field = next((c for c in df_participants.columns if 'dur' in c.lower()), None)
                
                if not name_field or not duration_field:
                    st.error(f"Failed to isolate Name or Duration fields. Headers found: {list(df_participants.columns)}")
                else:
                    # Execute local data cleaning pipelines
                    cleaned_rows = []
                    for _, row in df_participants.iterrows():
                        raw_name = str(row[name_field]).strip()
                        
                        # Strip standard Teams system-generated tags like "(Unverified)"
                        clean_name = re.sub(r'\s*\(unverified\)\s*', '', raw_name, flags=re.IGNORECASE).strip()
                        
                        # Bypass organizer/session layout markers
                        if "meeting with data analytics" in clean_name.lower() or not clean_name:
                            continue
                            
                        raw_duration = str(row[duration_field])
                        calculated_minutes = parse_teams_duration(raw_duration)
                        
                        cleaned_rows.append({
                            "Student Name": clean_name,
                            "Online Duration (Mins)": calculated_minutes
                        })
                    
                    raw_parsed_df = pd.DataFrame(cleaned_rows)
                    
                    # Group by student name to eliminate duplicates from dropped connections
                    online_summary = raw_parsed_df.groupby("Student Name").agg({
                        "Online Duration (Mins)": "sum"
                    }).reset_index()
                    
                    # Apply operational noise filter threshold logic
                    online_summary["Status"] = online_summary["Online Duration (Mins)"].apply(
                        lambda x: "Present (Online)" if x >= noise_filter else "Absent / Dropped Noise"
                    )
                    
                    valid_online_df = online_summary[online_summary["Status"] == "Present (Online)"].copy()
                    
                    st.subheader("🟢 Isolated Active Online Attendees")
                    st.dataframe(valid_online_df, use_container_width=True)
                    
                    # --- STREAM JOINER LOGIC CONTROLLER ---
                    st.markdown("---")
                    st.subheader("🔀 Consolidated Hybrid Master Matrix")
                    
                    # Retrieve classroom logs for this date from the local database
                    conn = sqlite3.connect(DB_NAME)
                    offline_df = pd.read_sql_query(
                        "SELECT name as 'Student Name', status as 'Status' FROM offline_logs WHERE date=?", 
                        conn, params=(selected_date,)
                    )
                    # Pull master list to identify absent students
                    full_roster = pd.read_sql_query("SELECT name as 'Student Name' FROM roster", conn)
                    conn.close()
                    
                    offline_df["Online Duration (Mins)"] = 0
                    offline_df = offline_df[["Student Name", "Online Duration (Mins)", "Status"]]
                    
                    # Combine online data streams and offline data streams
                    combined_present_df = pd.concat([valid_online_df, offline_df], ignore_index=True)
                    
                    # Deduplicate entries if a student logged into Teams while in the room
                    combined_present_summary = combined_present_df.groupby("Student Name").agg({
                        "Online Duration (Mins)": "max",
                        "Status": lambda x: "Present (Hybrid/Both)" if len(set(x)) > 1 else list(x)[0]
                    }).reset_index()
                    
                    # Left join against full roster to catch absolute absentees
                    master_attendance_sheet = pd.merge(full_roster, combined_present_summary, on="Student Name", how="left")
                    master_attendance_sheet["Status"] = master_attendance_sheet["Status"].fillna("Absent")
                    master_attendance_sheet["Online Duration (Mins)"] = master_attendance_sheet["Online Duration (Mins)"].fillna(0).astype(int)
                    master_attendance_sheet.insert(0, "Session Date", selected_date)
                    
                    st.dataframe(master_attendance_sheet, use_container_width=True)
                    
                    # Download trigger
                    csv_output = master_attendance_sheet.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Unified Master Attendance CSV",
                        data=csv_output,
                        file_name=f"Hybrid_Attendance_Report_{selected_date}.csv",
                        mime="text/csv",
                        type="primary"
                    )
                    
        except Exception as e:
            st.error(f"Parsing Fault Trace: {str(e)}. Please check your Teams CSV file configuration schema.")

# --- TAB 3: ROSTER STORAGE DIRECTORY ---
with menu[2]:
    st.header("🗃️ Master Class Roster Management")
    st.caption("Register student identity frames here so the system can audit absence logs correctly.")
    
    c_import, c_display = st.columns(2)
    
    with c_import:
        st.subheader("Bulk Import Class List")
        bulk_text = st.text_area("Paste Student Names (One name per line text format):", height=200, placeholder="Example:\nJagtap Abhirucha\nSwapnil\nSaurabh Kumbhar")
        
        if st.button("Bulk Register Students", type="primary"):
            if bulk_text.strip():
                lines_to_add = [line.strip() for line in bulk_text.split("\n") if line.strip()]
                added_counter = 0
                
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                for student_name in lines_to_add:
                    try:
                        c.execute("INSERT INTO roster (name) VALUES (?)", (student_name,))
                        added_counter += 1
                    except sqlite3.IntegrityError:
                        pass # Ignore duplicates quietly
                conn.commit()
                conn.close()
                st.success(f"Successfully processed database updates. Registered {added_counter} new records.")
                st.rerun()
            else:
                st.error("Input text canvas context cannot be blank.")
                
        if st.button("🗑️ Wipe Entire Database Roster", type="secondary", help="Deletes all student profiles from local records"):
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("DELETE FROM roster")
            c.execute("DELETE FROM offline_logs")
            conn.commit()
            conn.close()
            st.warning("All master roster listings and recorded presence tables have been purged.")
            st.rerun()
            
    with c_display:
        st.subheader("Current Registered Student Roster")
        conn = sqlite3.connect(DB_NAME)
        registered_df = pd.read_sql_query("SELECT id as 'ID Index', name as 'Student Name' FROM roster ORDER BY name ASC", conn)
        conn.close()
        st.dataframe(registered_df, use_container_width=True, height=350)
