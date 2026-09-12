import pandas as pd
import streamlit as st
import sqlite3
from io import BytesIO
from datetime import datetime

# Initialize SQLite database
DB_NAME = "attendance_db.sqlite"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS roster 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, email TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance_logs 
                 (date TEXT, name TEXT, email TEXT, platform TEXT, duration TEXT)''')
    conn.commit()
    conn.close()

init_db()

st.set_page_config(page_title="Hybrid Attendance Engine", layout="wide")

# Sidebar Navigation (No password required)
st.sidebar.title("📋 Navigation Menu")
menu = st.sidebar.radio(
    "Go To Workspace:", 
    ["Student Check-in Portal", "Logs & Teams Cleaner Pipeline", "Master Roster Management"]
)

session_date = st.sidebar.date_input("Target Lecture Date", datetime.now()).strftime("%Y-%m-%d")
noise_threshold = st.sidebar.slider("Online Noise Aggregation Filter (Mins)", 5, 45, 15)

# --- 1. STUDENT VIEW HUB ---
if menu == "Student Check-in Portal":
    st.title("📱 Offline Student Kiosk Check-In Portal")
    st.write("Please confirm your physical presence by choosing your name from the verified roster below.")
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    conn = sqlite3.connect(DB_NAME)
    students = pd.read_sql_query("SELECT name FROM roster ORDER BY name ASC", conn)['name'].tolist()
    # Fetch today's check-ins to show live logs
    checked_in_today = pd.read_sql_query("SELECT name FROM attendance_logs WHERE date=? AND platform='Offline'", conn)['name'].tolist()
    conn.close()
    
    if not students:
        st.info("The Master Roster directory is currently empty. Go to 'Master Roster Management' to add students.")
    else:
        c_left, c_right = st.columns()
        
        with c_left:
            selected_student = st.selectbox("Select Your Registered Name:", ["-- Choose Name --"] + students)
            if st.button("Submit Presence Verification", use_container_width=True):
                if selected_student != "-- Choose Name --":
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    
                    c.execute("SELECT email FROM roster WHERE name=?", (selected_student,))
                    res = c.fetchone()
                    email = res[0] if res else "Offline Registry"
                    
                    c.execute("SELECT * FROM attendance_logs WHERE date=? AND name=? AND platform='Offline'", (current_date, selected_student))
                    if c.fetchone():
                        st.warning("Attendance confirmation already checked in for today's date!")
                    else:
                        c.execute("INSERT INTO attendance_logs VALUES (?, ?, ?, 'Offline', 'Classroom')", (current_date, selected_student, email))
                        conn.commit()
                        st.success(f"Success! Attendance confirmed for {selected_student}.")
                        st.rerun()
                    conn.close()
        
        with c_right:
            st.subheader("Logged In Today")
            if checked_in_today:
                for name in checked_in_today:
                    st.text(f"✅ {name}")
            else:
                st.caption("No offline sign-ins yet.")

# --- 2. CLEANER VIEW ---
elif menu == "Logs & Teams Cleaner Pipeline":
    st.title("💻 Process Online Logs & Merge Streams")
    uploaded_file = st.file_uploader("Drop Raw Teams CSV Export Here", type=["csv"])
    cleaned_online = []
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            df.columns = [c.strip() for c in df.columns]
            
            name_col = next((c for c in df.columns if 'name' in c.lower()), None)
            email_col = next((c for c in df.columns if 'email' in c.lower()), None)
            dur_col = next((c for c in df.columns if 'dur' in c.lower()), None)
            
            if name_col and dur_col:
                summary = df.groupby(name_col).agg({
                    dur_col: 'sum',
                    **( {email_col: 'first'} if email_col else {} )
                }).reset_index()
                
                summary.columns = ['Name', 'Duration', 'Email'] if email_col else ['Name', 'Duration']
                if 'Email' not in summary.columns:
                    summary['Email'] = 'Online Student Log'
                    
                summary['Status'] = summary['Duration'].apply(
                    lambda x: "Present (Online)" if x >= noise_threshold else "Dropped / Noise"
                )
                
                valid_online = summary[summary['Status'] == "Present (Online)"]
                st.success(f"Log isolated successfully. Found {len(valid_online)} valid online attendees.")
                st.dataframe(valid_online)
                
                for _, row in valid_online.iterrows():
                    cleaned_online.append((session_date, row['Name'].strip(), row['Email'], 'Online', f"{row['Duration']} mins"))
            else:
                st.error("Metrics structural lookup failed inside this CSV format.")
        except Exception as e:
            st.error(f"Processing Error: {str(e)}")

    # Local Database Fetch
    conn = sqlite3.connect(DB_NAME)
    offline_today = pd.read_sql_query("SELECT name, email, platform FROM attendance_logs WHERE date=? AND platform='Offline'", conn, params=(session_date,))
    conn.close()

    st.subheader(f"🚶‍♂️ Logged Classroom Registries for Target Date: {len(offline_today)}")
    st.dataframe(offline_today)

    if st.button("💾 Compile & Build Closed-Loop Report"):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("DELETE FROM attendance_logs WHERE date=? AND platform='Online'", (session_date,))
        if cleaned_online:
            c.executemany("INSERT INTO attendance_logs VALUES (?, ?, ?, ?, ?)", cleaned_online)
        conn.commit()
        
        master_df = pd.read_sql_query("SELECT date, name, email, platform, duration FROM attendance_logs WHERE date=?", conn, params=(session_date,))
        conn.close()
        
        st.subheader("📋 Consolidated Master Attendance Matrix")
        st.dataframe(master_df)
        
        st.download_button(
            label="📥 Export Master CSV Roster File",
            data=master_df.to_csv(index=False).encode('utf-8'),
            file_name=f"Master_Attendance_{session_date}.csv",
            mime="text/csv"
        )

# --- 3. ROSTER UPLOAD MANAGEMENT ---
elif menu == "Master Roster Management":
    st.title("🗃️ Student Identity Database")
    c1, c2 = st.columns()
    with c1:
        st.subheader("Bulk Import Roster")
        bulk_input = st.text_area("Paste Names (One name per line):", height=150, help="Great for copy-pasting a list from Excel or text files.")
        if st.button("Bulk Save Entries"):
            if bulk_input.strip():
                names_list = [line.strip() for line in bulk_input.split('\n') if line.strip()]
                inserted_count = 0
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                for name in names_list:
                    try:
                        c.execute("INSERT INTO roster (name, email) VALUES (?, ?)", (name, "Bulk Registered"))
                        inserted_count += 1
                    except sqlite3.IntegrityError:
                        pass # Skip duplicates gracefully
                conn.commit()
                conn.close()
                st.success(f"Successfully batch-imported {inserted_count} new students!")
                st.rerun()
            else:
                st.error("Input area cannot be empty.")

        st.markdown("---")
        st.subheader("Single Registration")
        n_name = st.text_input("Student Name")
        n_email = st.text_input("Email ID (Optional)", value="Manual Entry")
        if st.button("Save Single Entry"):
            if n_name.strip():
                try:
                    conn = sqlite3.connect(DB_NAME)
                    c = conn.cursor()
                    c.execute("INSERT INTO roster (name, email) VALUES (?, ?)", (n_name.strip(), n_email))
                    conn.commit()
                    conn.close()
                    st.success(f"Added {n_name} successfully.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.warning("Identity entry already exists.")
            else:
                st.error("Name column cannot be blank.")
    with c2:
        st.subheader("Current Database Directory")
        conn = sqlite3.connect(DB_NAME)
        r_df = pd.read_sql_query("SELECT id, name, email FROM roster ORDER BY name ASC", conn)
        conn.close()
        st.dataframe(r_df, use_container_width=True, height=450)
