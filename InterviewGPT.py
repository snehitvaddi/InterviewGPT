import pickle
from pathlib import Path
import websockets
import base64
import asyncio
import json
from groq import AsyncGroq, Groq
import pyaudio
# from openai import OpenAI
import pandas as pd  # pip install pandas openpyxl
import plotly.express as px  # pip install plotly-express
import streamlit as st  # pip install streamlit
import streamlit_authenticator as stauth  # pip install streamlit-authenticator
import spacy
from collections import deque

# emojis: https://www.webfx.com/tools/emoji-cheat-sheet/
st.set_page_config(page_title="IntervewGPT", page_icon=":brain:", layout="wide")


# --- USER AUTHENTICATION ---
names = ["snehit", "vaddi"]
usernames = ["snehit", "vaddi"]

# load hashed passwords
file_path = Path(__file__).parent / "hashed_pw.pkl"
with file_path.open("rb") as file:
    hashed_passwords = pickle.load(file)

authenticator = stauth.Authenticate(
    names,
    usernames,
    hashed_passwords,
    "sales_dashboard",
    "abcdef",
    cookie_expiry_days=30,
)

name, authentication_status, username = authenticator.login("Login", "main")

if authentication_status == False:
    st.error("Username/password is incorrect")

if authentication_status == None:
    st.warning("Please enter your username and password")

if authentication_status:

    # ---- SIDEBAR ----
    authenticator.logout("Logout", "sidebar")
    st.sidebar.title(f"Welcome {name.upper()}")

    # ---- MAINPAGE ----
    st.title(":brain: InterviewGPT")
    st.markdown("##")

    # # openai api_key
    # client = OpenAI(
    # api_key="OPEN_AI_API",
    # )

    # Groq API
    client = AsyncGroq(
    api_key="GROQ_API",
)
    # AssemblyAI API key
    auth_key = "ASSEMBLY_AI_API"

    if "text" not in st.session_state:
        st.session_state["text"] = "Listening..."
        st.session_state["run"] = False

    FRAMES_PER_BUFFER = 8000
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    p = pyaudio.PyAudio()

    # starts recording
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=FRAMES_PER_BUFFER,
    )

    conversation_history = deque(maxlen=5)
    transcript = []  # Global transcript

    def start_listening():
        st.session_state["run"] = True

    def stop_listening():
        with open("conversation.txt", "w") as file:
            file.write("\n".join(transcript))
        st.session_state["run"] = False

    def apply_differential_privacy():
        # Load spaCy model for NER
        nlp = spacy.load("en_core_web_sm")

        with open("conversation.txt", "r") as file:
            lines = file.readlines()

        # Consider only lines starting with "User:"
        user_lines = [
            line[len("User:") :].strip() for line in lines if line.startswith("User:")
        ]
        user_text = "\n".join(user_lines)

        # Apply NER and redact sensitive information
        doc = nlp(user_text)
        for ent in doc.ents:
            if ent.label_ in ["PERSON", "ORG", "GPE", "DATE", "PHONE"]:
                # Redact sensitive information
                user_text = user_text.replace(ent.text, "[REDACTED]")

        # Write the redacted user text to a new file
        with open("conversation_redacted.txt", "w") as file:
            file.write(user_text)

    start, stop = st.columns(2)
    start.button("Start listening", on_click=start_listening)

    stop.button(
        "Stop listening",
        on_click=lambda: [stop_listening(), apply_differential_privacy()],
    )

    URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"

    async def send_receive():

        print(f"Connecting websocket to url ${URL}")

        async with websockets.connect(
            URL,
            extra_headers=(("Authorization", auth_key),),
            ping_interval=5,
            ping_timeout=20,
        ) as _ws:

            r = await asyncio.sleep(0.1)
            print("Receiving SessionBegins ...")

            session_begins = await _ws.recv()
            print(session_begins)
            print("Sending messages ...")

            async def send():
                while st.session_state["run"]:
                    try:
                        data = stream.read(FRAMES_PER_BUFFER)
                        data = base64.b64encode(data).decode("utf-8")

                        json_data = json.dumps({"audio_data": str(data)})
                        r = await _ws.send(json_data)

                    except websockets.exceptions.ConnectionClosedError as e:
                        print(e)
                        assert e.code == 4008
                        break

                    except Exception as e:
                        print(e)
                        assert False, "Not a websocket 4008 error"

                    r = await asyncio.sleep(0.01)

            async def receive():
                
                while st.session_state["run"]:
                    try:
                        result_str = await _ws.recv()
                        result_json = json.loads(result_str)
                        result = result_json.get("text", "")
                        if result_json.get("message_type") == "FinalTranscript":
                            print(result)

                            st.session_state["text"] = f"<span style='color: orange;'>User:</span> {result}"
                            st.markdown(st.session_state["text"], unsafe_allow_html=True)
                            transcript.append(f"User: {result}")  # Global Transcript
                            conversation_history.append({"role": "user", "content": result})

                            if result:
                                # Prepare messages including the full conversation history
                                messages = [
                                        {"role": "system", "content": "You are a helpful assistant."}
                                    ] + list(conversation_history)  

                                chat_completion = await client.chat.completions.create(
                                    messages=messages,
                                    model="llama3-8b-8192",
                                    temperature=0.5,
                                    max_tokens=300,
                                    stream=False
                                )
                                reply = chat_completion.choices[0].message.content
                                print(f"InterviewGPT: {reply}")
                                conversation_history.append({"role": "assistant", "content": reply})
                                transcript.append(f"InterviewGPT: {reply}")  # Global Transcript

                                st.session_state["chatText"] = f"<span style='color: green;'>InterviewGPT:</span> {reply}"
                                st.markdown(st.session_state["chatText"], unsafe_allow_html=True)

                    except websockets.exceptions.ConnectionClosedError as e:
                        print(f"WebSocket connection closed: {e}")
                        if e.code != 4008:
                            print("Received unexpected error code from WebSocket.")
                        break

                    except Exception as e:
                        print(f"An unexpected error occurred: {e}")


            send_result, receive_result = await asyncio.gather(send(), receive())

    asyncio.run(send_receive())
