import streamlit as st
import pandas as pd
import re
from io import BytesIO

st.set_page_config(
    page_title="Teams Attendance Tracker",
    page_icon="📊",
    layout="wide"
)

# ---------------------------
# Helper Functions
# ---------------------------

def duration_to_minutes(duration):
    """
    Convert Teams duration format:
    1h 24m 42s
    28m 40s
    3m 22s
    """

    duration = str(duration)

    hours = 0
    minutes = 0
    seconds = 0

    h = re.search(r'(\d+)h', duration)
    m = re.search(r'(\d+)m', duration)
    s = re.search(r'(\d+)s', duration)

    if h:
        hours = int(h.group(1))

    if m:
        minutes = int(m.group(1))

    if s:
        seconds = int(s.group(1))

    return round(hours * 60 + minutes + seconds / 60, 2)


def extract_participants_section(df_raw):
    """
    Extract only the participant table from Teams CSV
    """

    start_idx = None

    for i in range(len(df_raw)):
        row = " ".join(df_raw.iloc[i].astype(str).tolist())

        if "Name" in row and "First Join" in row:
            start_idx = i
            break

    if start_idx is None:
        return None

    header = df_raw.iloc[start_idx].tolist()

    data = []

    for i in range(start_idx + 1, len(df_raw)):
        row = df_raw.iloc[i].tolist()

        if str(row[0]).strip().startswith("- In-Meeting Activities"):
            break

        data.append(row)

    df = pd.DataFrame(data, columns=header)

    return df


def clean_name(name):

    name = str(name)

    name = name.replace("(Unverified)", "")
    name = re.sub(r"\s+", " ", name)

    return name.strip().title()


def attendance_status(percent):

    if percent >= 75:
        return "Present"

    elif percent >= 30:
        return "Partial"

    else:
        return "Absent"


def convert_excel(df):

    output = BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(
            writer,
            index=False,
            sheet_name="Attendance"
        )

    return output.getvalue()


# ---------------------------
# App UI
# ---------------------------

st.title("📊 Teams Attendance Tracker")

st.markdown(
    """
    Upload Microsoft Teams Attendance Report
    and get a cleaned attendance register.
    """
)

uploaded_file = st.file_uploader(
    "Upload Attendance CSV",
    type=["csv"]
)

if uploaded_file:

    try:

        df_raw = pd.read_csv(
            uploaded_file,
            header=None,
            engine="python"
        )

        participants_df = extract_participants_section(df_raw)

        if participants_df is None:
            st.error("Participants section not found.")
            st.stop()

        # ---------------------------
        # Cleaning
        # ---------------------------

        participants_df["Name"] = (
            participants_df["Name"]
            .apply(clean_name)
        )

        participants_df = participants_df[
            participants_df["Role"]
            .str.contains("Organiser|Organizer",
                          case=False,
                          na=False) == False
        ]

        participants_df["Minutes"] = (
            participants_df["In-Meeting Duration"]
            .apply(duration_to_minutes)
        )

        cleaned_df = (
            participants_df
            .groupby("Name", as_index=False)
            .agg({
                "Minutes": "sum"
            })
        )

        session_duration = st.number_input(
            "Session Duration (Minutes)",
            min_value=1,
            value=96
        )

        cleaned_df["Attendance %"] = round(
            (cleaned_df["Minutes"] / session_duration) * 100,
            2
        )

        cleaned_df["Status"] = (
            cleaned_df["Attendance %"]
            .apply(attendance_status)
        )

        cleaned_df = cleaned_df.sort_values(
            by="Attendance %",
            ascending=False
        )

        # ---------------------------
        # Dashboard
        # ---------------------------

        st.header("📈 Attendance Dashboard")

        total_students = len(cleaned_df)

        present_count = (
            cleaned_df["Status"] == "Present"
        ).sum()

        partial_count = (
            cleaned_df["Status"] == "Partial"
        ).sum()

        absent_count = (
            cleaned_df["Status"] == "Absent"
        ).sum()

        c1, c2, 
