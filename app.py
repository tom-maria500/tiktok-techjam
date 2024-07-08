import streamlit as st
from st_on_hover_tabs import on_hover_tabs
from streamlit_option_menu import option_menu
from streamlit_calendar import calendar
from streamlit_modal import Modal

import datetime
import os
import pickle
import json
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from openai import OpenAI
import dotenv

import queue
import time
from google.cloud import speech
import pyaudio
from google.oauth2 import service_account

import threading 

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

from clientDashboard import showClientDashboard
from bs4 import BeautifulSoup

# Sample data for TikTok CRM
client_data = {
    "Amazon": {
        "Industry": "E-commerce",
        "Status": "Negotiating",
        "Point of Contact": "Maria Thomas",
        "Email": "maria.tom06@gmail.com",
        "VectorStoreID": ""
    },
    "Gymshark": {
        "Industry": "Fitness Apparel",
        "Status": "Negotiating",
        "Point of Contact": "Michael Brown",
        "Email": "michael@gymshark.com",
        "VectorStoreID": ""
    },
    "Crocs": {
        "Industry": "Footwear",
        "Status": "Negotiating",
        "Point of Contact": "Tom Harris",
        "Email": "tom@crocs.com",
        "VectorStoreID": ""
    }
}

# Convert dict into json
json_data = json.dumps(client_data)

# Create a pandas DataFrame from the dictionary
df = pd.DataFrame.from_dict(client_data, orient='index')

dotenv.load_dotenv()
client_chatbot = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

client_file = 'smart_chat_service_account.json'
speech_credentials = service_account.Credentials.from_service_account_file(client_file)

# Audio recording parameters
STREAMING_LIMIT = 240000  # 4 minutes
SAMPLE_RATE = 16000
CHUNK_SIZE = int(SAMPLE_RATE / 10)  # 100ms

def get_current_time() -> int:
    return int(round(time.time() * 1000))

# from google api 
class ResumableMicrophoneStream:
    """Opens a recording stream as a generator yielding the audio chunks."""

    def __init__(self, rate: int, chunk_size: int, mic_index: int, spkr_index: int) -> None:
        """Creates a resumable microphone stream.

        Args:
        rate: The audio file's sampling rate.
        chunk_size: The audio file's chunk size.
        mic_index: The device index for the microphone.
        spkr_index: The device index for the virtual audio device.
        """
        self._rate = rate
        self.chunk_size = chunk_size
        self._num_channels = 1
        self._buff = queue.Queue()
        self.closed = True
        self.start_time = get_current_time()
        self.restart_counter = 0
        self.audio_input = []
        self.last_audio_input = []
        self.result_end_time = 0
        self.is_final_end_time = 0
        self.final_request_end_time = 0
        self.bridging_offset = 0
        self.last_transcript_was_final = False
        self.new_stream = True
        self._audio_interface = pyaudio.PyAudio()
        self._mic_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            channels=self._num_channels,
            rate=self._rate,
            input=True,
            input_device_index=mic_index,
            frames_per_buffer=self.chunk_size,
            stream_callback=self._fill_buffer,
        )
        self._spkr_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            channels=self._num_channels,
            rate=self._rate,
            input=True,
            input_device_index=spkr_index,
            frames_per_buffer=self.chunk_size,
            stream_callback=self._fill_buffer,
        )

    def __enter__(self):
        self.closed = False
        return self

    def __exit__(self, type, value, traceback):
        self._mic_stream.stop_stream()
        self._mic_stream.close()
        self._spkr_stream.stop_stream()
        self._spkr_stream.close()
        self.closed = True
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, *args, **kwargs):
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            data = []

            if self.new_stream and self.last_audio_input:
                chunk_time = STREAMING_LIMIT / len(self.last_audio_input)

                if chunk_time != 0:
                    if self.bridging_offset < 0:
                        self.bridging_offset = 0

                    if self.bridging_offset > self.final_request_end_time:
                        self.bridging_offset = self.final_request_end_time

                    chunks_from_ms = round(
                        (self.final_request_end_time - self.bridging_offset)
                        / chunk_time
                    )

                    self.bridging_offset = round(
                        (len(self.last_audio_input) - chunks_from_ms) * chunk_time
                    )

                    for i in range(chunks_from_ms, len(self.last_audio_input)):
                        data.append(self.last_audio_input[i])

                self.new_stream = False

            chunk = self._buff.get()
            self.audio_input.append(chunk)

            if chunk is None:
                return
            data.append(chunk)
            while True:
                try:
                    chunk = self._buff.get(block=False)

                    if chunk is None:
                        return
                    data.append(chunk)
                    self.audio_input.append(chunk)

                except queue.Empty:
                    break

            yield b"".join(data)

