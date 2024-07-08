import streamlit as st
from dotenv import load_dotenv
import openai
import time
from clientDashboardFunctions import generateSentimentAnalysis, generateTasks, summarize_email
import plotly.graph_objects as go
from gmail_utils import search_emails
import os 
from streamlit_option_menu import option_menu


# Load environment variables and initialize OpenAI client
# @st.cache_resource
# def initialize_resources():
#     load_dotenv()
#     return openai.OpenAI(api_key=os.getenv("OPEN_API_KEY_CLIENT_DASHBOARD"))

client = openai.OpenAI(api_key=os.getenv("OPEN_API_KEY_CLIENT_DASHBOARD"))

@st.cache_data
def upload_to_openai(filepath):
    with open(filepath, "rb") as file:
        response = client.files.create(file=file, purpose="assistants")
    return response.id

def handle_chat_input(prompt, chat_container, client, assistant_id):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with chat_container:
        with st.chat_message("user"):
            st.markdown(prompt)

    client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=prompt
    )

    run = client.beta.threads.runs.create(
        thread_id=st.session_state.thread_id,
        assistant_id=assistant_id,
        instructions="Please answer the questions using the knowledge provided in the files. When adding additional information, make sure to distinguish it with bold or underlined text."
    )

    with chat_container:
        with st.spinner("Generating response..."):
            while run.status != "completed":
                time.sleep(1)
                run = client.beta.threads.runs.retrieve(
                    thread_id=st.session_state.thread_id, run_id=run.id
                )

            messages = client.beta.threads.messages.list(thread_id=st.session_state.thread_id)
            assistant_messages_for_run = [
                message for message in messages
                if message.run_id == run.id and message.role == "assistant"
            ]

        for message in assistant_messages_for_run:
            full_response = message.content[0].text.value
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            with st.chat_message("assistant"):
                st.markdown(full_response, unsafe_allow_html=True)

def handle_file_upload(vector_store_id, file_uploaded):
    if file_uploaded:
        with open(f"{file_uploaded.name}", "wb") as f:
            f.write(file_uploaded.getbuffer())
        another_file_id = upload_to_openai(f"{file_uploaded.name}")
        if "file_id_list" not in st.session_state:
            st.session_state.file_id_list = []
        st.session_state.file_id_list.append(another_file_id)
        if st.session_state.file_id_list:
            for file_id in st.session_state.file_id_list:
                # add file id to vector store
                file = client.beta.vector_stores.files.create_and_poll(
                    vector_store_id=vector_store_id,
                    file_id=file_id
                )
        st.success(f"File {file_uploaded.name} uploaded successfully!")

@st.cache_data(show_spinner=False)
def get_client_data(vector_store_id):
    tasks = generateTasks(vector_store_id=vector_store_id)
    scoreDict = generateSentimentAnalysis(vector_store_id=vector_store_id)
    return tasks, scoreDict

def showClientDashboard(clientName, clientEmail, industryName, vector_store_id, credentials, userEmail):
    st.title(f"{clientName} | {industryName}")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "thread_id" not in st.session_state:
        chat_thread = client.beta.threads.create()
        st.session_state.thread_id = chat_thread.id

    selected = option_menu(
        menu_title=None, 
        options=["Client Overview", "Email Summaries", "Client Information Assistant"],
        orientation="horizontal"
    )
    
    if selected == "Client Overview":
        st.spinner("Loading...")
        tasks, scoreDict = get_client_data(vector_store_id)
        with st.container():
            st.subheader("Client Information")
            st.write(f"Client Name: {clientName}")
            st.write(f"Client Email: {clientEmail}")

        col1, col2 = st.columns(2)  # Create two columns of equal width

        with col1:
            st.subheader("Action Items")
            for i, task in enumerate(tasks, 1):
                st.markdown(f"{i}. {task}")

        with col2:
            scoreDict = generateSentimentAnalysis(vector_store_id=vector_store_id)
            score = 0
            key=""
            for score in scoreDict:
                key=score
                score = round(float(score),2)

            fig = go.Figure()
            fig.add_trace(go.Pie(
                values=[score, 100 - score],
                hole=0.7,
                marker_colors=['#00f2ea', 'lightgrey'],
                direction='clockwise',
                sort=False,
                textinfo='none',
                showlegend=False
            ))
            fig.update_layout(
                title='Sentiment Analysis',
                title_x=0.4,
                annotations=[{
                    "font": {"size": 20, "color": "#00f2ea"},
                    "showarrow": False,
                    "text": f"{score}%",
                    "x": 0.5,
                    "y": 0.5
                }],
                height=200,
                margin=dict(l=0, r=0, t=40, b=0)
            )
            st.plotly_chart(fig)

        with st.form(key='file_upload_form'):
            file_uploaded = st.file_uploader(
                "Upload additional documents containing client information",
                key="file_upload"
            )
            submit_button = st.form_submit_button(label='Upload')

        if submit_button and file_uploaded:
            handle_file_upload(vector_store_id, file_uploaded)
    if selected == "Email Summaries":
        st.header("Email Summaries")
        if credentials:
            specific_email = clientEmail
            user_email = userEmail
            query = f'(from:"{user_email}" to:"{specific_email}") OR (from:"{specific_email}" to:"{user_email}")'
            emails = search_emails(credentials, query)
            for email in emails:
                summary = summarize_email(email['body'])
                with st.expander(f"Subject: {email['subject']}, Date: {email['date']}"):
                    st.write("Body:")
                    st.write(summary)
    if selected == "Client Information Assistant":
        st.subheader("Chat Assistant")
        chat_container = st.container()
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"], unsafe_allow_html=True)

        if prompt := st.chat_input("Ask any questions you have about your client"):
            handle_chat_input(prompt, chat_container, client, "asst_HI5jDraznUXvlLmfmjqTmh8l")