"""Evidence service layer for business logic and data operations."""

from typing import List
from fastapi import HTTPException
from app.database.models.evidence import Evidence
from app.database.models.controls import Control
from app.database.models.assessments import SecurityAssessment
from app.assessments.base import BaseService
from app.evidence.validation import (
    EvidenceCreateRequest,
    EvidenceUpdateRequest,
    EvidenceResponse,
)


class EvidenceService(BaseService[Evidence]):
    """Service class for evidence CRUD operations."""

    def __init__(self):
        super().__init__(Evidence)

    def validate_ownership(self, entity: Evidence, user_id: str) -> bool:
        """Validate that the user owns the assessment containing the evidence."""
        try:
            # Get control that this evidence belongs to
            control = Control.get(entity.control_id)
            # Get assessment that the control belongs to
            assessment = SecurityAssessment.get(control.assessment_id)
            return assessment.is_owner(user_id)
        except (Control.DoesNotExist, SecurityAssessment.DoesNotExist):
            return False

    def get_user_entities(self, user_id: str) -> List[Evidence]:
        """Get all evidence belonging to user's assessments."""
        try:
            # Get all user's assessments
            user_assessments = SecurityAssessment.get_by_owner(user_id)
            all_evidence = []

            for assessment in user_assessments:
                # Get all controls for this assessment
                controls = Control.get_by_assessment(assessment.assessment_id)
                for control in controls:
                    # Get evidence for each control
                    evidence_list = Evidence.get_by_control(control.control_id)
                    all_evidence.extend(evidence_list)

            return all_evidence
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve evidence: {str(e)}"
            )

    def validate_control_access(self, control_id: str, user_id: str) -> Control:
        """Validate that user has access to the control and return it."""
        try:
            control = Control.get(control_id)
            assessment = SecurityAssessment.get(control.assessment_id)
            if not assessment.is_owner(user_id):
                raise HTTPException(status_code=403, detail="Access denied to control")
            return control
        except Control.DoesNotExist:
            raise HTTPException(status_code=404, detail="Control not found")
        except SecurityAssessment.DoesNotExist:
            raise HTTPException(status_code=404, detail="Assessment not found")

    def create_evidence(
        self, control_id: str, user_id: str, data: EvidenceCreateRequest
    ) -> EvidenceResponse:
        """Create new evidence."""
        # Validate control access
        self.validate_control_access(control_id, user_id)

        try:
            evidence = Evidence.create_evidence(
                control_id=control_id,
                title=data.title,
                description=data.description,
                evidence_type=data.evidence_type,
            )
            return self._to_response(evidence)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to create evidence: {str(e)}"
            )

    def get_evidence(self, evidence_id: str, user_id: str) -> EvidenceResponse:
        """Get a specific evidence by ID."""
        evidence = self.get_entity_or_404(evidence_id, user_id)
        return self._to_response(evidence)

    def list_evidence_by_control(
        self, control_id: str, user_id: str
    ) -> List[EvidenceResponse]:
        """List all evidence for a specific control."""
        # Validate control access
        self.validate_control_access(control_id, user_id)

        try:
            evidence_list = Evidence.get_by_control(control_id)
            return [self._to_response(evidence) for evidence in evidence_list]
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to retrieve evidence: {str(e)}"
            )

    def update_evidence(
        self, evidence_id: str, user_id: str, data: EvidenceUpdateRequest
    ) -> EvidenceResponse:
        """Update existing evidence."""
        evidence = self.get_entity_or_404(evidence_id, user_id)

        try:
            # Update only provided fields
            if data.title is not None:
                evidence.title = data.title

            if data.description is not None:
                evidence.description = data.description

            if data.evidence_type is not None:
                evidence.evidence_type = data.evidence_type

            evidence.save()
            return self._to_response(evidence)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to update evidence: {str(e)}"
            )

    def delete_evidence(self, evidence_id: str, user_id: str) -> None:
        """Delete evidence."""
        evidence = self.get_entity_or_404(evidence_id, user_id)

        try:
            # TODO: If evidence has a file, delete it from S3 storage
            evidence.delete()
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to delete evidence: {str(e)}"
            )

    def get_control_and_assessment_info(self, control_id: str, user_id: str) -> tuple:
        """Get control and assessment information for context."""
        control = self.validate_control_access(control_id, user_id)
        try:
            assessment = SecurityAssessment.get(control.assessment_id)
            return control, assessment
        except SecurityAssessment.DoesNotExist:
            raise HTTPException(status_code=404, detail="Assessment not found")

    def _to_response(self, evidence: Evidence) -> EvidenceResponse:
        """Convert evidence model to response schema."""
        return EvidenceResponse(
            evidence_id=evidence.evidence_id,
            control_id=evidence.control_id,
            title=evidence.title,
            description=evidence.description,
            evidence_type=evidence.evidence_type,
            file_url=evidence.file_url,
            has_file=evidence.has_file(),
            created_at=evidence.created_at,
            updated_at=evidence.updated_at,
        )
