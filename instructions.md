# Voice Complaint Registration Agent — 

## Project Overview

Build a production-ready voice call agent microservice for an Indian government
complaint registration system. Citizens call a phone number, speak their complaint
in any Indian language, and the agent extracts structured data and stores it in
MongoDB. After registration, the citizen receives an SMS and/or email confirmation.

This is one microservice in a larger governance platform. It must expose clean
APIs so the main project can query complaints, update statuses, and trigger
re-notifications.

---

## Tech Stack (strict — no substitutions)

### Primary AI Services

- **STT**: Sarvam AI — `saaras:v3` model (auto language detection, 12 Indic languages)
- **TTS**: Sarvam AI — `bulbul:v1` model (11 Indic languages, streaming)
- **Translation**: Sarvam AI — `mayura:v1` (citizen lang ↔ English)
- **LLM**: Google Gemini Flash 2.0 (`gemini-2.0-flash`) via google-generativeai SDK

### Fallback AI Services (triggered when Sarvam confidence < 0.70)

- **STT fallback**: Google Cloud Speech-to-Text v2 (chirp_2 model, multi-region)
- **TTS fallback**: Google Cloud Text-to-Speech (Neural2 / Wavenet Indic voices)

### Telephony

- **Provider**: Exotel (India)
- **Protocol**: Bidirectional WebSocket (wss://) — Exotel Voicebot Applet
- **Audio format**: PCM 16-bit, 8kHz, mono, base64-encoded, 100ms chunks (3200 bytes raw)

### Backend

- **Framework**: FastAPI (Python 3.11+)
- **WebSocket**: FastAPI native WebSocket + asyncio
- **Database**: MongoDB (Motor async driver)
- **Validation**: Pydantic v2

### Notifications

- **SMS**: Twilio (fallback: MSG91 if Twilio credits unavailable)
- **Email**: SendGrid (fallback: SMTP via Gmail for dev)

### Infrastructure

- **Containerization**: Docker + docker-compose
- **Reverse proxy**: Nginx (for WSS termination in production)
- **Dev tunneling**: ngrok (for Exotel webhook during local dev)

---

## Repository Structure to Create






what if exotel doesn't works?

**18:37**

Good question. Exotel has a few pain points — KYC takes days, pricing isn't transparent, and their WebSocket Voicebot Applet is a relatively newer feature that can be flaky. Here are all your real alternatives, ranked by how well they work for this use case:

**Searched the web**

Searched the web

Good research. Here's the full picture — every real fallback option ranked, with the key technical differences your code needs to handle for each.

<iframe sandbox="allow-scripts allow-same-origin allow-forms" allow="fullscreen *; clipboard-write *" src="https://3e17935aa299337f0bf6a226c77c5ae8.claudemcpcontent.com/mcp_apps?connect-src=https%3A%2F%2Fesm.sh+https%3A%2F%2Fcdnjs.cloudflare.com+https%3A%2F%2Fcdn.jsdelivr.net+https%3A%2F%2Funpkg.com&resource-src=https%3A%2F%2Fesm.sh+https%3A%2F%2Fcdnjs.cloudflare.com+https%3A%2F%2Fcdn.jsdelivr.net+https%3A%2F%2Funpkg.com+https%3A%2F%2Fassets.claude.ai&dev=true"></iframe>

---

## The one critical difference: audio codec

This is where most people get stuck switching providers. Every telephony provider sends a different audio format over WebSocket, and Sarvam expects  **WAV/PCM** . Here's the decode map:

```
Exotel  → base64(PCM 16-bit 8kHz)  → decode b64 → send directly as WAV ✓
Twilio  → base64(μ-law 8kHz)       → decode b64 → audioop.ulaw2lin() → WAV
Plivo   → base64(μ-law 8kHz)       → decode b64 → audioop.ulaw2lin() → WAV
         OR request L16 directly   → decode b64 → send as WAV ✓ (no conversion)
Telnyx  → base64(μ-law 8kHz)       → decode b64 → audioop.ulaw2lin() → WAV
```

So the only thing that changes between providers in your codebase is this one utility function:

python

```python
# services/audio_utils.py

import audioop, io, wave, base64

defdecode_twilio_audio(b64_payload:str)->bytes:
"""Twilio/Telnyx: base64 μ-law → raw PCM 16-bit 8kHz"""
    mulaw_bytes = base64.b64decode(b64_payload)
    pcm_bytes = audioop.ulaw2lin(mulaw_bytes,2)# 2 = 16-bit samples
return pcm_bytes

defdecode_plivo_audio(b64_payload:str, content_type:str)->bytes:
"""Plivo: supports both μ-law and L16 PCM"""
    raw = base64.b64decode(b64_payload)
if"mulaw"in content_type or"pcmu"in content_type:
return audioop.ulaw2lin(raw,2)
return raw  # already PCM if content_type is audio/x-l16

defdecode_exotel_audio(b64_payload:str)->bytes:
"""Exotel: already PCM, just base64 decode"""
return base64.b64decode(b64_payload)

defpcm_to_wav(pcm_bytes:bytes, sample_rate:int=8000)->bytes:
"""Wrap raw PCM in WAV header for Sarvam STT"""
    buf = io.BytesIO()
with wave.open(buf,'wb')as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
return buf.getvalue()

defencode_for_twilio(pcm_bytes:bytes)->str:
"""PCM → μ-law → base64 for sending back to Twilio"""
    mulaw = audioop.lin2ulaw(pcm_bytes,2)
return base64.b64encode(mulaw).decode()

defencode_for_plivo_l16(pcm_bytes:bytes)->str:
"""PCM → base64 for Plivo L16 response"""
return base64.b64encode(pcm_bytes).decode()
```

---

## The fastest path right now: Twilio + no KYC wait

Twilio's bidirectional Media Streams let your WebSocket application both receive audio from Twilio and send audio back — the exact use case for a real-time voice conversation with an AI assistant. [Huskyvoice](https://www.huskyvoice.ai/ai-translator)

Sign up at twilio.com → get $15 free credit → buy a +91 India number (about $1/month) → done in 10 minutes. No KYC, no waiting.

The TwiML you return when a call comes in is just:

xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
<Connect>
<Streamurl="wss://your-domain.com/ws/complaint">
<Parametername="provider"value="twilio"/>
</Stream>
</Connect>
</Response>
```

Twilio sends a `connected` event first, then a `start` event with metadata, then continuous `media` events with base64 μ-law audio. For bidirectional streams, your server sends `media` messages back with base64 μ-law audio for Twilio to play to the caller, and a `clear` message to interrupt buffered audio. [Bolna](https://www.bolna.ai/)

---

## Option 5: Skip telephony entirely for hackathon/demo

If you need a working demo *today* without any provider signup, build a browser WebSocket client that captures mic audio and streams it directly to your FastAPI `/ws/complaint` endpoint. The citizen "calls" by opening a web page and clicking a button. It's not a real phone call, but it demonstrates the full AI pipeline end to end — STT, LLM, TTS, MongoDB write, confirmation — which is what judges evaluate.

html

```html
<!-- demo_client.html — streams mic directly to your bot server -->
<buttonid="call">Start Complaint Call</button>
<script>
const ws =newWebSocket("wss://your-ngrok-url/ws/complaint");
ws.onopen=async()=>{
const stream =awaitnavigator.mediaDevices.getUserMedia({audio:true});
const recorder =newMediaRecorder(stream,{mimeType:'audio/webm'});
  recorder.ondataavailable=e=>{
// Convert blob to base64 and send as mock Twilio media event
const reader =newFileReader();
    reader.onload=()=> ws.send(JSON.stringify({
event:"media",
media:{payload: reader.result.split(',')[1]}
}));
    reader.readAsDataURL(e.data);
};
  recorder.start(100);// 100ms chunks
};
ws.onmessage=e=>{
const msg =JSON.parse(e.data);
if(msg.event==="media"){
// Play response audio
const audio =newAudio("data:audio/wav;base64,"+ msg.media.payload);
    audio.play();
}
};
document.getElementById('call').onclick=()=> ws.send(
JSON.stringify({event:"connected",start:{callSid:"DEMO_"+Date.now()}})
);
</script>
```

---

## Updated `.env.example` with provider switch

Add a single `TELEPHONY_PROVIDER` env var so you can swap providers without changing any logic:

env

```env
# Switch between: twilio | plivo | exotel | demo
TELEPHONY_PROVIDER=twilio

# Twilio (active if TELEPHONY_PROVIDER=twilio)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+91XXXXXXXXXX

# Plivo (active if TELEPHONY_PROVIDER=plivo)
PLIVO_AUTH_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
PLIVO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
PLIVO_PHONE_NUMBER=+91XXXXXXXXXX
PLIVO_AUDIO_FORMAT=l16   # or mulaw

# Exotel (active if TELEPHONY_PROVIDER=exotel)
EXOTEL_API_KEY=xxx
EXOTEL_API_TOKEN=xxx
EXOTEL_ACCOUNT_SID=xxx
```

And in your `main.py`, the WebSocket handler just reads `settings.TELEPHONY_PROVIDER` and calls the right decoder — everything else (Sarvam, Gemini, MongoDB) is identical regardless of which provider is sending the audio.

---

 **Bottom line** : use Twilio right now. It's instant, has a +91 number, the best docs, and the most FastAPI code examples online. Plivo supports bidirectional streaming with the option to request L16 PCM directly [Sarvam AI](https://www.sarvam.ai/apis/text-to-speech), which actually makes it slightly simpler than Twilio (no μ-law decode step if you set `contentType="audio/x-l16;rate=8000"`), so it's a strong second choice. Keep Exotel as the production upgrade once KYC clears — its India PSTN routing is genuinely better for rural callers on BSNL/MTNL networks.
