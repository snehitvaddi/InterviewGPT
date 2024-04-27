## Introduction
**InterviewGPT V2**: A real-time Audio Transcription + LLM interview preparation application. Listens to the system's output voice and responds in real time.

## Video Demo
Click on the thumbnail to watch the demo.<br>
<a href="https://youtu.be/26__rpg5AvA">
[![Demo](https://github.com/snehitvaddi/InterviewGPT/blob/main/ApplicationDemo.gif?raw=true)](https://github.com/snehitvaddi/InterviewGPT/blob/main/ApplicationDemo.mp4.mp4?raw=true)
</a>

## Setup:
```
pip install -r requirements.txt
```

```
export GROQ_API_KEY='Your_Groq_API_Key'
export ASSEMBLY_AI_API_KEY='Your_AssemblyAI_API_Key'
```
```
streamlit run app.py
```

## Technologies Used
- **Speech to Text**: Utilizes AssemblyAI.
- **NLP and Response Generation**: Groq API.
- **Model**: llama3-8b-8192
- **Web Framework**: Streamlit.
- **Security**: Streamlit Authenticator and data obscuring strategies to protect user privacy.

## Features
- Real-time audio to text conversion using AssemblyAI.
- Intelligent response generation using Groq's powerful AI models.
- Interactive web interface built with Streamlit.
- User authentication for secure access.
- Audio data handling and differential privacy considerations.

## Prerequisites
- Python 3.7 or higher
- pip
- Groq API access
- AssemblyAI API access



