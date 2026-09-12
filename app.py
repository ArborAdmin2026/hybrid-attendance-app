import streamlit as st
import pandas as pd
import re
from io import BytesIO

# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(
    page_title="Teams Attendance Tracker",
    page_icon="📊",
    layout="wide"
)

# -----------------------------
# Helper Functions
# -----------------------------
def duration_to_minutes(duration):
    duration = str(duration)

    hours = 0
    minutes = 0
    seconds = 0

    h = re.search(r"(\d+)h", duration)
    m = re.search(r"(\d+)m", duration)
    s = re.search(r"(\d+)s", duration)

    if h:
        hours = int(h.group(1))

    if m:
        minutes = int(m.group(1))

    if s:
        seconds = int(s.group(1))

    return round(hours * 60 + minutes + seconds / 60, 2)


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

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(
            writer,
            index=False,
            sheet_name="Attendance"
        )

    return output.getvalue()


# -----------------------------
# Main App
# -----------------------------
st.title("📊 Teams Attendance Tracker")

st.write(
    "Upload your Microsoft Teams Attendance Report CSV "
    "and get a cleaned attendance register."
)

uploaded_file = st.file_uploader(
    "Upload Teams Attendance CSV",
    type=["csv"]
)

if uploaded_file is not None:

    try:

        # Read all rows without headers
        df_raw = pd.read_csv(
            uploaded_file,
            header=None,
            encoding="utf-8",
            sep = "\t",
            engine="python"
        )

        # Find Participants section
        start_idx = None

        for i in range(len(df_raw)):
            row_text = " ".join(
                df_raw.iloc[i].fillna("").astype(str)
            )

            if "First Join" in row_text and "Last Leave" in row_text:
                start_idx = i
                break

        if start_idx is None:
            st.error(
                "Participants section not found in the uploaded file."
            )
            st.stop()

        # Extract header
        header = df_raw.iloc[start_idx].tolist()

        data_rows = []

        for i in range(start_idx + 1, len(df_raw)):

            row = df_raw.iloc[i].tolist()

            row_text = " ".join(
                [str(x) for x in row]
            )

            if "In-Meeting Activities" in row_text:
                break

            data_rows.append(row)

        participants_df = pd.DataFrame(
            data_rows,
            columns=header
        )

        # Remove empty rows
        participants_df = participants_df.dropna(
            subset=["Name"]
        )

        # Clean names
        participants_df["Name"] = (
            participants_df["Name"]
            .astype(str)
            .apply(clean_name)
        )

        # Remove organizer
        participants_df = participants_df[
            ~participants_df["Role"]
            .astype(str)
            .str.contains(
                "Organiser|Organizer",
                case=False,
                na=False
            )
        ]

        # Duration conversion
        participants_df["Minutes"] = (
            participants_df["In-Meeting Duration"]
            .apply(duration_to_minutes)
        )

        # Merge duplicate attendees
        cleaned_df = (
            participants_df.groupby(
                "Name",
                as_index=False
            )["Minutes"]
            .sum()
        )

        st.sidebar.header("Settings")

        session_duration = st.sidebar.number_input(
            "Session Duration (Minutes)",
            min_value=1,
            value=96
        )

        cleaned_df["Attendance %"] = round(
            (cleaned_df["Minutes"] / session_duration) * 100,
            2
        )

        cleaned_df["Status"] = cleaned_df[
            "Attendance %"
        ].apply(attendance_status)

        cleaned_df = cleaned_df.sort_values(
            by="Attendance %",
            ascending=False
        )

        # Dashboard
        st.header("📈 Dashboard")

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

        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Students",
            total_students
        )

        c2.metric(
            "Present",
            present_count
        )

        c3.metric(
            "Partial",
            partial_count
        )

        c4.metric(
            "Absent",
            absent_count
        )

        # Chart
        st.subheader("Attendance Status")

        chart_data = (
            cleaned_df["Status"]
            .value_counts()
        )

        st.bar_chart(chart_data)

        # Table
        st.subheader("Cleaned Attendance")

        st.dataframe(
            cleaned_df,
            use_container_width=True
        )

        # Download
        excel_file = convert_excel(cleaned_df)

        st.download_button(
            label="📥 Download Excel",
            data=excel_file,
            file_name="cleaned_attendance.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Error: {e}")
