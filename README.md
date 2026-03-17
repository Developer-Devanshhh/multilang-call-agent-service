# Real-Time Multilingual Voice Agent Microservice

A standalone real-time voice AI microservice built with **FastAPI**, **Google Cloud STT**, **Gemini 1.5/2.5 Flash**, and **Sarvam TTS**. This service acts as a fully autonomous government/civic customer support agent capable of speaking naturally with citizens natively in multiple Indian languages over a phone call or browser microphone.

## 🚀 Features

- **Native Multilingual Processing:** Directly processes Hindi, English, Tamil, Marathi, and other regional languages without clunky translation layers, unlocking ultra-fast latency.
- **Smart Data Extraction:** While conversing naturally, the Gemini agent seamlessly extracts structured JSON data (issue description, department, location, severity, and ward number) from the user.
- **Auto Database Storage:** The parsed MongoDB document (`TicketMongo`) is directly saved to your database, along with a full transcript of the conversation (`VoiceCallLogMongo`).
- **Audio Overlap Prevention:** Built-in mechanisms handle audio buffering and actively prevent the agent from talking over itself or capturing its own voice feedback.
- **Cross-Platform Telephony:** 
  - Works natively with Twilio Media Streams (Bidirectional WebSockets).
  - Works out of the box with the included WebRTC Browser Client for testing without a real phone number.

## 🏗️ Architecture Stack

- **Framework:** FastAPI / WebSockets (Python 3.10+)
- **Database:** MongoDB via [Beanie ODM](https://beanie-odm.dev/) + Motor
- **Speech-to-Text (STT):** Google Cloud Speech-to-Text API
- **Agent Intelligence:** Gemini 1.5/2.5 Flash
- **Text-to-Speech (TTS):** Sarvam AI (bulbul:v3)

## 📁 Project Structure

```
├── app/
│   ├── main.py                 # FastAPI mounting & Router setup
│   ├── config.py               # Environment variables mapping
│   ├── database.py             # Beanie/Motor ODM initialization
│   ├── api/
│   │   ├── twilio.py           # Twilio inbound WebSockets
│   │   ├── exotel.py           # Exotel integration stub
│   │   └── demo.py             # Browser WebSocket handler
│   ├── models/
│   │   ├── ticket.py           # Civic Issue Ticket Schema
│   │   └── voice_call.py       # Conversation Logging Schema
│   └── services/
│       ├── audio_utils.py      # Base64 μ-law (Twilio) ↔ PCM 16-bit 8kHz
│       ├── google_stt.py       # Async Google Gen2 STT
│       ├── gemini_agent.py     # Multilingual Native prompt logic
│       ├── sarvam_tts.py       # Text-to-Speech logic
│       └── session_manager.py  # Tracks call state & AI pipeline execution
├── static/
│   └── demo_client.html        # Test the agent instantly in your browser
├── .env.example
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## 🛠️ Local Setup & Installation

### 1. Prerequisites
- Python 3.10 or higher
- MongoDB cluster URI (e.g. MongoDB Atlas)
- API Keys for Google Cloud, Gemini, and Sarvam AI.

### 2. Environment Variables
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```

Your `.env` should look like this:
```ini
MONGODB_URI=mongodb+srv://<user>:<password>@cluster...
GEMINI_API_KEY=your_gemini_api_key
SARVAM_API_KEY=your_sarvam_api_key
GOOGLE_APPLICATION_CREDENTIALS=C:/path/to/your/gcp-credentials.json
```
*(Windows Users: Ensure your GCP credentials path uses **forward slashes** `/` instead of backslashes `\` to avoid escape character issues).*

### 3. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # Or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

### 4. Run the Application
Start the ASGI server:
```bash
uvicorn app.main:app --reload --port 8001
```

## 🎙️ Testing the Agent (No Phone Needed)

We've included a powerful browser client to test the AI without setting up Twilio:
1. Start the server (as shown above).
2. Open your browser and navigate to: `http://localhost:8001/static/demo_client.html`
3. Allow microphone permissions.
4. Click **Start Call**. 
5. The agent will greet you and ask for your preferred language. You can respond in English, Hindi, or other supported regional languages!

## 📞 Twilio Setup (For actual phone calls)
1. Purchase a Twilio phone number.
2. In the Twilio Console, configure the Webhook URL for incoming calls to: 
   `https://<your-ngrok-url>/api/twilio/incoming`
3. Ensure your local server is exposed to the internet via `ngrok http 8001` or deployed on a VPS.

## 📝 License
MIT License
