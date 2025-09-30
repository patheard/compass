"""Chat routes for web interface and API endpoints."""

import json
import logging
from typing import Optional
from fastapi import (
    APIRouter,
    Request,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.auth.middleware import get_user_from_session
from app.auth.websocket import get_websocket_auth
from app.database.models.users import User
from app.chat.services import ChatStreamingService

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)
chat_service = ChatStreamingService()


class ChatMessage(BaseModel):
    """Request model for chat messages."""

    message: str
    session_id: Optional[str] = None
    current_page: Optional[str] = None


@router.post("/response")
async def get_chat_response(
    chat_message: ChatMessage,
    request: Request,
    current_user: Optional[User] = Depends(get_user_from_session),
) -> JSONResponse:
    """Get a chat response for the AI assistant based on user input."""
    # Require authentication
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Use the streaming service to get a complete response
    result = await chat_service.get_full_response(
        chat_message.message,
        current_user,
        chat_message.session_id,
        chat_message.current_page,
    )

    return JSONResponse(content=result)


@router.websocket("/ws")
async def websocket_chat_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat streaming."""
    await websocket.accept()

    # Authenticate the WebSocket connection
    websocket_auth = get_websocket_auth()
    user = await websocket_auth.authenticate_websocket(websocket)
    if not user:
        return  # Connection already closed by authenticate_websocket

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)

            user_message = message_data.get("content", "").strip()
            session_id = message_data.get("session_id")
            current_page = message_data.get("current_page", "").strip()
            if not user_message:
                continue

            # Stream response back to client
            await chat_service.stream_to_websocket(
                user_message,
                user,
                websocket,
                session_id=session_id,
                current_page=current_page,
            )

    except WebSocketDisconnect:
        logger.debug("WebSocket disconnected by client")
    except Exception as e:
        logger.exception("Unexpected error in websocket_chat_endpoint")
        try:
            await websocket.send_text(
                json.dumps({"type": "error", "content": f"Connection error: {str(e)}"})
            )
        except Exception as send_err:
            logger.debug(f"Failed to send error message over websocket: {send_err}")
