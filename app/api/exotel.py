from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json
import base64
import asyncio
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
                
                # Send initial greeting audio
                greeting_audio = await session_manager.generate_greeting(session)
                if greeting_audio:
                    print(f"Sending Exotel Greeting: {call_id}")
                    payload_b64 = encode_for_exotel(greeting_audio)
                    
                    # Calculate playback duration (PCM 16-bit 8kHz mono = 16000 bytes/sec)
                    play_duration = len(greeting_audio) / 16000.0
                    
                    session.is_agent_speaking = True
                    session.audio_buffer.clear()
                    await websocket.send_text(json.dumps({
                        "event": "media",
                        "media": {"payload": payload_b64}
                    }))
                    
                    # Wait for audio to finish playing before listening again
                    async def unlock_speech():
                        await asyncio.sleep(play_duration)
                        if session:
                            session.audio_buffer.clear()
                            session.is_agent_speaking = False
                    
                    asyncio.create_task(unlock_speech())
                
            elif event == "media":
                if not session or session.is_processing or session.is_agent_speaking:
                    # Actively discard audio while agent is thinking or speaking
                    continue
                    
                payload_b64 = msg.get("media", {}).get("payload", "")
                if not payload_b64:
                    continue
                    
                # Exotel sends base64 PCM 16-bit 8kHz
                pcm_bytes = decode_exotel_audio(payload_b64)
                session.audio_buffer.extend(pcm_bytes)
                
                # Process when buffer has enough audio (~1.5s = 24000 bytes)
                if len(session.audio_buffer) > 24000:
                    agent_audio = await session_manager.process_audio_buffer(session)
                    
                    if agent_audio:
                        print(f"Sending Exotel Response: {call_id}")
                        payload_b64 = encode_for_exotel(agent_audio)
                        
                        play_duration = len(agent_audio) / 16000.0
                        session.is_agent_speaking = True
                        session.audio_buffer.clear()
                        
                        out_msg = {
                            "event": "media",
                            "media": {"payload": payload_b64}
                        }
                        await websocket.send_text(json.dumps(out_msg))
                        
                        if session.state == "COMPLETED":
                            print(f"Call completed, ending Exotel session: {call_id}")
                            await websocket.send_text(json.dumps({"event": "stop"}))
                            break
                            
                        # Unlock speech after playback completes
                        async def unlock_speech_response():
                            await asyncio.sleep(play_duration)
                            if session:
                                session.audio_buffer.clear()
                                session.is_agent_speaking = False
                                
                        asyncio.create_task(unlock_speech_response())
                            
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
