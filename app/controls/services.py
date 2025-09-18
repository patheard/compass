"""Control service layer for business logic and data operations."""

from typing import List
from fastapi import HTTPException
from app.database.models.controls import Control
from app.database.models.assessments import SecurityAssessment
from app.assessments.base import BaseService
from app.controls.validation import (
    ControlCreateRequest,
    ControlUpdateRequest,
    ControlResponse,
)


class ControlService(BaseService[Control]):
    """Service class for control CRUD operations."""

    def __init__(self):
        super().__init__(Control)

    def validate_ownership(self, entity: Control, user_id: str) -> bool:
        """Validate that the user owns the assessment containing the control."""
        try:
            assessment = SecurityAssessment.get(entity.assessment_id)
            return assessment.is_owner(user_id)
        except SecurityAssessment.DoesNotExist:
            return False

    def get_user_entities(self, user_id: str) -> List[Control]:
        """Get all controls belonging to user's assessments."""
        try:
            # Get all user's assessments first
            user_assessments = SecurityAssessment.get_by_owner(user_id)
            all_controls = []

            for assessment in user_assessments:
                controls = Control.get_by_assessment(assessment.assessment_id)
                all_controls.extend(controls)

            return all_controls
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve controls: {str(e)}"
            )

    def validate_assessment_access(self, assessment_id: str, user_id: str) -> None:
        """Validate that user has access to the assessment."""
        try:
            assessment = SecurityAssessment.get(assessment_id)
            if not assessment.is_owner(user_id):
                raise HTTPException(
                    status_code=403, detail="Access denied to assessment"
                )
        except SecurityAssessment.DoesNotExist:
            raise HTTPException(status_code=404, detail="Assessment not found")

    def create_control(
        self, assessment_id: str, user_id: str, data: ControlCreateRequest
    ) -> ControlResponse:
        """Create a new control."""
        # Validate assessment access
        self.validate_assessment_access(assessment_id, user_id)

        # Check for duplicate NIST control ID in assessment
        existing_control = Control.get_by_assessment_and_nist_id(
            assessment_id, data.nist_control_id
        )
        if existing_control:
            raise HTTPException(
                status_code=400,
                detail=f"Control {data.nist_control_id} already exists in this assessment",
            )

        try:
            control = Control.create_control(
                assessment_id=assessment_id,
                nist_control_id=data.nist_control_id,
                control_title=data.control_title,
                control_description=data.control_description,
            )
            return self._to_response(control)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to create control: {str(e)}"
            )

    def get_control(self, control_id: str, user_id: str) -> ControlResponse:
        """Get a specific control by ID."""
        control = self.get_entity_or_404(control_id, user_id)
        return self._to_response(control)

    def list_controls_by_assessment(
        self, assessment_id: str, user_id: str
    ) -> List[ControlResponse]:
        """List all controls for a specific assessment."""
        # Validate assessment access
        self.validate_assessment_access(assessment_id, user_id)

        try:
            controls = Control.get_by_assessment(assessment_id)
            return [self._to_response(control) for control in controls]
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve controls: {str(e)}"
            )

    def update_control(
        self, control_id: str, user_id: str, data: ControlUpdateRequest
    ) -> ControlResponse:
        """Update an existing control."""
        control = self.get_entity_or_404(control_id, user_id)

        try:
            # Check for duplicate NIST control ID if being updated
            if data.nist_control_id and data.nist_control_id != control.nist_control_id:
                existing_control = Control.get_by_assessment_and_nist_id(
                    control.assessment_id, data.nist_control_id
                )
                if existing_control and existing_control.control_id != control_id:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Control {data.nist_control_id} already exists in this assessment",
                    )

            # Update only provided fields
            if data.nist_control_id is not None:
                control.nist_control_id = data.nist_control_id

            if data.control_title is not None:
                control.control_title = data.control_title

            if data.control_description is not None:
                control.control_description = data.control_description

            if data.implementation_status is not None:
                control.update_implementation_status(data.implementation_status)
            else:
                control.save()

            return self._to_response(control)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to update control: {str(e)}"
            )

    def delete_control(self, control_id: str, user_id: str) -> None:
        """Delete a control."""
        control = self.get_entity_or_404(control_id, user_id)

        try:
            control.delete()
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to delete control: {str(e)}"
            )

    def _to_response(self, control: Control) -> ControlResponse:
        """Convert control model to response schema."""
        return ControlResponse(
            control_id=control.control_id,
            assessment_id=control.assessment_id,
            nist_control_id=control.nist_control_id,
            control_title=control.control_title,
            control_description=control.control_description,
            implementation_status=control.implementation_status,
            created_at=control.created_at,
            updated_at=control.updated_at,
        )