def listen_print_loop(responses, stream, filename):
    transcript_container = st.empty()
    full_transcript = []

    for response in responses:
        if get_current_time() - stream.start_time > STREAMING_LIMIT:
            stream.start_time = get_current_time()
            break

        if not response.results:
            continue

        result = response.results[0]
        if not result.alternatives:
            continue

        transcript = result.alternatives[0].transcript
        result_seconds = 0
        result_micros = 0

        if result.result_end_time.seconds:
            result_seconds = result.result_end_time.seconds
        if result.result_end_time.microseconds:
            result_micros = result.result_end_time.microseconds

        stream.result_end_time = int((result_seconds * 1000) + (result_micros / 1000))

        if result.is_final:
            output = f"{transcript}"
            full_transcript.append(output)
            stream.is_final_end_time = stream.result_end_time
            stream.last_transcript_was_final = True

        else:
            interim_output = f"{transcript} (interim)"
            full_transcript_with_interim = full_transcript + [interim_output]
            stream.last_transcript_was_final = False

        # formatted_transcript = "\n".join(full_transcript_with_interim if not result.is_final else full_transcript)

        if result.is_final:
            with open(filename, "w") as f:
                for item in full_transcript:
                    f.write(f"{item}\n")

def record_audio(client, streaming_config, mic_index, spkr_index, filename):
    mic_manager = ResumableMicrophoneStream(SAMPLE_RATE, CHUNK_SIZE, mic_index, spkr_index)
    
    with mic_manager as stream:
        while not stream.closed:
            stream.audio_input = []
            audio_generator = stream.generator()
            requests = (
                speech.StreamingRecognizeRequest(audio_content=content)
                for content in audio_generator
            )

            responses = client.streaming_recognize(streaming_config, requests)
            listen_print_loop(responses, stream, filename)

            if stream.result_end_time > 0:
                stream.final_request_end_time = stream.is_final_end_time
                stream.result_end_time = 0
                stream.last_audio_input = []
                stream.last_audio_input = stream.audio_input
                stream.audio_input = []
                stream.restart_counter = stream.restart_counter + 1
                stream.new_stream = True

def read_text_file(text_file_path):
    with open(text_file_path, "r") as file:
        text_content = file.read()
    return text_content

def generate_response(transcription):
    response = client_chatbot.chat.completions.create(
        model="gpt-4",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "As an AI with expertise in language analysis, your task is to analyze the context of the text and suggest possible statements and follow-up questions to the text provided. Please generate the most relevant three based on the context. This should only be a question if necessary."
            },
            {
                "role": "user",
                "content": transcription
            }
        ]
    )
    return response.choices[0].message.content

def detect_exaggeration(transcription):
    response = client_chatbot.chat.completions.create(
        model="gpt-4",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "As an AI with expertise in language analysis and business, your task is to analyze the text and extract words that may contain exaggerated phrases about the product/service or an unreliable promise made to the client. Also, provide why this word may be an exaggeration or unreliable."
            },
            {
                "role": "user",
                "content": transcription
            }
        ]
    )
    return response.choices[0].message.content

def summarize(transcription): 
    response = client_chatbot.chat.completions.create(
        model="gpt-4",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "As an AI with expertise in language analysis, your task is to summarize the text. Include important business notes if the text contains business insights."
            },
            {
                "role": "user",
                "content": transcription
            }
        ]
    )
    return response.choices[0].message.content

# Configuration
REDIRECT_URI = "http://localhost:8501"
CLIENT_SECRETS_FILE = "clientSecrets.json"
SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "openid"
]

# Create a Flow instance
flow = Flow.from_client_secrets_file(
    CLIENT_SECRETS_FILE,
    scopes=SCOPES,
    redirect_uri=REDIRECT_URI
)
    
def save_user_data(user_data):
    with open("user_data.pkl", "wb") as f:
        pickle.dump(user_data, f)

