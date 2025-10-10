"""Common database operations and access patterns."""

from typing import Dict, List, Optional

from app.database.models import Control, Evidence, SecurityAssessment, User


class DatabaseOperations:
    """High-level database operations implementing common access patterns."""

    @staticmethod
    def get_user_by_google_id(google_id: str) -> Optional[User]:
        """Get user by Google ID (primary access pattern #1)."""
        return User.get_by_google_id(google_id)

    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """Get user by email (primary access pattern #2)."""
        return User.get_by_email(email)

    @staticmethod
    def get_user_assessments(user_id: str) -> List[SecurityAssessment]:
        """Get user's owned assessments (primary access pattern #3)."""
        return SecurityAssessment.get_by_owner(user_id)

    @staticmethod
    def check_user_assessment_access(user_id: str, assessment_id: str) -> bool:
        """Check user ownership of assessment (primary access pattern #4)."""
        try:
            assessment = SecurityAssessment.get(assessment_id)
            return assessment.is_owner(user_id)
        except SecurityAssessment.DoesNotExist:
            return False

    @staticmethod
    def get_assessment_controls(assessment_id: str) -> List[Control]:
        """Get assessment controls (primary access pattern #5)."""
        return Control.get_by_assessment(assessment_id)

    @staticmethod
    def get_control_evidence(control_id: str) -> List[Evidence]:
        """Get control evidence (primary access pattern #6)."""
        return Evidence.get_by_control(control_id)

    @staticmethod
    def get_assessments_by_status(status: str) -> List[SecurityAssessment]:
        """Get all assessments with status (secondary access pattern #7)."""
        return [
            assessment
            for assessment in SecurityAssessment.scan()
            if assessment.status == status
        ]

    @staticmethod
    def get_controls_by_nist_id(nist_control_id: str) -> List[Control]:
        """Get controls by NIST ID (secondary access pattern #8)."""
        return [
            control
            for control in Control.scan()
            if control.nist_control_id == nist_control_id
        ]

    @staticmethod
    def get_recent_evidence_for_control(
        control_id: str, limit: int = 10
    ) -> List[Evidence]:
        """Get recent evidence (secondary access pattern #9)."""
        return Evidence.get_recent_evidence(control_id, limit)

    @staticmethod
    def create_user_and_assessment(
        google_id: str,
        email: str,
        name: str,
        product_name: str,
        product_description: str,
    ) -> Dict[str, object]:
        """Create a new user and their first assessment."""
        # Check if user already exists
        existing_user = User.get_by_google_id(google_id)
        if existing_user:
            user = existing_user
        else:
            user = User.create_user(google_id, email, name)

        # Create assessment
        assessment = SecurityAssessment.create_assessment(
            creator_id=google_id,
            product_name=product_name,
            product_description=product_description,
        )

        return {"user": user, "assessment": assessment}

    @staticmethod
    def get_assessment_summary(
        assessment_id: str, user_id: str
    ) -> Optional[Dict[str, object]]:
        """Get comprehensive assessment summary with access check."""
        # Check access first
        if not DatabaseOperations.check_user_assessment_access(user_id, assessment_id):
            return None

        try:
            assessment = SecurityAssessment.get(assessment_id)
            controls = DatabaseOperations.get_assessment_controls(assessment_id)

            # Get evidence count for each control
            controls_with_evidence = []
            for control in controls:
                evidence = DatabaseOperations.get_control_evidence(control.control_id)
                controls_with_evidence.append(
                    {"control": control, "evidence_count": len(evidence)}
                )

            # Calculate status summary
            status_counts = {"not_started": 0, "partial": 0, "implemented": 0}
            for control in controls:
                if control.implementation_status in status_counts:
                    status_counts[control.implementation_status] += 1

            return {
                "assessment": assessment,
                "controls": controls_with_evidence,
                "total_controls": len(controls),
                "status_summary": status_counts,
                "completion_percentage": (
                    (status_counts["implemented"] / len(controls) * 100)
                    if controls
                    else 0
                ),
            }
        except SecurityAssessment.DoesNotExist:
            return None

    @staticmethod
    def add_control_with_evidence(
        assessment_id: str,
        user_id: str,
        nist_control_id: str,
        control_title: str,
        control_description: str,
        evidence_items: Optional[List[Dict[str, str]]] = None,
    ) -> Optional[Dict[str, object]]:
        """Add a control with optional evidence to an assessment."""
        # Check access
        if not DatabaseOperations.check_user_assessment_access(user_id, assessment_id):
            return None

        # Create control
        control = Control.create_control(
            assessment_id=assessment_id,
            nist_control_id=nist_control_id,
            control_title=control_title,
            control_description=control_description,
        )

        # Add evidence if provided
        evidence_objects = []
        if evidence_items:
            for evidence_item in evidence_items:
                evidence = Evidence.create_evidence(
                    control_id=control.control_id,
                    title=evidence_item.get("title", ""),
                    description=evidence_item.get("description", ""),
                    evidence_type=evidence_item.get("evidence_type", "document"),
                )
                evidence_objects.append(evidence)

        return {"control": control, "evidence": evidence_objects}

    @staticmethod
    def initialize_tables() -> None:
        """Initialize all database tables if they don't exist."""
        import logging

        logger = logging.getLogger(__name__)
        models = [User, SecurityAssessment, Control, Evidence]

        for model in models:
            try:
                if model.create_table_if_not_exists():
                    logger.info(f"Created table: {model.get_table_name()}")
                else:
                    logger.info(f"Table already exists: {model.describe_table()}")
            except Exception as e:
                logger.error(
                    f"Failed to initialize table {model.get_table_name()}: {e}"
                )
                raise
