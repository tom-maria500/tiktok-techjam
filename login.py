import os
import streamlit as st
import webbrowser
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

redirect_uri = "http://localhost:8501"
client_secrets_file = "clientSecrets.json"

def init_session_state():
    if "google_auth_code" not in st.session_state:
        st.session_state["google_auth_code"] = None
    if "user_info" not in st.session_state:
        st.session_state["user_info"] = None

init_session_state()

def auth_flow():
    st.set_page_config(layout="wide", page_title="TikTok CRM")

    # Custom CSS
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

    # Sidebar
    st.markdown('<div class="sidebar">', unsafe_allow_html=True)
    st.markdown("<h2 class='login-text'>Sidebar</h2>", unsafe_allow_html=True)
    # Add any sidebar content here
    st.markdown('</div>', unsafe_allow_html=True)

    # Main content
     # Main content
    with col2:
        st.markdown('<div class="content">', unsafe_allow_html=True)
        st.markdown("<h1 class='login-text'>Welcome to TikTok CRM</h1>", unsafe_allow_html=True)
        st.markdown("<p class='login-text'>Sign in with Google to see the latest updates.</p>", unsafe_allow_html=True)

        # Check if we're in the callback

        auth_code = st.query_params.get("code")
        flow = Flow.from_client_secrets_file(
            "clientSecrets.json",
            scopes=["https://www.googleapis.com/auth/userinfo.email", "openid"],
            redirect_uri=redirect_uri,
        )
        if auth_code:
            flow.fetch_token(code=auth_code)
            credentials = flow.credentials
            st.write("Login Done")
            user_info_service = build(
                serviceName="oauth2",
                version="v2",
                credentials=credentials,
            )
            user_info = user_info_service.userinfo().get().execute()
            assert user_info.get("email"), "Email not found in infos"
            st.session_state["google_auth_code"] = auth_code
            st.session_state["user_info"] = user_info
        elif st.session_state["google_auth_code"] is None:
            if st.button("Sign in with Google"):
                authorization_url, state = flow.authorization_url(
                    access_type="offline",
                    include_granted_scopes="true",
                )
                webbrowser.open_new_tab(authorization_url)
        else:
            st.write(f"Welcome back, {st.session_state['user_info'].get('email')}")

            
            st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    auth_flow()