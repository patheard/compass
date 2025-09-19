"""Assessment service layer for business logic and data operations."""

from typing import List
from fastapi import HTTPException
from app.database.models.assessments import SecurityAssessment
from app.database.models.controls import Control
from app.database.models.evidence import Evidence
from app.assessments.base import BaseService
from app.assessments.validation import (
    AssessmentCreateRequest,
    AssessmentUpdateRequest,
    AssessmentResponse,
)


class AssessmentService(BaseService[SecurityAssessment]):
    """Service class for assessment CRUD operations."""

    def __init__(self):
        super().__init__(SecurityAssessment)

    def validate_ownership(self, entity: SecurityAssessment, user_id: str) -> bool:
        """Validate that the user owns the assessment."""
        return entity.is_owner(user_id)

    def get_user_entities(self, user_id: str) -> List[SecurityAssessment]:
        """Get all assessments belonging to a user."""
        try:
            return SecurityAssessment.get_by_owner(user_id)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve assessments: {str(e)}"
            )

    def create_assessment(
        self, user_id: str, data: AssessmentCreateRequest
    ) -> AssessmentResponse:
        """Create a new assessment."""
        try:
            assessment = SecurityAssessment.create_assessment(
                creator_id=user_id,
                product_name=data.product_name,
                product_description=data.product_description,
            )
            return self._to_response(assessment)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to create assessment: {str(e)}"
            )

    def get_assessment(self, assessment_id: str, user_id: str) -> AssessmentResponse:
        """Get a specific assessment by ID."""
        assessment = self.get_entity_or_404(assessment_id, user_id)
        return self._to_response(assessment)

    def list_assessments(self, user_id: str) -> List[AssessmentResponse]:
        """List all assessments for a user."""
        assessments = self.get_user_entities(user_id)
        return [self._to_response(assessment) for assessment in assessments]

    def update_assessment(
        self, assessment_id: str, user_id: str, data: AssessmentUpdateRequest
    ) -> AssessmentResponse:
        """Update an existing assessment."""
        assessment = self.get_entity_or_404(assessment_id, user_id)

        try:
            # Update only provided fields
            if data.product_name is not None:
                assessment.product_name = data.product_name

            if data.product_description is not None:
                assessment.product_description = data.product_description

            if data.status is not None:
                assessment.update_status(data.status)
            else:
                assessment.save()

            return self._to_response(assessment)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to update assessment: {str(e)}"
            )

    def delete_assessment(self, assessment_id: str, user_id: str) -> None:
        """Delete an assessment and all associated controls and evidence."""
        assessment = self.get_entity_or_404(assessment_id, user_id)

        try:
            # Get all controls for this assessment
            controls = Control.get_by_assessment(assessment_id)

            # Delete all evidence for each control
            for control in controls:
                evidence_list = Evidence.get_by_control(control.control_id)
                for evidence in evidence_list:
                    evidence.delete()

            # Delete all controls
            for control in controls:
                control.delete()

            # Finally delete the assessment
            assessment.delete()
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to delete assessment: {str(e)}"
            )

    def _to_response(self, assessment: SecurityAssessment) -> AssessmentResponse:
        """Convert assessment model to response schema."""
        return AssessmentResponse(
            assessment_id=assessment.assessment_id,
            owner_id=assessment.owner_id,
            product_name=assessment.product_name,
            product_description=assessment.product_description,
            status=assessment.status,
            created_at=assessment.created_at,
            updated_at=assessment.updated_at,
        )
