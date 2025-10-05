"""Chat routes for web interface and API endpoints."""

import json
import logging
from typing import Any, Dict, Optional
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
from app.evidence.services import EvidenceService
from app.evidence.validation import EvidenceRequest
from app.assessments.base import CSRFTokenManager

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)
chat_service = ChatStreamingService()
csrf_manager = CSRFTokenManager()


class ChatMessage(BaseModel):
    """Request model for chat messages."""

    message: str
    session_id: Optional[str] = None
    current_page: Optional[str] = None
    current_url: Optional[str] = None


class ChatAction(BaseModel):
    """Request model for chat action execution."""

    action_type: str
    params: Dict[str, Any]


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
        user=current_user,
        message=chat_message.message,
        session_id=chat_message.session_id,
        current_page=chat_message.current_page,
        current_url=chat_message.current_url,
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
            current_url = message_data.get("current_url", "").strip()
            if not user_message:
                continue

            # Stream response back to client
            await chat_service.stream_to_websocket(
                user_message,
                user,
                websocket,
                session_id=session_id,
                current_page=current_page,
                current_url=current_url,
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


@router.post("/action")
async def execute_chat_action(
    request: Request,
    action: ChatAction,
    current_user: Optional[User] = Depends(get_user_from_session),
) -> JSONResponse:
    """Execute a chat action on behalf of the authenticated user."""
    # Require authentication
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Get CSRF token from request body
    body = await request.json()
    csrf_token = body.get("csrf_token")

    # Validate CSRF token
    session_token = request.session.get("csrf_token")
    if not csrf_manager.validate_csrf_token(session_token, csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")

    try:
        if action.action_type == "add_evidence":
            # Execute add_evidence action
            result = await _execute_add_evidence_action(
                action.params, current_user.user_id
            )
            return JSONResponse(
                content={"success": True, "message": result["message"], "data": result}
            )
        else:
            raise HTTPException(
                status_code=400, detail=f"Unknown action type: {action.action_type}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error executing chat action: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to execute action: {str(e)}"
        )


async def _execute_add_evidence_action(
    params: Dict[str, Any], user_id: str
) -> Dict[str, Any]:
    """Execute the add_evidence action."""
    # Validate required parameters
    required_params = ["control_id", "evidence_type", "title", "description"]
    for param in required_params:
        if param not in params:
            raise HTTPException(
                status_code=400, detail=f"Missing required parameter: {param}"
            )

    control_id = params["control_id"]
    evidence_type = params["evidence_type"]
    title = params["title"]
    description = params["description"]
    job_template_id = params.get("job_template_id")
    aws_account_id = params.get("aws_account_id")

    # Create evidence request
    evidence_data = EvidenceRequest(
        title=title,
        description=description,
        evidence_type=evidence_type,
        job_template_id=job_template_id,
        aws_account_id=aws_account_id,
    )

    # Use evidence service to create evidence
    evidence_service = EvidenceService()
    evidence = evidence_service.create_evidence(control_id, user_id, evidence_data)

    return {
        "message": f"Successfully added evidence **{title}** to the control",
        "evidence_id": evidence.evidence_id,
        "control_id": control_id,
    }
