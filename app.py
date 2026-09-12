import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from io import BytesIO

DB="attendancehub.db"

st.set_page_config(page_title="AttendanceHub Pro", layout="wide")

conn=sqlite3.connect(DB)
conn.execute("CREATE TABLE IF NOT EXISTS attendance(att_date TEXT, student_name TEXT, mode TEXT, status TEXT)")
conn.commit()

st.title("AttendanceHub Pro - Reports")

df=pd.read_sql_query("SELECT * FROM attendance", conn)
conn.close()

st.dataframe(df, use_container_width=True)

col1,col2=st.columns(2)

with col1:
    st.download_button(
        'Download CSV',
        df.to_csv(index=False).encode('utf-8'),
        file_name='attendance_report.csv',
        mime='text/csv'
    )

with col2:
    excel_buffer=BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Attendance', index=False)
    excel_buffer.seek(0)

    st.download_button(
        'Download Excel',
        excel_buffer.getvalue(),
        file_name=f"Attendance_Report_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
