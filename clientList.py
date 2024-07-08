import streamlit as st
import pandas as pd
from login import auth_flow
from clientDashboard import showClientDashboard
import json

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

def show_client_list(main_container):
    main_container.empty()
    with main_container:
        st.title("TikTok Ad Clients Dashboard")

        for client_name, client_info in client_data.items():
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

                with col1:
                    if st.button(client_name, key=f"button_{client_name}", help="Click to view client dashboard"):
                        st.session_state.selected_client = client_name
                        st.session_state.current_page = "client_dashboard"
                        st.rerun()
                    st.markdown(f"<div class='industry'>{client_info['Industry']}</div>", unsafe_allow_html=True)

                with col2:
                    st.markdown(f"<span class='status status-{client_info['Status']}'>{client_info['Status']}</span>", unsafe_allow_html=True)

                with col3:
                    st.write(client_info['Point of Contact'])

                with col4:
                    st.write(client_info['Email'])

                st.markdown("<hr style='border:1px solid #333333; margin: 20px 0;'>", unsafe_allow_html=True)

        


def main():
    # Check if user is authenticated (replace with your authentication logic)
    if "google_auth_code" not in st.session_state:
        auth_flow()

    if "google_auth_code" in st.session_state:
        # Set page configuration after authentication
        st.set_page_config(layout="wide", page_title="TikTok Ad Clients Dashboard")

        # Custom CSS with correct TikTok colors
        st.markdown("""
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                background-color: #000000;
                color: #ffffff;
            }
            .stApp {
                max-width: 100%;
            }
            h1 {
                color: #ff0050;
                text-align: center;
                font-size: 3em;
                margin-bottom: 30px;
            }
            .client-button {
                background-color: #ff0050;
                border: none;
                color: #00f2ea;
                font-weight: bold;
                cursor: pointer;
                padding: 0;
                text-align: left;
                font-size: 16px;
            }
            .client-button:hover {
                color: #ff0050;
            }
            .industry {
                color: #888888;
                font-size: 12px;
            }
            .status {
                padding: 3px 8px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: bold;
            }
            .status-Active {
                background-color: #00f2ea;
                color: #000000;
            }
            .status-Pending {
                background-color: #ff0050;
                color: #ffffff;
            }
            .status-Negotiating {
                background-color: #ffffff;
                color: #000000;
            }
            .dataframe {
                background-color: #121212;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
            }
            .stMarkdown {
                color: #ffffff;
            }
        </style>
        """, unsafe_allow_html=True)

        # Initialize session state for current page
        if "current_page" not in st.session_state:
            st.session_state.current_page = "client_list"

        # Create a container for the entire content
        main_container = st.container()

        # Display the appropriate page
        
        if st.session_state.current_page == "client_list":
            show_client_list(main_container)


        if st.session_state.current_page == "client_dashboard":
            clientName = st.session_state.get('selected_client')
            industryName = client_data[clientName]["Industry"]
            clientEmail = client_data[clientName]["Email"]
            credentials = st.session_state.get("credentials")
            userEmail = st.session_state.get("user_info")
            main_container.empty()
            showClientDashboard(main_container, clientName, clientEmail, industryName, "vs_G0ichcYATIwdL2x2TWYnBtm7", credentials, userEmail)
            
if __name__ == "__main__":
    main()