def load_user_data():
    if os.path.exists("user_data.pkl"):
        with open("user_data.pkl", "rb") as f:
            return pickle.load(f)
    return None

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

def get_upcoming_meetings(credentials):
    service = build('calendar', 'v3', credentials=credentials)
    now = datetime.datetime.now().isoformat() + 'Z'
    events_result = service.events().list(
        calendarId='primary', timeMin=now,
        maxResults=10, singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])
    
    upcoming_meetings = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        upcoming_meetings.append({
            'title': event['summary'],
            'start': start,
            'end': end,
            'link': event.get('hangoutLink', '')
        })
    return upcoming_meetings

def meeting_minutes(transcription):
    abstract_summary = abstract_summary_extraction(transcription)
    key_points = key_points_extraction(transcription)
    action_items = action_item_extraction(transcription)
    sentiment = sentiment_analysis(transcription)
    return {
        'abstract_summary': abstract_summary,
        'key_points': key_points,
        'action_items': action_items,
        'sentiment': sentiment
    }

def abstract_summary_extraction(transcription):
    response = client_chatbot.chat.completions.create(
        model="gpt-4",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "You are a highly skilled AI trained in language comprehension and summarization. I would like you to read the following text and summarize it into a concise abstract paragraph. Aim to retain the most important points, providing a coherent and readable summary that could help a person understand the main points of the discussion without needing to read the entire text. Please avoid unnecessary details or tangential points."
            },
            {
                "role": "user",
                "content": transcription
            }
        ]
    )
    return response.choices[0].message.content


def key_points_extraction(transcription):
    response = client_chatbot.chat.completions.create(
        model="gpt-4",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "You are a proficient AI with a specialty in distilling information into key points. Based on the following text, identify and list the main points that were discussed or brought up. These should be the most important ideas, findings, or topics that are crucial to the essence of the discussion. Your goal is to provide a list that someone could read to quickly understand what was talked about."
            },
            {
                "role": "user",
                "content": transcription
            }
        ]
    )
    return response.choices[0].message.content


def action_item_extraction(transcription):
    response = client_chatbot.chat.completions.create(
        model="gpt-4",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "You are an AI expert in analyzing conversations and extracting action items. Please review the text and identify any tasks, assignments, or actions that were agreed upon or mentioned as needing to be done. These could be tasks assigned to specific individuals, or general actions that the group has decided to take. Please list these action items clearly and concisely."
            },
            {
                "role": "user",
                "content": transcription
            }
        ]
    )
    return response.choices[0].message.content

def sentiment_analysis(transcription):
    response = client_chatbot.chat.completions.create(
        model="gpt-4",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "As an AI with expertise in language and emotion analysis, your task is to analyze the sentiment of the following text. Please consider the overall tone of the discussion, the emotion conveyed by the language used, and the context in which words and phrases are used. Indicate whether the sentiment is generally positive, negative, or neutral, and provide brief explanations for your analysis where possible."
            },
            {
                "role": "user",
                "content": transcription
            }
        ]
    )
    return response.choices[0].message.content

def init_session_state():
    if "google_auth_code" not in st.session_state:
        st.session_state["google_auth_code"] = None
    if "user_info" not in st.session_state:
        st.session_state["user_info"] = None
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'filename' not in st.session_state:
        st.session_state.filename = ""
    if 'edit_mode' not in st.session_state:
        st.session_state.edit_mode = False

def format_datetime(dt_string):
    dt = datetime.datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
    return dt.strftime("%A, %B %d, %Y at %I:%M %p")

