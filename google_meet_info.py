import streamlit as st
import os
import pickle
import json
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from datetime import datetime

# Configuration
REDIRECT_URI = "http://localhost:8501"
CLIENT_SECRETS_FILE = "clientSecrets.json"
SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/calendar.readonly",
    "openid"
]

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
    now = datetime.utcnow().isoformat() + 'Z'
    events_result = service.events().list(
        calendarId='primary', timeMin=now,
        maxResults=10, singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])
    
    upcoming_meetings = []
    for event in events:
        if 'hangoutLink' in event:
            start = event['start'].get('dateTime', event['start'].get('date'))
            upcoming_meetings.append({
                'summary': event['summary'],
                'start': start,
                'link': event['hangoutLink']
            })
    return upcoming_meetings

def login_page():
    st.title("Google Login")
    
    if st.button("Login with Google"):
        authorization_url, _ = flow.authorization_url(prompt="consent")
        st.markdown(f'<a href="{authorization_url}" target="_self">Click here to login</a>', unsafe_allow_html=True)

def homepage():
    st.title("Welcome to the Homepage")
    user_data = load_user_data()
    if user_data:
        st.write(f"Welcome, {user_data['name']}!")
        st.write(f"Email: {user_data['email']}")
        
        credentials_dict = json.loads(user_data['credentials'])
        credentials = Credentials.from_authorized_user_info(info=credentials_dict)
        
        upcoming_meetings = get_upcoming_meetings(credentials)
        
        if upcoming_meetings:
            st.subheader("Your Upcoming Meetings")
            for meeting in upcoming_meetings:
                meeting_time = datetime.fromisoformat(meeting['start'].rstrip('Z'))
                st.write(f"{meeting['summary']} - {meeting_time.strftime('%Y-%m-%d %H:%M')}")
                if st.button(f"Join {meeting['summary']}"):
                    st.markdown(f'<a href="{meeting["link"]}" target="_blank">Click here to join the meeting</a>', unsafe_allow_html=True)
        else:
            st.info("You have no upcoming meetings.")
        
        if st.button("Logout"):
            os.remove("user_data.pkl")
            st.experimental_rerun()
    else:
        st.warning("You are not logged in. Please go back to the login page.")

def main():
    if "page" not in st.session_state:
        st.session_state.page = "login"

    if st.session_state.page == "login":
        login_page()
        
        # Check if the OAuth flow has completed
        if "code" in st.experimental_get_query_params():
            with st.spinner("Authenticating..."):
                try:
                    code = st.experimental_get_query_params()["code"][0]
                    flow.fetch_token(code=code)
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
        homepage()

if __name__ == "__main__":
    main()