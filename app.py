import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import qrcode
from io import BytesIO

DB_NAME = "attendance_pro.db"

st.set_page_config(page_title="AttendanceHub Pro", page_icon="🎓", layout="wide")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)")
    cur.execute("CREATE TABLE IF NOT EXISTS attendance(date TEXT, student_name TEXT, mode TEXT, status TEXT)")
    conn.commit()
    conn.close()

init_db()

st.title("🎓 AttendanceHub Pro")
menu = st.sidebar.radio("Navigation", ["Dashboard","Students","QR Attendance"])

if menu == "Students":
    names = st.text_area("Paste student names (one per line)")
    if st.button("Save Students"):
        conn = sqlite3.connect(DB_NAME)
        cur = conn.cursor()
        for n in names.splitlines():
            try:
                cur.execute("INSERT OR IGNORE INTO students(name) VALUES(?)", (n.strip(),))
            except:
                pass
        conn.commit()
        conn.close()
        st.success("Saved")

elif menu == "QR Attendance":
    today = datetime.now().strftime("%Y-%m-%d")
    qr_text = f"ATTENDANCE|{today}"
    img = qrcode.make(qr_text)
    buf = BytesIO()
    img.save(buf, format="PNG")
    st.image(buf.getvalue())
    st.code(qr_text)

    conn = sqlite3.connect(DB_NAME)
    students = pd.read_sql_query("SELECT name FROM students", conn)
    conn.close()

    if len(students):
        student = st.selectbox("Student", students['name'])
        if st.button("Mark Attendance"):
            conn = sqlite3.connect(DB_NAME)
            conn.execute("INSERT INTO attendance VALUES (?,?,?,?)", (today, student, 'QR', 'Present'))
            conn.commit()
            conn.close()
            st.success('Attendance Marked')

else:
    conn = sqlite3.connect(DB_NAME)
    s = pd.read_sql_query("SELECT * FROM students", conn)
    a = pd.read_sql_query("SELECT * FROM attendance", conn)
    conn.close()
    st.metric("Total Students", len(s))
    st.metric("Attendance Records", len(a))
    st.dataframe(a, use_container_width=True)
