import streamlit as st 
import webbrowser

import datetime
import os
import pickle
import json
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
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
from app import home


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

def credentials_to_dict(credentials):
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

def login_page():
    st.markdown("""
    <style>
    .stApp {
        background-color: #000000;
        color: white;
    }
    .main {
        background-color: #000000;
    }
    .sidebar {
        background-color: #ff0050;  /* TikTok pink */
        padding: 2rem 1rem;
        height: 100vh;  /* Full height of the viewport */
        width: 350px;  /* Adjust width as needed */
        position: fixed;  /* Fixed position on the side */
        top: 0;  /* Align to the top */
        left: 0;  /* Align to the left */
        z-index: 1;  /* Ensure it's above other content */
    }
    .content {
        
        padding: 6rem 2rem;  /* Padding for top and bottom */
    }
    .login-text {
        text-align: left;
        color: white;
    }
    .stButton>button {
        width: 100%;
        background-color: #00f2ea;  /* TikTok aqua for button */
        color: black;
        font-weight: bold;
        border: none;
        padding: 0.75rem 1rem;
        border-radius: 5px;
        font-size: 16px;
        margin-top: 1rem;  /* Space above the button */
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1,2,1])

    # # Check for and clear any residual OAuth data
    # if 'credentials' in st.session_state:
    #     del st.session_state['credentials']
    
    # for key in list(st.session_state.keys()):
    #     if key.startswith('oauth2_'):
    #         del st.session_state[key]

    # Sidebar
    st.markdown('<div class="sidebar">', unsafe_allow_html=True)
    # Add any sidebar content here
    st.markdown('</div>', unsafe_allow_html=True)

    # Main content
    with col2:
        st.markdown('<div class="content">', unsafe_allow_html=True)
        st.markdown("<h1 class='login-text'>IntelliTok</h1>", unsafe_allow_html=True)
        st.markdown("<p class='login-text'>Sign in with Google to continue to IntelliTok.</p>", unsafe_allow_html=True)
        if st.button("Login with Google"):
            authorization_url, _ = flow.authorization_url(prompt="consent")
            webbrowser.open_new_tab(authorization_url)

def main():
    if "page" not in st.session_state:
        st.session_state.page = "login"

    if st.session_state.page == "login":
        login_page()
        auth_code = st.query_params.get("code")
        # Check if the OAuth flow has completed
        if auth_code:
            with st.spinner("Authenticating..."):
                try:
                    flow.fetch_token(code=auth_code)
                    credentials = flow.credentials
                    
                    user_info_service = build('oauth2', 'v2', credentials=credentials)
                    user_info = user_info_service.userinfo().get().execute()
                    
                    # Save user data and credentials as a JSON string
                    user_info['credentials'] = json.dumps(credentials_to_dict(credentials))
                    save_user_data(user_info)
                    
                    st.session_state.page = "homepage"
                    st.success("Authentication successful!")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")

    elif st.session_state.page == "homepage":
        home()

if __name__ == "__main__":
    main()