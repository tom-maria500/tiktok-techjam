from openai import OpenAI
import os 
import dotenv 

dotenv.load_dotenv()
client= OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def transcribe_audio(audio_file_path):
    audio_file = open(audio_file_path, "rb")
    transcript = client.audio.transcriptions.create(
        model="whisper-1", 
        file=audio_file
    )
    return transcript.text

def read_text_file(text_file_path):
    with open(text_file_path, "r") as file:
        text_content = file.read()
    return text_content

def detect_exaggeration(transcription):
    response = client.chat.completions.create(
        model="gpt-4",
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "As an AI with expertise in language analysis and business, your task is to analyze the text and extract words that may contain exaggerated phrases about the product/service or an unrelaible promise made to the client. Also, provide why this word may be an exxageration or unreliable."
            },
            {
                "role": "user",
                "content": transcription
            }
        ]
    )
    return response.choices[0].message.content


audio_file_path = "audio_sample.mp3"
text_file_path = "transcript.txt"
transcription = read_text_file(text_file_path)
flagged_words = detect_exaggeration(transcription)
print(flagged_words)