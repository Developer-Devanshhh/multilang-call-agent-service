from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import uuid
import base64
import traceback
from app.services.session_manager import session_manager
from app.services.audio_utils import pcm_to_wav

router = APIRouter(prefix="/demo", tags=["Demo"])

@router.websocket("/ws")
async def demo_websocket(websocket: WebSocket):
    await websocket.accept()
    call_id = f"demo_{uuid.uuid4().hex[:8]}"
    session = session_manager.create_session(call_id, "demo_browser", "Web Client")
    print(f"Browser Demo started: {call_id}")
    
    try:
        # Send initial greeting immediately
        greeting_audio = await session_manager.generate_greeting(session)
        if greeting_audio:
            wav_bytes = pcm_to_wav(greeting_audio)
            b64_wav = base64.b64encode(wav_bytes).decode()
            await websocket.send_text(json.dumps({
                "event": "media",
                "media": {"payload": b64_wav, "format": "wav"}
            }))
            await websocket.send_text(json.dumps({
                "event": "transcript",
                "transcript": session.conversation_log
            }))
        
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg.get("event") == "media":
                b64_payload = msg.get("media", {}).get("payload", "")
                audio_format = msg.get("media", {}).get("format", "")
                
                if not b64_payload:
                    continue
                    
                raw_bytes = base64.b64decode(b64_payload)
                
                if audio_format == "pcm_s16le_8000":
                    # Browser is sending raw PCM 16-bit 8kHz mono — use directly
                    pcm_bytes = raw_bytes
                else:
                    # Legacy: try WebM conversion
                    try:
                        from app.services.audio_utils import webm_to_pcm
                        pcm_bytes = webm_to_pcm(raw_bytes)
                    except Exception:
                        pcm_bytes = raw_bytes
                
                session.audio_buffer.extend(pcm_bytes)
                
                # Process when we have ~1.5 seconds of audio
                # 8000 Hz * 2 bytes * 1.5 sec = 24000 bytes
                if len(session.audio_buffer) > 24000 and not session.is_processing:
                    agent_audio = await session_manager.process_audio_buffer(session)
                    
                    if agent_audio:
                        wav_bytes = pcm_to_wav(agent_audio)
                        b64_wav = base64.b64encode(wav_bytes).decode()
                        
                        await websocket.send_text(json.dumps({
                            "event": "media",
                            "media": {"payload": b64_wav, "format": "wav"}
                        }))
                        
                        await websocket.send_text(json.dumps({
                            "event": "transcript",
                            "transcript": session.conversation_log
                        }))
                        
                        if session.state == "COMPLETED":
                            await websocket.send_text(json.dumps({
                                "event": "completed",
                                "ticket": session.extracted_data
                            }))
                            
            elif msg.get("event") == "stop":
                print(f"Demo stop requested: {call_id}")
                break
                
    except WebSocketDisconnect:
        print(f"Demo WS disconnected: {call_id}")
    except Exception as e:
        print(f"Demo WS Error: {e}")
        traceback.print_exc()
    finally:
        await session_manager.end_session(call_id)
