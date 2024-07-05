# Upcoming Meetings Page 

from st_on_hover_tabs import on_hover_tabs
import streamlit as st
from streamlit_option_menu import option_menu

import google_auth_oauthlib.flow
from googleapiclient.discovery import build
import webbrowser

from streamlit_calendar import calendar
import datetime
from streamlit_modal import Modal

redirect_uri = "http://localhost:8501"

def init_session_state():
    if "google_auth_code" not in st.session_state:
        st.session_state["google_auth_code"] = None
    if "user_info" not in st.session_state:
        st.session_state["user_info"] = None

st.set_page_config(layout="wide")

init_session_state()

#st.title("TikTok CRM")
st.markdown('<style>' + open('./style.css').read() + '</style>', unsafe_allow_html=True)


with st.sidebar:
    tabs = on_hover_tabs(tabName=['Dashboard', 'Mail', 'Meetings', 'Business'], 
                         iconName=['dashboard', 'mail', 'phone', 'lightbulb'], default_choice=0)

if tabs == 'Dashboard':
    st.title("TikTok CRM")

elif tabs == 'Mail':
    st.title("Client Interactions")

elif tabs == 'Meetings':
    st.title("Client Meetings")
    selected = option_menu(
        menu_title=None, 
        options=["Upcoming Meetings", "Smart Call Assistant", "Meeting Minutes"],
        orientation="horizontal",
    )
    if selected == "Upcoming Meetings": 
        # Sample event data
        # change with access to google calendar 
        events = [
            {
                'title': 'Meeting with Team',
                'start': '2024-07-05',
                'end': '2024-07-05'
            },
            {
                'title': 'Project Deadline',
                'start': '2024-07-15',
                'end': '2024-07-15'
            },
            # Add more events as needed
        ]
        # Create two columns
        col1, col2 = st.columns([3, 1])

        with col1:
            # Calendar configuration
            calendar_options = {
                "headerToolbar": {
                    "left": "prev,next today",
                    "center": "title",
                    "right": "dayGridMonth,timeGridWeek,timeGridDay",
                },
                "initialView": "dayGridMonth",
                "selectable": True,
                "events": events,
                "height": "600px",
            }

            # Display the calendar
            selected_date = calendar(events=events, options=calendar_options)

        with col2:
            st.button("Connect to Google Calendar")
            st.subheader("Today's Events")
            modal1 = Modal("Demo Modal", key="demo-modal")
            open_modal = st.button("Meeting with Team")
            if open_modal:
                modal1.open()

            if modal1.is_open():
                with modal1.container():
                    st.write("Text goes here")

    if selected == "Smart Call Assistant":
        url = st.text_input("Paste meeting URL to record")

        # Create a submit button
        if st.button("Join"):
            if url:
                st.success("URL submitted successfully!")
                # st.write("You submitted the following URL:")
                # st.write(url)
            else:
                st.error("Please enter a URL before submitting.")

elif tabs == 'Business':
    st.title("Business Intelligence")


def main():
    if st.session_state["google_auth_code"] is not None:
        email = st.session_state["user_info"].get("email")
        st.write(f"Hello {email}")


if __name__ == "__main__":
    main()