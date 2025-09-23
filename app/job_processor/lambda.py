"""Lambda function for processing evidence collection SQS messages."""

import json
import logging
from typing import Dict, Any

from app.database.models.evidence import Evidence
from app.database.models.job_executions import JobExecution
from app.database.models.job_templates import JobTemplate
from lambda_functions.aws_config_service import AWSConfigService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for processing evidence collection SQS messages.

    Args:
        event: Lambda event containing SQS message(s)
        context: Lambda context object

    Returns:
        Processing results
    """
    logger.info(f"Processing evidence collection event: {json.dumps(event)}")

    results = []
    errors = []

    # Process each SQS record
    for record in event.get("Records", []):
        try:
            result = process_sqs_record(record)
            results.append(result)
        except Exception as e:
            error_msg = f"Failed to process record {record.get('messageId', 'unknown')}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

    return {
        "statusCode": 200,
        "processed_count": len(results),
        "error_count": len(errors),
        "results": results,
        "errors": errors,
    }


def process_sqs_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single SQS record for evidence collection.

    Args:
        record: SQS record from the event

    Returns:
        Processing result
    """
    # Parse the SQS message
    message_body = json.loads(record["body"])
    message_id = record.get("messageId", "unknown")

    logger.info(f"Processing message {message_id}: {message_body}")

    # Extract required fields
    control_id = message_body.get("control_id")
    evidence_id = message_body.get("evidence_id")

    if not all([control_id, evidence_id]):
        raise ValueError(f"Missing required fields in message: {message_body}")

    # Process the evidence
    return process_evidence_collection(evidence_id, control_id, message_id)


def process_evidence_collection(
    evidence_id: str, control_id: str, message_id: str
) -> Dict[str, Any]:
    """
    Process evidence collection for automated evidence.

    Args:
        evidence_id: ID of the evidence to process
        control_id: ID of the control (for validation)
        message_id: SQS message ID for tracking

    Returns:
        Processing result
    """
    logger.info(f"Processing evidence collection for evidence {evidence_id}")
    execution = None

    try:
        # Retrieve evidence record and check it belongs to the control
        evidence = Evidence.get(evidence_id)
        if evidence.control_id != control_id:
            raise ValueError(
                f"Evidence {evidence_id} does not belong to control {control_id}"
            )

        if not evidence.job_template_id:
            raise ValueError(f"Evidence {evidence_id} has no job template ID")

        if not evidence.aws_account_id:
            raise ValueError(f"Evidence {evidence_id} has no AWS account ID")

        # Create new execution
        job_template = JobTemplate.get(evidence.job_template_id)
        execution = JobExecution.create_execution(
            template_id=job_template.template_id,
            evidence_id=evidence_id,
            aws_account_id=evidence.aws_account_id,
        )
        execution.start_execution("lambda-job-processor")

        # Process based on scan type
        # TODO: Add support for more scan types
        scan_type = job_template.scan_type
        if scan_type == "aws_config":
            results = process_aws_config_scan(job_template, execution)
        else:
            raise ValueError(f"Unsupported scan type: {scan_type}")

        # Update execution with results
        execution.set_aws_config_compliance_results(results)
        execution.complete_execution(results)

        logger.info(f"Successfully processed evidence {evidence_id}")

        return {
            "evidence_id": evidence_id,
            "execution_id": execution.execution_id,
            "scan_type": scan_type,
            "status": "completed",
            "rules_scanned": results.get("rules_scanned", []),
            "compliance_summary": results.get("compliance_summary", {}),
        }

    except Exception as e:
        error_msg = f"Evidence processing failed: {str(e)}"
        logger.error(error_msg)
        try:
            if execution:
                execution.fail_execution(error_msg)
        except Exception as update_error:
            logger.error(f"Failed to update execution status: {update_error}")
        raise


def process_aws_config_scan(
    job_template: JobTemplate, execution: JobExecution
) -> Dict[str, Any]:
    """
    Process AWS Config scan based on job template configuration.

    Args:
        job_template: Job template with AWS Config configuration
        execution: Job execution record to update

    Returns:
        Scan results
    """
    logger.info(f"Processing AWS Config scan for template {job_template.template_id}")

    config = job_template.config.as_dict()
    if not config:
        raise ValueError("Job template has no configuration")

    iam_role_arn = (
        f"arn:aws:iam::{execution.aws_account_id}:role/compass-aws-config-job"
    )
    rule_names = config.get("rule_names", None)
    region = config.get("region", "ca-central-1")

    if not rule_names:
        raise ValueError("Job template configuration missing rule_names")

    config_service = AWSConfigService(role_arn=iam_role_arn, region=region)
    results = config_service.scan_config_compliance(rule_names)

    results["scan_metadata"] = {
        "template_id": job_template.template_id,
        "execution_id": execution.execution_id,
        "region": region,
        "rule_names": rule_names,
        "iam_role_arn": iam_role_arn,
    }

    logger.info(
        f"AWS Config scan completed: {results['compliance_summary']['compliant']} compliant, "
        f"{results['compliance_summary']['non_compliant']} non-compliant rules"
    )

    return results
