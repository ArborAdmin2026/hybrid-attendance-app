import pandas as pd
import streamlit as st
import sqlite3
import qrcode
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

st.set_page_config(page_title="Secure Hybrid Attendance Engine", layout="wide")

# --- SECURE APPARATUS CONTROLLER ---
# Change "admin123" to your preferred private master password
ADMIN_PASSWORD = "admin123" 

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

# Sidebar Role Selector
st.sidebar.title("🔐 Access Control")
user_role = st.sidebar.selectbox("Select View Profile", ["Student Check-in Portal", "Trainer Dashboard Workspace"])

# --- TRAINER PASSWORD GATEFOOT ---
if user_role == "Trainer Dashboard Workspace":
    if not st.session_state['authenticated']:
        st.subheader("Trainer Security Verification")
        pwd_input = st.text_input("Enter Master Password:", type="password")
        if st.button("Unlock Dashboard"):
            if pwd_input == ADMIN_PASSWORD:
                st.session_state['authenticated'] = True
                st.success("Access Granted.")
                st.rerun()
            else:
                st.error("Invalid Credentials. Access Denied.")
                
    if st.session_state['authenticated']:
        if st.sidebar.button("Logout from Session"):
            st.session_state['authenticated'] = False
            st.rerun()
            
        # --- TRAINER WORKSPACE CODE BLOCKS ---
        st.title("🎛️ Trainer Master Control Panel")
        menu = st.radio("Navigation Workspaces", ["Logs & Teams Cleaner Pipeline", "Master Roster Management"], horizontal=True)
        
        session_date = st.sidebar.date_input("Target Lecture Date", datetime.now()).strftime("%Y-%m-%d")
        noise_threshold = st.sidebar.slider("Online Noise Aggregation Filter (Mins)", 5, 45, 15)

        # 1. CLEANER VIEW
        if menu == "Logs & Teams Cleaner Pipeline":
            st.header("💻 Process Online Logs & Merge Streams")
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
                            cleaned_online.append((session_date, row['Name'], row['Email'], 'Online', f"{row['Duration']} mins"))
                    else:
                        st.error("Metrics structural lookup failed inside this CSV format.")
                except Exception as e:
                    st.error(f"Processing Error: {str(e)}")

            # Local Database Fetch
            conn = sqlite3.connect(DB_NAME)
            offline_today = pd.read_sql_query("SELECT name, email, platform FROM attendance_logs WHERE date=? AND platform='Offline'", conn, params=(session_date,))
            conn.close()

            st.subheader(f"🚶‍♂️ Logged Classroom Registries for Today: {len(offline_today)}")
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

        # 2. ROSTER MANAGEMENT VIEW
        elif menu == "Master Roster Management":
            st.header("🗃️ Student Identity Database")
            c1, c2 = st.columns([1, 2])
            with c1:
                st.subheader("Register New Student")
                n_name = st.text_input("Student Name")
                n_email = st.text_input("Email ID")
                if st.button("Save Entry to DB"):
                    if n_name:
                        try:
                            conn = sqlite3.connect(DB_NAME)
                            c = conn.cursor()
                            c.execute("INSERT INTO roster (name, email) VALUES (?, ?)", (n_name, n_email))
                            conn.commit()
                            conn.close()
                            st.success(f"Added {n_name} successfully.")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.warning("Identity entry exists.")
                    else:
                        st.error("Name column cannot be blank.")
            with c2:
                st.subheader("Current Database Directory")
                conn = sqlite3.connect(DB_NAME)
                r_df = pd.read_sql_query("SELECT id, name, email FROM roster", conn)
                conn.close()
                st.dataframe(r_df, use_container_width=True)

# --- 4. SECURE CUSTOMER/STUDENT VIEW HUB ---
else:
    # Reset internal authentication state when moving out of admin screen
    st.title("📱 Offline Student Kiosk Check-In Portal")
    st.write("Please confirm your physical presence by choosing your name from the verified roster below.")
    
    session_date = datetime.now().strftime("%Y-%m-%d")
    
    conn = sqlite3.connect(DB_NAME)
    students = pd.read_sql_query("SELECT name FROM roster", conn)['name'].tolist()
    conn.close()
    
    if not students:
        st.info("The Master Roster directory is currently empty. Ask the trainer to add students from the dashboard.")
    else:
        selected_student = st.selectbox("Select Your Registered Name:", ["-- Choose Name --"] + students)
        if st.button("Submit Presence Verification"):
            if selected_student != "-- Choose Name --":
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                
                c.execute("SELECT email FROM roster WHERE name=?", (selected_student,))
                res = c.fetchone()
                email = res[0] if res else "Offline Registry"
                
                c.execute("SELECT * FROM attendance_logs WHERE date=? AND name=? AND platform='Offline'", (session_date, selected_student))
                if c.fetchone():
                    st.warning("Attendance confirmation already checked in for today's date!")
                else:
                    c.execute("INSERT INTO attendance_logs VALUES (?, ?, ?, 'Offline', 'Classroom')", (session_date, selected_student, email))
                    conn.commit()
                    st.success(f"Success! Attendance confirmed for {selected_student}.")
                conn.close()
