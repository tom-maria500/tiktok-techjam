import queue
import time
from google.cloud import speech
import pyaudio
from google.oauth2 import service_account
import streamlit as st
import uuid

client_file = 'service_account_info.json'
credentials = service_account.Credentials.from_service_account_file(client_file)

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

def listen_print_loop(responses, stream):
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

        formatted_transcript = "\n".join(full_transcript_with_interim if not result.is_final else full_transcript)
        transcript_container.text_area("Transcript", formatted_transcript, height=400, key=str(uuid.uuid4()))

        if result.is_final:
            with open("transcript.txt", "w") as f:
                for item in full_transcript:
                    f.write(f"{item}\n")

def record_audio(client, streaming_config, mic_index, spkr_index):
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
            listen_print_loop(responses, stream)

            if stream.result_end_time > 0:
                stream.final_request_end_time = stream.is_final_end_time
                stream.result_end_time = 0
                stream.last_audio_input = []
                stream.last_audio_input = stream.audio_input
                stream.audio_input = []
                stream.restart_counter = stream.restart_counter + 1
                stream.new_stream = True

def main():
    st.title("Real-time Speech-to-Text")
    st.write("Click 'Start' to begin recording and transcription. Click 'Stop' to end the session.")

    client = speech.SpeechClient(credentials=credentials)
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
    col1, col2 = st.columns(2)

    # start button
    if col1.button("Start Recording", key="start_button"):
        st.success("Recording started. Speak now...")
        record_audio(client, streaming_config, mic_index, spkr_index)

    # stop button
    if col2.button("Stop Recording", key="stop_button"):
        st.warning("Recording stopped.")

if __name__ == "__main__":
    main()