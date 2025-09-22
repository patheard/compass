"""Routes for job execution management."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import UUID4

from app.auth.middleware import require_authenticated_user
from app.database.models.users import User
from app.evidence.validation import JobExecutionResponse
from app.job_executions.services import JobExecutionService

router = APIRouter(prefix="/job-executions", tags=["job-executions"])


@router.get("/evidence/{evidence_id}", response_model=List[JobExecutionResponse])
async def get_evidence_executions(
    evidence_id: UUID4,
    current_user: User = Depends(require_authenticated_user),
) -> List[JobExecutionResponse]:
    """Get all scan job executions for a specific evidence."""
    try:
        executions = JobExecutionService.get_evidence_executions(
            str(evidence_id), current_user.user_id
        )
        return [JobExecutionResponse.from_orm(execution) for execution in executions]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{execution_id}", response_model=JobExecutionResponse)
async def get_execution(
    execution_id: UUID4,
    current_user: User = Depends(require_authenticated_user),
) -> JobExecutionResponse:
    """Get a specific scan job execution."""
    try:
        execution = JobExecutionService.get_execution(
            str(execution_id), current_user.user_id
        )
        if not execution:
            raise HTTPException(status_code=404, detail="Execution not found")
        return JobExecutionResponse.from_orm(execution)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{execution_id}/cancel")
async def cancel_execution(
    execution_id: UUID4,
    current_user: User = Depends(require_authenticated_user),
) -> dict:
    """Cancel a pending or running scan job execution."""
    try:
        success = JobExecutionService.cancel_execution(
            str(execution_id), current_user.user_id
        )
        if not success:
            raise HTTPException(
                status_code=404, detail="Execution not found or cannot be cancelled"
            )
        return {"message": "Execution cancelled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{execution_id}/retry")
async def retry_execution(
    execution_id: UUID4,
    current_user: User = Depends(require_authenticated_user),
) -> dict:
    """Retry a failed scan job execution."""
    try:
        success = JobExecutionService.retry_execution(
            str(execution_id), current_user.user_id
        )
        if not success:
            raise HTTPException(
                status_code=404, detail="Execution not found or cannot be retried"
            )
        return {"message": "Execution queued for retry"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status/pending", response_model=List[JobExecutionResponse])
async def get_pending_executions(
    current_user: User = Depends(require_authenticated_user),
) -> List[JobExecutionResponse]:
    """Get all pending scan job executions for the user."""
    try:
        executions = JobExecutionService.get_user_pending_executions(
            current_user.user_id
        )
        return [JobExecutionResponse.from_orm(execution) for execution in executions]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status/running", response_model=List[JobExecutionResponse])
async def get_running_executions(
    current_user: User = Depends(require_authenticated_user),
) -> List[JobExecutionResponse]:
    """Get all running scan job executions for the user."""
    try:
        executions = JobExecutionService.get_user_running_executions(
            current_user.user_id
        )
        return [JobExecutionResponse.from_orm(execution) for execution in executions]
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
