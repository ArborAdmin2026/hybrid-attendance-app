import streamlit as st
import pandas as pd
import plotly.express as px
import re
from io import BytesIO

st.set_page_config(page_title='Enterprise Attendance Platform',layout='wide')

st.markdown('''
<style>
.main {padding-top:1rem;}
.metric-card{padding:10px;border-radius:10px;background:#f3f4f6;}
</style>
''',unsafe_allow_html=True)

# ---------- Helpers ----------

def clean_name(name):
    if pd.isna(name):
        return ''
    name=str(name).strip().lower()
    name=re.sub(r'\(unverified\)','',name,flags=re.I)
    name=re.sub(r'\s+',' ',name)
    return name.strip().title()


def clean_email(email):
    if pd.isna(email):
        return ''
    return str(email).strip().lower()


def parse_duration(v):
    if pd.isna(v):
        return 0
    s=str(v).lower()
    h=re.search(r'(\d+)h',s)
    m=re.search(r'(\d+)m',s)
    sec=re.search(r'(\d+)s',s)
    total=0
    if h: total+=int(h.group(1))*60
    if m: total+=int(m.group(1))
    if sec: total+=int(sec.group(1))/60
    if total>0: return total
    try:
        return float(v)
    except:
        return 0


def detect_source(cols):
    c=[x.lower() for x in cols]
    if 'join time' in c and 'leave time' in c:
        return 'Microsoft Teams'
    return 'Manual Upload'


def load_file(file):
    try:
        if file.name.endswith('.xlsx'):
            df=pd.read_excel(file)
        else:
            try:
                df=pd.read_csv(file)
            except:
                file.seek(0)
                df=pd.read_csv(file,encoding='utf-16',sep='\t')
        return df
    except Exception as e:
        st.error(str(e))
        return None


def build_excel(data,duplicates,exceptions):
    output=BytesIO()
    with pd.ExcelWriter(output,engine='openpyxl') as writer:
        data.to_excel(writer,sheet_name='Attendance Summary',index=False)
        duplicates.to_excel(writer,sheet_name='Duplicates',index=False)
        exceptions.to_excel(writer,sheet_name='Exceptions',index=False)
    return output.getvalue()

# ---------- UI ----------

st.title('🎓 Enterprise Attendance Management Platform')

with st.sidebar:
    duration=st.number_input('Class Duration (Minutes)',30,1000,90)
    threshold=st.slider('Attendance Threshold %',0,100,75)

files=st.file_uploader('Upload CSV or Excel Attendance Files',type=['csv','xlsx'],accept_multiple_files=True)

if files:
    frames=[]

    for file in files:
        df=load_file(file)
        if df is None:
            continue

        df.columns=[str(c).strip().title() for c in df.columns]

        rename={
            'Full Name':'Name',
            'Display Name':'Name',
            'User Name':'Name',
            'Email Address':'Email',
            'Participant Id (Upn)':'Email',
            'In-Meeting Duration':'Duration'
        }

        df.rename(columns=rename,inplace=True)

        if 'Name' in df.columns:
            df['Name']=df['Name'].apply(clean_name)

        if 'Email' in df.columns:
            df['Email']=df['Email'].apply(clean_email)
        else:
            df['Email']=''

        df['Source']=detect_source(df.columns)
        frames.append(df)

    master=pd.concat(frames,ignore_index=True)

    if 'Duration' in master.columns:
        master['Duration (Minutes)']=master['Duration'].apply(parse_duration)
    elif {'Join Time','Leave Time'}.issubset(master.columns):
        master['Join Time']=pd.to_datetime(master['Join Time'],errors='coerce')
        master['Leave Time']=pd.to_datetime(master['Leave Time'],errors='coerce')
        master['Duration (Minutes)']=(master['Leave Time']-master['Join Time']).dt.total_seconds()/60
    else:
        master['Duration (Minutes)']=duration

    master['Duration (Minutes)']=master['Duration (Minutes)'].fillna(0)

    master['Unique_ID']=master.apply(
        lambda r:r['Email'] if str(r['Email']).strip() else r.get('Name',''),axis=1
    )

    duplicates=master[master.duplicated('Unique_ID',keep=False)].copy()

    agg={
        'Name':'first',
        'Email':'first',
        'Source':'first',
        'Duration (Minutes)':'sum'
    }

    final=master.groupby('Unique_ID',as_index=False).agg(agg)

    final['Attendance %']=((final['Duration (Minutes)']/duration)*100).clip(upper=100)

    final['Status']=final['Attendance %'].apply(
        lambda x:'Present' if x>=threshold else 'Partial/Absent'
    )

    exceptions=final[final['Attendance %']<threshold].copy()

    quality=((len(final)/max(len(master),1))*100)

    c1,c2,c3,c4=st.columns(4)
    c1.metric('Uploaded Records',len(master))
    c2.metric('Unique Participants',len(final))
    c3.metric('Duplicates Removed',len(master)-len(final))
    c4.metric('Quality Score',f'{quality:.1f}%')

    tab1,tab2,tab3,tab4=st.tabs(['Dashboard','Roster','Duplicates','Exceptions'])

    with tab1:
        st.subheader('Attendance Analytics')

        fig1=px.pie(final,names='Status',title='Attendance Status')
        st.plotly_chart(fig1,use_container_width=True)

        fig2=px.histogram(final,x='Attendance %',title='Attendance Distribution')
        st.plotly_chart(fig2,use_container_width=True)

    with tab2:
        search=st.text_input('Search Student')
        view=final.copy()
        if search:
            view=view[view['Name'].str.contains(search,case=False,na=False)]
        st.dataframe(view,use_container_width=True)

    with tab3:
        st.dataframe(duplicates,use_container_width=True)

    with tab4:
        st.dataframe(exceptions,use_container_width=True)

    csv_data=final.to_csv(index=False).encode('utf-8')

    st.download_button(
        'Download Cleaned CSV',
        csv_data,
        'attendance_cleaned.csv',
        'text/csv'
    )

    excel_data=build_excel(final,duplicates,exceptions)

    st.download_button(
        'Download Excel Report',
        excel_data,
        'attendance_report.xlsx',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

else:
    st.info('Upload attendance files to begin processing.')