def home():
    init_session_state()

    # Define a stop event
    stop_recording_event = threading.Event()

    st.set_page_config(layout="wide")

    st.markdown('<style>' + open('./style.css').read() + '</style>', unsafe_allow_html=True)

    with st.sidebar:
        client_names = list(client_data.keys())
        option = st.selectbox(
            "Select client",
            client_names
        )
        tabs = on_hover_tabs(tabName=['Dashboard', 'Meetings', 'Business', 'Profile', 'Logout'], 
                            iconName=['dashboard', 'phone', 'lightbulb', 'person', 'logout'], default_choice=0)

    if tabs == 'Dashboard':
        industryName = client_data[option]["Industry"]
        clientEmail = client_data[option]["Email"]
        user_data = load_user_data()
        credentials_dict = json.loads(user_data['credentials'])
        credentials = Credentials.from_authorized_user_info(info=credentials_dict)
        # credentials = st.session_state.get("credentials")
        userEmail = user_data.get('email')
        showClientDashboard(option, clientEmail, industryName, "vs_G0ichcYATIwdL2x2TWYnBtm7", credentials, userEmail)

    elif tabs == 'Meetings':
        st.title("Client Meetings")
        #meeting_tabs = st.tabs(["Upcoming Meetings", "Smart Meeting Assistant", "Meeting Minutes"])
        selected = option_menu(
            menu_title=None, 
            options=["Upcoming Meetings", "Smart Call Assistant", "Meeting Minutes"],
            orientation="horizontal",
        )
        if selected == "Upcoming Meetings": 
            user_data = load_user_data()
            if user_data and 'credentials' in user_data:
                credentials_dict = json.loads(user_data['credentials'])
                credentials = Credentials.from_authorized_user_info(info=credentials_dict)
                events = get_upcoming_meetings(credentials)
            else:
                events = []

            col1, col2 = st.columns([3, 1])

            with col1:
                calendar_options = {
                    "headerToolbar": {
                        "left": "prev,next today",
                        "center": "title",
                        "right": "dayGridMonth,timeGridWeek,timeGridDay",
                    },
                    "initialView": "dayGridMonth",
                    "selectable": True,
                    "events": events,
                    "height": "500px",
                }

                selected_date = calendar(events=events, options=calendar_options)

            with col2:
                if not user_data or 'credentials' not in user_data:
                    if st.button("Connect to Google Calendar"):
                        authorization_url, _ = flow.authorization_url(prompt="consent")
                        st.markdown(f'<a href="{authorization_url}" target="_self">Click here to connect</a>', unsafe_allow_html=True)
                
                st.subheader("Today's Events")
                today = datetime.datetime.now().date()
                today_events = [event for event in events if datetime.datetime.fromisoformat(event['start'].rstrip('Z')).date() == today]
                
                for event in today_events:
                    modal = Modal(f"{event['title']}", key=f"modal-{event['title']}")
                    open_modal = st.button(event['title'])
                    if open_modal:
                        modal.open()

                    if modal.is_open():
                        with modal.container():
                            st.markdown("#### 🕒 Meeting Info")
                            if event['link']:
                                st.markdown(f"[Join Now]({event['link']})")
                            start = format_datetime(event['start'])
                            end = format_datetime(event['end'])
                            st.markdown(f"Start: {start}")
                            st.markdown(f"End: {end}")

        if selected == "Smart Call Assistant":
            # Get today's meetings
            user_data = load_user_data()
            today_events = []
            if user_data and 'credentials' in user_data:
                credentials_dict = json.loads(user_data['credentials'])
                credentials = Credentials.from_authorized_user_info(info=credentials_dict)
                events = get_upcoming_meetings(credentials)
                today = datetime.datetime.now().date()
                today_events = [event for event in events if datetime.datetime.fromisoformat(event['start'].rstrip('Z')).date() == today]

            # Dropdown to select the meeting
            selected_meeting = st.selectbox(
                "Select current meeting and record call. Stop recording when the call is finished.",
                options=[f"{event['title']} - {format_datetime(event['start'])}" for event in today_events],
                format_func=lambda x: x.split(" - ")[0]
            )

            speech_client = speech.SpeechClient(credentials=speech_credentials)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=SAMPLE_RATE,
                language_code="en-US",
                max_alternatives=1,
            )
            streaming_config = speech.StreamingRecognitionConfig(
                config=config, interim_results=True
            )

            mic_index = 0
            spkr_index = 2 

            # columns for start and stop buttons
            col1, col2 = st.columns([1,1])

            transcription = ""
            filename = ""
            # start button
            if col1.button("Start Recording", key="start_button"):
                stop_recording_event.clear()
                meeting_name = selected_meeting.split(" - ")[0]
                filename = f"{meeting_name}_transcript.txt"
                st.session_state.filename = filename
                threading.Thread(target=record_audio, args=(speech_client, streaming_config, mic_index, spkr_index, filename), daemon=True).start()

            # stop button
            if col2.button("Meeting Done", key="stop_button"):
                stop_recording_event.set()
                st.success("Recording stopped and transcript saved.")

            # Display chat messages from history on app rerun
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # Accept user input
            if prompt := st.chat_input("Type 'summary' for a debrief, 'false' to detect false claims, or 'response' for recommended follow-ups"):
                # Add user message to chat history
                st.session_state.messages.append({"role": "user", "content": prompt})
                
                # Display user message in chat message container
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                # Generate and display assistant response
                response = ""
                # get content from the transcript 
                if st.session_state.filename:
                    transcription = read_text_file(st.session_state.filename)
                with st.chat_message("assistant"):
                    with st.spinner("Generating..."):
                        if prompt.lower() == "false":
                            response = detect_exaggeration(transcription)
                        elif prompt.lower() == "summary":
                            response = summarize(transcription)
                        elif prompt.lower() == "response":
                            response = generate_response(transcription)
                        st.markdown(response)
                
                # Add assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": response})

        if selected == "Meeting Minutes":

            transcript_files = [f for f in os.listdir() if f.endswith(".txt")]
            
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Previous Meetings")
                # Dropdown to select the meeting
                selected_meeting = st.selectbox("Select a meeting", transcript_files)

                if st.button("Get Report"):
                    with st.spinner("Generating..."):
                        # Read the selected transcript file
                        with open(selected_meeting, "r") as file:
                            transcription = file.read()
                        
                        # Generate meeting minutes
                        minutes = meeting_minutes(transcription)

                        # Save the generated minutes to session state
                        st.session_state.generated_minutes = minutes

            with col2:
                if 'generated_minutes' in st.session_state:
                    st.subheader("Report")

                    for key, value in st.session_state.generated_minutes.items():
                        with st.expander(key.replace('_', ' ').title()):
                            st.write(value)


    elif tabs == 'Business':
        st.title("Business Intelligence")

        # Create tabs for different BI perspectives
        bi_tabs = st.tabs(["Manager's Insights", "Team Performance", "Sales Analysis", "Personal Sales Process"])

        with bi_tabs[0]:
            st.header("Advertising Sales Manager")
            # Example KPIs for boss's perspective
            col1, col2, col3 = st.columns(3)
            col1.metric("Revenue", "$1.2M", "+8%")
            col2.metric("Profit Margin", "22%", "+2%")
            col3.metric("Customer Acquisition Cost", "$50", "-10%")

            # Example chart
            st.subheader("Revenue Trend")
            chart_data = pd.DataFrame(
                np.random.randn(20, 3),
                columns=['Revenue', 'Costs', 'Profit'])
            st.line_chart(chart_data)

        with bi_tabs[1]:
            st.header("Team Performance")

            # Team performance metrics
            st.subheader("Team KPIs")
            team_data = pd.DataFrame({
                'Team Member': ['Alice', 'Bob', 'Charlie', 'David'],
                'Sales': [100000, 85000, 92000, 78000],
                'Deals Closed': [15, 12, 14, 10],
                'Customer Satisfaction': [4.8, 4.6, 4.7, 4.5],
                'Conversion Rate': [0.25, 0.22, 0.24, 0.20],
                'Average Deal Size': [6667, 7083, 6571, 7800]
            })

            st.table(team_data)

            # Team performance charts
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Sales Performance by Team Member")
                fig = px.bar(team_data, x='Team Member', y='Sales', text='Sales')
                fig.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
                fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("Deals Closed vs Customer Satisfaction")
                fig = px.scatter(team_data, x='Deals Closed', y='Customer Satisfaction', color='Team Member', hover_name='Team Member')
                st.plotly_chart(fig, use_container_width=True)

        with bi_tabs[2]:
            st.header("Sales Analysis")
            col1, col2 = st.columns([3,2])

            with col1:
                st.subheader("Sales Funnel")
                # Sales funnel
                funnel_data = pd.DataFrame({
                    'Stage': ['Leads', 'Qualified Leads', 'Proposals', 'Negotiations', 'Closed Deals'],
                    'Count': [1000, 500, 200, 100, 50]
                })
                fig = go.Figure(go.Funnelarea(
                    values = funnel_data['Count'],
                    text = funnel_data['Stage'],
                    #textinfo = "value+percent total"
                ))
                # Customize the layout
                fig.update_layout(
                    font_size = 14,
                    height = 300,
                    margin=dict(t=0, b=0, l=0, r=0) 
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("Sales Trend")
                dates = pd.date_range(start='1/1/2024', end='7/1/2024', freq='ME')
                sales_trend = pd.DataFrame({
                    'Date': dates,
                    'Sales': np.random.randint(50000, 100000, size=len(dates))
                })
                sales_trend.set_index('Date', inplace=True)
                st.line_chart(sales_trend)

        with bi_tabs[3]:
            st.header("Personal Sales Process Analysis")
            # Personal sales metrics
            st.subheader("Your Sales Metrics")
            col1, col2, col3 = st.columns(3)
            col1.metric("Your Sales", "$120K", "+5%")
            col2.metric("Conversion Rate", "18%", "+2%")
            col3.metric("Average Deal Size", "$8K", "+1%")

            # Sales activity breakdown
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Activities Breakdown")
                activities = pd.DataFrame({
                    'Activity': ['Calls', 'Emails', 'Meetings', 'Proposals'],
                    'Hours Spent': [20, 15, 10, 5]
                })
                fig = go.Figure(data=[go.Pie(labels=activities['Activity'], values=activities['Hours Spent'])])
                fig.update_layout(title_text='Sales Activities Breakdown', 
                                margin=dict(t=40, b=0, l=0, r=0),
                                height = 300,  
                                width = 500)
                st.plotly_chart(fig)

            with col2:
                # Areas for improvement
                st.subheader("Areas for Improvement")
                improvements = [
                    "Increase follow-up frequency",
                    "Improve product knowledge",
                    "Enhance negotiation skills"
                ]

                for item in improvements:
                    st.info(item)
    elif tabs == 'Profile':
        st.title("TikTok Smart Sales Profile")
        user_data = load_user_data()

        # Initialize session state for profile data if not exists
        if 'profile_data' not in st.session_state:
            st.session_state.profile_data = {
                'name': user_data.get('name', "John Doe") if user_data else "John Doe",
                'email': user_data.get('email', "john.doe@example.com") if user_data else "john.doe@example.com",
                'role': "Senior Sales Representative",
                'phone': "+1 (555) 123-4567",
                'team': "Enterprise Sales Team",
                'reports_to': "Sarah Johnson, Sales Director",
                'bio': "Experienced sales professional with a track record of exceeding targets in the enterprise software sector. Specializes in building long-term client relationships and delivering tailored solutions."
            }

        # Create two columns for layout
        col1, col2 = st.columns([1, 3])

        with col1:
            # profile picture placeholder
            st.image("https://i.pinimg.com/originals/54/8a/65/548a659c2b06a877516d3c998f5b0939.png", width=200)
            # Edit profile button
            if st.button("Edit Profile"):
                st.session_state.edit_mode = not st.session_state.get('edit_mode', False)

        with col2:
            if st.session_state.get('edit_mode', False):
                # Editable fields
                st.session_state.profile_data['name'] = st.text_input("Name", st.session_state.profile_data['name'])
                st.session_state.profile_data['role'] = st.text_input("Role", st.session_state.profile_data['role'])
                st.session_state.profile_data['email'] = st.text_input("Email", st.session_state.profile_data['email'])
                st.session_state.profile_data['phone'] = st.text_input("Phone", st.session_state.profile_data['phone'])
                st.session_state.profile_data['team'] = st.text_input("Team", st.session_state.profile_data['team'])
                st.session_state.profile_data['reports_to'] = st.text_input("Reports to", st.session_state.profile_data['reports_to'])
                st.session_state.profile_data['bio'] = st.text_area("Bio", st.session_state.profile_data['bio'])
                
                if st.button("Save Changes"):
                    st.session_state.edit_mode = False
                    st.success("Profile updated successfully!")
                    st.experimental_rerun()
            else:
                # Display profile information
                st.header(st.session_state.profile_data['name'])
                st.markdown(f"### *{st.session_state.profile_data['role']}*")
                
                st.markdown("---")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Email:** {st.session_state.profile_data['email']}")
                    st.markdown(f"**Phone:** {st.session_state.profile_data['phone']}")
                with col2:
                    st.markdown(f"**Team:** {st.session_state.profile_data['team']}")
                    st.markdown(f"**Reports to:** {st.session_state.profile_data['reports_to']}")
                
                st.markdown("---")
                
                st.subheader("Bio")
                st.write(st.session_state.profile_data['bio'])