import asyncio
import base64
import json
import uuid
import traceback
from datetime import datetime
from typing import Dict, Optional

from app.services.audio_utils import pcm_to_wav
from app.services.google_stt import stt_service
from app.services.sarvam_tts import tts_service
from app.services.gemini_agent import gemini_agent
from app.models.voice_call import VoiceCallLogMongo
from app.models.ticket import TicketMongo
from app.enums import TicketSource, PriorityLabel

# Languages confirmed supported by Sarvam TTS bulbul:v3
# Ref: https://docs.sarvam.ai (10 Indian languages + en-IN)
SARVAM_TTS_SUPPORTED = {
    "hi-IN", "en-IN", "ta-IN", "te-IN", "kn-IN",
    "ml-IN", "mr-IN", "bn-IN", "pa-IN", "or-IN"
    # Note: gu-IN (Gujarati) NOT supported in bulbul:v3 — falls back to hi-IN
}

def normalize_lang_for_tts(lang_code: str) -> str:
    """Ensure language code is in supported TTS format e.g. hi-IN not hi-in."""
    lang_code = lang_code.strip()
    if "-" not in lang_code:
        lang_code = "en-IN" if lang_code.lower() == "en" else f"{lang_code}-IN"
    parts = lang_code.split("-")
    lang_code = f"{parts[0].lower()}-{parts[1].upper()}"
    if lang_code not in SARVAM_TTS_SUPPORTED:
        print(f"Language {lang_code} not supported by TTS, falling back to hi-IN")
        return "hi-IN"
    return lang_code


class CallSession:
    def __init__(self, call_id: str, provider: str, caller_phone: str):
        self.call_id = call_id
        self.provider = provider
        self.caller_phone = caller_phone
        self.state = "GREETING"
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()

        self.audio_buffer = bytearray()

        # Gemini chat session
        self.chat_session = gemini_agent.start_session()
        self.conversation_log = []

        self.user_language = "en-IN"
        self.is_processing = False
        self.greeting_sent = False

        # Final extracted complaint data
        self.extracted_data = {}


