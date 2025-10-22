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
from app.controls.services import ControlService
from app.database.models.users import User
from app.chat.services import ChatStreamingService
from app.chat.skills import (
    create_skill_registry,
    SkillContextFactory,
    ConversationState,
)
from app.assessments.base import CSRFTokenManager

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)
chat_service = ChatStreamingService()
control_service = ControlService()
csrf_manager = CSRFTokenManager()
skill_registry = create_skill_registry()
skill_context_factory = SkillContextFactory()


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


class EvidenceDescriptionRequest(BaseModel):
    """Request model for evidence description parsing."""

    control_id: str
    description: str


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


@router.get("/actions")
async def get_context_actions(
    current_url: str,
    current_user: Optional[User] = Depends(get_user_from_session),
) -> JSONResponse:
    """Get available actions based on the current page context."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Build context for skill discovery
    context = await skill_context_factory.create(
        user=current_user,
        current_url=current_url,
    )

    # Get all available actions from skills
    actions = await skill_registry.get_all_available_actions(context)

    # Convert actions to dicts for JSON serialization
    actions_dict = [action.to_dict() for action in actions]

    # Build context text (optional - for backwards compatibility)
    context_text = ""
    if actions_dict:
        context_text = "The following actions are available:"

    return JSONResponse(content={"context": context_text, "actions": actions_dict})


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
    """Execute a chat action through the skill registry."""
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
        # Build context
        context = await skill_context_factory.create(
            user=current_user,
            session_id=action.params.get("session_id"),
            current_url=action.params.get("current_url"),
            csrf_token=csrf_token,
        )

        # Find and execute skill
        skill = await skill_registry.find_skill(
            action.action_type,
            action.params,
            context,
        )

        if not skill:
            raise HTTPException(
                status_code=400,
                detail=f"No skill found for action: {action.action_type}",
            )

        result = await skill.execute(
            action.action_type,
            action.params,
            context,
        )

        # Handle conversation state
        if result.conversation_state:
            state_action = ConversationState.create_state_action(
                result.conversation_state
            )
            await context.repository.append_message(
                user_id=current_user.user_id,
                session_id=context.session_id,
                role="assistant",
                content=result.message,
                actions=[state_action.to_dict()],
            )

        # Convert actions to dicts for JSON serialization
        actions_dict = None
        if result.actions:
            actions_dict = [action.to_dict() for action in result.actions]

        # Ensure data dict exists and includes session_id
        response_data = result.data or {}
        response_data["session_id"] = context.session_id

        return JSONResponse(
            content={
                "success": result.success,
                "message": result.message,
                "data": response_data,
                "actions": actions_dict,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error executing action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evidence/parse")
async def parse_evidence_description(
    evidence_request: EvidenceDescriptionRequest,
    current_user: Optional[User] = Depends(get_user_from_session),
) -> JSONResponse:
    """Parse natural language evidence description into structured data."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        control = control_service.get_control(
            evidence_request.control_id, current_user.user_id
        )

        if not control:
            raise HTTPException(status_code=404, detail="Control not found")

        control_info = (
            f"{control.nist_control_id}: {control.control_title}\n{control.description}"
        )

        # Parse the evidence description
        parsed_evidence = await chat_service.parse_evidence_description(
            evidence_request.description, control_info
        )

        return JSONResponse(
            content={
                "success": True,
                "evidence": parsed_evidence,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error parsing evidence description: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to parse evidence description: {str(e)}"
        )
