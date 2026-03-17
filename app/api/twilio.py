from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import Response
import json
import traceback
from app.services.session_manager import session_manager
from app.services.audio_utils import decode_twilio_audio, encode_for_twilio

router = APIRouter(prefix="/twilio", tags=["Twilio"])

@router.post("/incoming")
async def twilio_incoming(request: Request):
    """
    Webhook triggered by Twilio when a call comes in.
    Returns TwiML instructing Twilio to open a bidirectional Media Stream.
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown_call")
    from_number = form_data.get("From", "Unknown")
    
    host = request.headers.get("host", "localhost:8001")
    protocol = "wss" if ("ngrok" in host or "https" in str(request.url)) else "ws"
    ws_url = f"{protocol}://{host}/api/twilio/ws"

    print(f"Twilio incoming call: {call_sid} from {from_number}")

    twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}">
            <Parameter name="call_sid" value="{call_sid}" />
            <Parameter name="caller" value="{from_number}" />
        </Stream>
    </Connect>
</Response>'''
    
    return Response(content=twiml, media_type="text/xml")

@router.post("/status")
async def twilio_status(request: Request):
    """Twilio call status callback."""
    form_data = await request.form()
    print(f"Twilio status: {dict(form_data)}")
    return {"status": "received"}

@router.websocket("/ws")
async def twilio_websocket(websocket: WebSocket):
    await websocket.accept()
    
    stream_sid = None
    call_sid = "unknown"
    session = None
    
    try:
        while True:
            msg_text = await websocket.receive_text()
            msg = json.loads(msg_text)
            event = msg.get("event")
            
            if event == "connected":
                print("Twilio WS connected")
                
            elif event == "start":
                start_data = msg.get("start", {})
                stream_sid = start_data.get("streamSid", "")
                custom_params = start_data.get("customParameters", {})
                call_sid = custom_params.get("call_sid", start_data.get("callSid", "unknown"))
                caller = custom_params.get("caller", "Unknown")
                
                session = session_manager.create_session(call_sid, "twilio", caller)
                print(f"Twilio Stream Started: call={call_sid} stream={stream_sid}")
                
                # Send initial greeting
                greeting_audio = await session_manager.generate_greeting(session)
                if greeting_audio and stream_sid:
                    b64_audio = encode_for_twilio(greeting_audio)
                    await websocket.send_text(json.dumps({
                        "event": "media",
                        "streamSid": stream_sid,
                        "media": {"payload": b64_audio}
                    }))
                
            elif event == "media":
                if not session:
                    continue
                    
                payload_b64 = msg.get("media", {}).get("payload", "")
                if not payload_b64:
                    continue
                    
                pcm_bytes = decode_twilio_audio(payload_b64)
                session.audio_buffer.extend(pcm_bytes)
                
                # Process when buffer has ~2 seconds of audio (32000 bytes at 16kHz)
                if len(session.audio_buffer) > 24000 and not session.is_processing:
                    agent_audio = await session_manager.process_audio_buffer(session)
                    
                    if agent_audio and stream_sid:
                        b64_response = encode_for_twilio(agent_audio)
                        
                        # Clear any buffered audio first
                        await websocket.send_text(json.dumps({
                            "event": "clear",
                            "streamSid": stream_sid
                        }))
                        
                        # Send response audio
                        await websocket.send_text(json.dumps({
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {"payload": b64_response}
                        }))
                        
                        # Mark completion
                        await websocket.send_text(json.dumps({
                            "event": "mark",
                            "streamSid": stream_sid,
                            "mark": {"name": "agent_response"}
                        }))
                        
                        if session.state == "COMPLETED":
                            print("Call completed, ending session")
                            break
                            
            elif event == "stop":
                print(f"Twilio Stream Stopped: {call_sid}")
                break
                
            elif event == "mark":
                pass  # Mark acknowledgment from Twilio
                
    except WebSocketDisconnect:
        print(f"Twilio WS disconnected: {call_sid}")
    except Exception as e:
        print(f"Twilio WS Error: {e}")
        traceback.print_exc()
    finally:
        if session:
            await session_manager.end_session(call_sid)
