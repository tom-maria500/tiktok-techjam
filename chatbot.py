import streamlit as st
from openai import OpenAI
import os 
import dotenv 

# Load environment variables
dotenv.load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def read_text_file(text_file_path):
    with open(text_file_path, "r") as file:
        text_content = file.read()
    return text_content

def generate_response(transcription):
    response = client.chat.completions.create(
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
    response = client.chat.completions.create(
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
    response = client.chat.completions.create(
        model="gpt-4",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "As an AI with expertise in language analysis and business, your task is to summarize the call so far from a business perspective."
            },
            {
                "role": "user",
                "content": transcription
            }
        ]
    )
    return response.choices[0].message.content

# Read the transcript once at the start
text_file_path = "transcript.txt"
transcription = read_text_file(text_file_path)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("Type 'summary', 'false' to detect false claims, or 'response' for recommended follow-ups"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Generate and display assistant response
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

# Display the transcript content (optional)
st.sidebar.title("Transcript Content")
st.sidebar.text_area("Transcript", transcription, height=300)