class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, CallSession] = {}

    def create_session(self, call_id: str, provider: str, caller_phone: str) -> CallSession:
        session = CallSession(call_id, provider, caller_phone)
        self.sessions[call_id] = session
        print(f"[Session] Created: {call_id} (provider={provider})")
        return session

    def get_session(self, call_id: str) -> Optional[CallSession]:
        return self.sessions.get(call_id)

    def remove_session(self, call_id: str):
        self.sessions.pop(call_id, None)

    async def generate_greeting(self, session: CallSession) -> Optional[bytes]:
        """Generate and return audio for the initial greeting."""
        try:
            greeting_text = await gemini_agent.get_greeting(session.chat_session)
            session.conversation_log.append({
                "role": "agent",
                "text": greeting_text,
                "timestamp": datetime.utcnow().isoformat()
            })
            print(f"[Greeting] {greeting_text}")
            tts_lang = normalize_lang_for_tts(session.user_language)
            audio = await tts_service.synthesize(greeting_text, tts_lang)
            session.greeting_sent = True
            session.state = "COLLECTING"
            return audio
        except Exception as e:
            print(f"[Greeting Error] {e}")
            traceback.print_exc()
            return None

    async def end_session(self, call_id: str):
        session = self.get_session(call_id)
        if not session:
            return

        session.state = "ENDED"
        ticket_code = None

        # Create ticket if complaint data was extracted
        try:
            ed = session.extracted_data
            desc = ed.get("issue_description") or ed.get("description")
            if desc:
                # Map severity string to PriorityLabel enum
                sev_str = ed.get("severity", "medium").upper()
                priority_map = {
                    "CRITICAL": PriorityLabel.CRITICAL,
                    "HIGH": PriorityLabel.HIGH,
                    "MEDIUM": PriorityLabel.MEDIUM,
                    "LOW": PriorityLabel.LOW,
                }
                priority = priority_map.get(sev_str, PriorityLabel.MEDIUM)

                ticket = TicketMongo(
                    ticket_code=f"VOICE-{uuid.uuid4().hex[:6].upper()}",
                    source=TicketSource.VOICE_CALL,
                    description=desc,
                    dept_id=ed.get("dept_id", "OTHER"),
                    ward_id=ed.get("ward_id") if isinstance(ed.get("ward_id"), int) else None,
                    location_text=ed.get("location_text", ""),
                    reporter_phone=session.caller_phone,
                    language_detected=session.user_language,
                    ai_confidence=0.85,
                    ai_routing_reason="voice_agent_extraction",
                    priority_label=priority,
                    status_timeline=[{
                        "status": "open",
                        "timestamp": datetime.utcnow().isoformat(),
                        "actor_role": "voice_agent",
                        "note": "Created via voice call"
                    }]
                )
                await ticket.insert()
                ticket_code = ticket.ticket_code
                print(f"[Ticket] Created: {ticket_code}")
        except Exception as e:
            print(f"[Ticket Error] {e}")
            traceback.print_exc()

        # Save call log
        try:
            log = VoiceCallLogMongo(
                call_id=session.call_id,
                provider=session.provider,
                caller_phone=session.caller_phone,
                language_detected=session.user_language,
                conversation_log=session.conversation_log,
                extracted_data=session.extracted_data or None,
                ticket_code=ticket_code,
                status="completed" if ticket_code else "abandoned",
                duration_seconds=(datetime.utcnow() - session.created_at).total_seconds(),
                ended_at=datetime.utcnow()
            )
            await log.insert()
            print(f"[Call Log] Saved: {session.call_id}")
        except Exception as e:
            print(f"[Call Log Error] {e}")
            traceback.print_exc()

        self.remove_session(call_id)

    async def process_audio_buffer(self, session: CallSession) -> Optional[bytes]:
        """
        Full AI pipeline: PCM buffer → STT → Gemini → TTS.
        Returns audio bytes for the agent's response.
        """
        if len(session.audio_buffer) < 4000 or session.is_processing:
            return None

        session.is_processing = True
        session.last_activity = datetime.utcnow()

        try:
            # 1. Snapshot + clear buffer
            raw_pcm = bytes(session.audio_buffer)
            session.audio_buffer.clear()
            wav_bytes = pcm_to_wav(raw_pcm)

            # 2. STT
            stt_res = await stt_service.transcribe(wav_bytes)
            user_transcript = stt_res.get("transcript", "").strip()

            if not user_transcript:
                print("[STT] Empty transcript, skipping")
                return None

            detected_lang = stt_res.get("language_code", "en-IN")
            # Normalize: some versions return "hi" instead of "hi-IN"
            if "-" not in detected_lang:
                detected_lang = f"{detected_lang}-IN" if detected_lang != "en" else "en-IN"
            session.user_language = detected_lang

            session.conversation_log.append({
                "role": "citizen",
                "text": user_transcript,
                "timestamp": datetime.utcnow().isoformat()
            })
            print(f"[STT] [{detected_lang}] {user_transcript}")

            # 3. Gemini natively processes the STT transcript
            agent_response = await gemini_agent.process_turn(
                session.chat_session, user_transcript
            )

            # 4. Check for complaint completion signal
            agent_text = agent_response
            if "COMPLAINT_COMPLETE:" in agent_response:
                parts = agent_response.split("COMPLAINT_COMPLETE:", 1)
                agent_text = parts[0].strip()
                json_str = parts[1].strip().strip("`").strip()
                if json_str.startswith("json"):
                    json_str = json_str[4:].strip()
                try:
                    session.extracted_data = json.loads(json_str)
                    print(f"[Extracted] {session.extracted_data}")
                    session.state = "COMPLETED"
                except json.JSONDecodeError as e:
                    print(f"[JSON Parse Error] {e} | Raw: {json_str[:200]}")
                # Ensure we have at least *some* audio reply if the agent stripped everything out accidentally
                if not agent_text:
                    agent_text = "Thank you. Your complaint is registered."

            # 5. Log the native agent response
            session.conversation_log.append({
                "role": "agent",
                "text": agent_text,
                "timestamp": datetime.utcnow().isoformat()
            })
            print(f"[Agent] [{detected_lang}] {agent_text}")

            # 6. TTS — use supported language or fallback to hi-IN
            tts_lang = normalize_lang_for_tts(detected_lang)
            audio_response = await tts_service.synthesize(agent_text, tts_lang)

            if not audio_response:
                print("[TTS] Empty audio, trying en-IN fallback")
                audio_response = await tts_service.synthesize(agent_text, "en-IN")

            return audio_response if audio_response else None

        except Exception as e:
            print(f"[Pipeline Error] {e}")
            traceback.print_exc()
            return None
        finally:
            session.audio_buffer.clear() # Drop audio collected while we were thinking/speaking
            session.is_processing = False


session_manager = SessionManager()
