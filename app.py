import streamlit as st
import pandas as pd
import re
from io import BytesIO
from datetime import datetime
import os

st.set_page_config(page_title="Hybrid Attendance Tracker", page_icon="📊", layout="wide")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
STUDENT_FILE = os.path.join(DATA_DIR, "students.csv")
OFFLINE_FILE = os.path.join(DATA_DIR, "offline_attendance.csv")


def duration_to_minutes(duration):
    duration = str(duration)
    h = re.search(r"(\d+)h", duration)
    m = re.search(r"(\d+)m", duration)
    s = re.search(r"(\d+)s", duration)
    hours = int(h.group(1)) if h else 0
    mins = int(m.group(1)) if m else 0
    secs = int(s.group(1)) if s else 0
    return round(hours * 60 + mins + secs / 60, 2)


def clean_name(name):
    name = str(name).replace("(Unverified)", "")
    name = re.sub(r"\s+", " ", name)
    return name.strip().title()


def attendance_status(percent):
    if percent >= 75:
        return "Present"
    elif percent >= 30:
        return "Partial"
    return "Absent"


def read_teams_file(uploaded_file):
    uploaded_file.seek(0)
    data = uploaded_file.read()
    try:
        text = data.decode("utf-16")
    except:
        text = data.decode("latin1")

    rows = [line.split("\t") for line in text.splitlines()]
    return pd.DataFrame(rows)


def excel_download(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()


menu = st.sidebar.selectbox(
    "Select Module",
    ["Online Attendance", "Offline Check-In", "Trainer Dashboard"]
)

if menu == "Online Attendance":
    st.title("📊 Teams Attendance Tracker")

    uploaded_file = st.file_uploader("Upload Teams Attendance Report", type=["csv"])

    if uploaded_file:
        try:
            df_raw = read_teams_file(uploaded_file)

            start_idx = None
            for i in range(len(df_raw)):
                row_text = " ".join(df_raw.iloc[i].fillna("").astype(str))
                if "First Join" in row_text and "Last Leave" in row_text:
                    start_idx = i
                    break

            if start_idx is None:
                st.error("Participants section not found")
                st.stop()

            header = df_raw.iloc[start_idx].tolist()
            records = []

            for i in range(start_idx + 1, len(df_raw)):
                row = df_raw.iloc[i].tolist()
                txt = " ".join([str(x) for x in row])
                if "In-Meeting Activities" in txt:
                    break
                records.append(row)

            participants = pd.DataFrame(records, columns=header)
            participants = participants.dropna(subset=["Name"])
            participants["Name"] = participants["Name"].apply(clean_name)

            participants = participants[
                ~participants["Role"].astype(str).str.contains("Organiser|Organizer", case=False, na=False)
            ]

            participants["Minutes"] = participants["In-Meeting Duration"].apply(duration_to_minutes)

            result = participants.groupby("Name", as_index=False)["Minutes"].sum()

            session_duration = st.number_input("Session Duration (Minutes)", value=96)

            result["Attendance %"] = round(result["Minutes"] / session_duration * 100, 2)
            result["Status"] = result["Attendance %"].apply(attendance_status)

            st.dataframe(result, use_container_width=True)

            st.download_button(
                "Download Excel",
                excel_download(result),
                file_name="online_attendance.xlsx"
            )

        except Exception as e:
            st.error(str(e))

elif menu == "Offline Check-In":
    st.title("📱 Offline Student Check-In")

    if not os.path.exists(STUDENT_FILE):
        st.info("Upload students.csv in Trainer Dashboard first")
    else:
        students = pd.read_csv(STUDENT_FILE)
        student = st.selectbox("Select Your Name", students["Name"])

        if st.button("✅ Check In"):
            today = str(datetime.now().date())

            if os.path.exists(OFFLINE_FILE):
                attendance = pd.read_csv(OFFLINE_FILE)
            else:
                attendance = pd.DataFrame(columns=["Name", "Date", "Time"])

            already = attendance[
                (attendance["Name"] == student)
                & (attendance["Date"] == today)
            ]

            if len(already) > 0:
                st.warning("Attendance already marked.")
            else:
                new_row = pd.DataFrame([
                    {
                        "Name": student,
                        "Date": today,
                        "Time": datetime.now().strftime("%H:%M:%S")
                    }
                ])

                attendance = pd.concat([attendance, new_row], ignore_index=True)
                attendance.to_csv(OFFLINE_FILE, index=False)

                st.success(f"Attendance marked for {student}")

else:
    st.title("📈 Trainer Dashboard")

    master = st.file_uploader("Upload Student Master List", type=["csv"])

    if master:
        df = pd.read_csv(master)
        df.to_csv(STUDENT_FILE, index=False)
        st.success("Student Master List Saved")

    if os.path.exists(OFFLINE_FILE):
        attendance = pd.read_csv(OFFLINE_FILE)
        st.dataframe(attendance, use_container_width=True)
        st.metric("Offline Attendance Count", attendance["Name"].nunique())
