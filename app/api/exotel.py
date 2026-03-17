from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import base64
from app.services.session_manager import session_manager
from app.services.audio_utils import decode_exotel_audio, encode_for_exotel

router = APIRouter(prefix="/exotel", tags=["Exotel"])

@router.websocket("/ws")
async def exotel_websocket(websocket: WebSocket):
    """
    Exotel Voicebot Applet Bidirectional WebSocket
    """
    await websocket.accept()
    
    call_id = "unknown"
    session = None
    
    try:
        while True:
            msg_text = await websocket.receive_text()
            msg = json.loads(msg_text)
            event = msg.get("event")
            
            if event == "connected":
                call_id = msg.get("call_details", {}).get("CallSid", "unknown")
                caller = msg.get("call_details", {}).get("From", "Unknown")
                session = session_manager.create_session(call_id, "exotel", caller)
                print(f"Exotel Call Started: {call_id}")
                
            elif event == "media":
                if not session: continue
                # Exotel sends base64 PCM 16-bit 8kHz
                payload_b64 = msg["media"]["payload"]
                pcm_bytes = decode_exotel_audio(payload_b64)
                
                # Append to buffer
                session.audio_buffer.extend(pcm_bytes)
                
                # If we have buffered enough (~1.5s = 24000 bytes, or check silence)
                if len(session.audio_buffer) > 16000 and not session.is_processing:
                    agent_audio_raw_pcm = await session_manager.process_audio_buffer(session)
                    
                    if agent_audio_raw_pcm:
                        # Send back to Exotel
                        exotel_response_b64 = encode_for_exotel(agent_audio_raw_pcm)
                        out_msg = {
                            "event": "media",
                            "media": {
                                "payload": exotel_response_b64
                            }
                        }
                        await websocket.send_text(json.dumps(out_msg))
                        
                        if session.state == "ENDED":
                            # Close the stream
                            await websocket.send_text(json.dumps({
                                "event": "stop"
                            }))
                            break
                            
            elif event == "stop":
                print(f"Exotel Call Stopped: {call_id}")
                break
                
    except WebSocketDisconnect:
        print(f"Exotel WS disconnected for {call_id}")
    except Exception as e:
        print(f"Exotel WS Error: {e}")
    finally:
        if session:
            await session_manager.end_session(call_id)
