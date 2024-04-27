
import pickle
from pathlib import Path
import websockets
import asyncio
import base64
import json
import pyaudio
import openai
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

authenticator = stauth.Authenticate(names, usernames, hashed_passwords,
    "sales_dashboard", "abcdef", cookie_expiry_days=30)

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
    st.title(":brain: Contextual AI")
    st.markdown("##")

    # openai.api_key = st.text_input("Enter OpenAI API key")
    openai.api_key = "OPENAI_API"

    # auth_key = st.text_input("Enter AssemblyAI API key")
    auth_key = 'ASSEMBLY_AI_API'

    if 'text' not in st.session_state:
            st.session_state['text'] = 'Listening...'
            st.session_state['run'] = False

     
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
       frames_per_buffer=FRAMES_PER_BUFFER
    )

    conversation_history = deque(maxlen=5) 
    transcript = [] # Global transcript

    def start_listening():
            st.session_state['run'] = True

    def stop_listening():
            with open('conversation.txt', 'w') as file:
                file.write('\n'.join(transcript))
            st.session_state['run'] = False
        

    def apply_differential_privacy():
    # Load spaCy model for NER
        nlp = spacy.load("en_core_web_sm")

        with open('conversation.txt', 'r') as file:
            lines = file.readlines()

    # Consider only lines starting with "User:"
        user_lines = [line[len("User:"):].strip() for line in lines if line.startswith("User:")]
        user_text = "\n".join(user_lines)

    # Apply NER and redact sensitive information
        doc = nlp(user_text)
        for ent in doc.ents:
            if ent.label_ in ["PERSON", "ORG", "GPE", "DATE", "PHONE"]:
            # Redact sensitive information
                user_text = user_text.replace(ent.text, "[REDACTED]")

    # Write the redacted user text to a new file
        with open('conversation_redacted.txt', 'w') as file:
            file.write(user_text)


    start, stop = st.columns(2)
    start.button('Start listening', on_click=start_listening)

    stop.button('Stop listening', on_click=lambda: [stop_listening(), apply_differential_privacy()])


    URL = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"

    async def send_receive():

            print(f'Connecting websocket to url ${URL}')

            async with websockets.connect(
                    URL,
                    extra_headers=(("Authorization", auth_key),),
                    ping_interval=5,
                    ping_timeout=20
            ) as _ws:

                    r = await asyncio.sleep(0.1)
                    print("Receiving SessionBegins ...")

                    session_begins = await _ws.recv()
                    print(session_begins)
                    print("Sending messages ...")


                    async def send():
                            while st.session_state['run']:
                                    try:
                                            data = stream.read(FRAMES_PER_BUFFER)
                                            data = base64.b64encode(data).decode("utf-8")

                                            json_data = json.dumps({"audio_data":str(data)})
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
                            while st.session_state['run']:
                                    try:
                                            result_str = await _ws.recv()
                                            result = json.loads(result_str)['text']
                                            if json.loads(result_str)['message_type']=='FinalTranscript':
                                                    print(result)

                                                    st.session_state['text'] = f"<span style='color: orange;'>User:</span> {result}"
                                                    st.markdown(st.session_state['text'], unsafe_allow_html=True)
                                                    print(result)
                                                    transcript.append("User: "+result) # Global Transcript
                                                    conversation_history.append({"role": "user", "content": result})
                                                    
                                                    messages = list(conversation_history)
                                                    if(result):
                                                            message = f'''Act as a technical interview assistant.
                                                            Provide detailed explanations, tips, or feedback in response to the user's
                                                            technical query or request for feedback on their answer. User's query or statement: '{result}. Keep everything within very crisp, on point.'''
                                                            if message:
                                                                    messages.append({"role": "user", "content": message})
                                                                    chat = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=messages)
                                                                    reply = chat.choices[0].message.content
                                                                    print(f"InterviewGPT: {reply}")
                                                                    conversation_history.append({"role": "assistant", "content": reply})
                                                                    transcript.append("InterviewGPT: "+reply) # Global Transcript

                                                            st.session_state['chatText'] = f"<span style='color: green;'>InterviewGPT:</span> {reply}"
                                                            st.markdown(st.session_state['chatText'], unsafe_allow_html=True)

                                    except websockets.exceptions.ConnectionClosedError as e:
                                            print(e)
                                            assert e.code == 4008
                                            break

                                    except Exception as e:
                                            print(e)
                                            assert False, "Not a websocket 4008 error"

                    send_result, receive_result = await asyncio.gather(send(), receive())


    asyncio.run(send_receive())


        
        

