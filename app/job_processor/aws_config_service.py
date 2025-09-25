"""AWS Config service for scanning configuration rules and compliance status."""

import logging
from typing import Dict, List, Optional, Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.job_processor.constants import (
    empty_compliance_summary,
    AwsComplianceType,
    AwsComplianceSummary,
)

logger = logging.getLogger(__name__)


class AWSConfigService:
    """Service for interacting with AWS Config service."""

    def __init__(
        self, role_arn: Optional[str] = None, region: str = "ca-central-1"
    ) -> None:
        """
        Initialize AWS Config service.

        Args:
            role_arn: IAM role ARN to assume for cross-account access
            region: AWS region to scan
        """
        self.region = region
        self.role_arn = role_arn
        self.config_client = self._create_config_client()

    def _create_config_client(self):
        """Create AWS Config client with optional role assumption."""
        session = boto3.Session()

        if self.role_arn:
            try:
                # Assume the specified IAM role
                sts_client = session.client("sts", region_name=self.region)
                assumed_role = sts_client.assume_role(
                    RoleArn=self.role_arn, RoleSessionName="CompassAWSConfigJob"
                )

                credentials = assumed_role["Credentials"]
                session = boto3.Session(
                    aws_access_key_id=credentials["AccessKeyId"],
                    aws_secret_access_key=credentials["SecretAccessKey"],
                    aws_session_token=credentials["SessionToken"],
                )
                logger.info(f"Assumed role {self.role_arn} for Config access")
            except (BotoCoreError, ClientError) as e:
                logger.error(f"Failed to assume role {self.role_arn}: {e}")
                raise

        return session.client("config", region_name=self.region)

    def get_all_config_rules(self) -> List[Dict[str, Any]]:
        """
        Get all AWS Config rules in the account.

        Returns:
            List of config rule dictionaries
        """
        try:
            rules = []
            paginator = self.config_client.get_paginator("describe_config_rules")

            for page in paginator.paginate():
                rules.extend(page.get("ConfigRules", []))

            logger.info(f"Retrieved {len(rules)} Config rules")
            return rules

        except (BotoCoreError, ClientError) as e:
            logger.error(f"Failed to retrieve Config rules: {e}")
            raise

    def filter_rules_by_prefixes(
        self, rules: List[Dict[str, Any]], rule_prefixes: List[str]
    ) -> List[str]:
        """
        Filter config rules by name prefixes.

        Args:
            rules: List of config rule dictionaries
            rule_prefixes: List of rule name prefixes to match

        Returns:
            List of rule names that match the prefixes
        """
        matching_rules = []

        for rule in rules:
            rule_name = rule.get("ConfigRuleName", "")
            for prefix in rule_prefixes:
                if rule_name.startswith(prefix):
                    matching_rules.append(rule_name)
                    break

        logger.info(
            f"Filtered {len(matching_rules)} rules from {len(rules)} total rules "
            f"using prefixes: {rule_prefixes}"
        )
        return matching_rules

    def get_compliance_for_config_rules(
        self, rule_names: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get compliance status for multiple config rules.

        Args:
            rule_names: List of config rule names

        Returns:
            Dictionary mapping rule names to compliance status
        """
        compliance_results = {}

        try:
            response = self.config_client.describe_compliance_by_config_rule(
                ConfigRuleNames=rule_names
            )

            compliance_by_rules = response.get("ComplianceByConfigRules", [])

            # Process the compliance results
            for compliance_info in compliance_by_rules:
                rule_name = compliance_info.get("ConfigRuleName")
                compliance_results[rule_name] = {
                    "config_rule_name": rule_name,
                    "compliance_type": compliance_info.get("Compliance", {}).get(
                        "ComplianceType"
                    ),
                    "compliance_contributor_count": compliance_info.get(
                        "Compliance", {}
                    ).get("ComplianceContributorCount", {}),
                }

            # Handle rules that weren't returned (no compliance data)
            returned_rule_names = {
                result.get("ConfigRuleName") for result in compliance_by_rules
            }
            for rule_name in rule_names:
                if rule_name not in returned_rule_names:
                    compliance_results[rule_name] = {
                        "config_rule_name": rule_name,
                        "compliance_type": "INSUFFICIENT_DATA",
                        "compliance_contributor_count": {},
                    }

        except (BotoCoreError, ClientError) as e:
            logger.warning(f"Failed to get compliance for rules {rule_names}: {e}")
            # If the entire call fails, mark all rules as error
            for rule_name in rule_names:
                compliance_results[rule_name] = {
                    "config_rule_name": rule_name,
                    "compliance_type": "ERROR",
                    "error": str(e),
                }

        logger.info(f"Retrieved compliance status for {len(compliance_results)} rules")
        return compliance_results

    def scan_config_compliance(self, rule_prefixes: List[str]) -> Dict[str, Any]:
        """
        Perform a complete AWS Config compliance scan.

        Args:
            rule_prefixes: List of rule name prefixes to filter by

        Returns:
            Dictionary containing scan results and compliance summary
        """
        try:
            # Get all config rules
            all_rules = self.get_all_config_rules()

            # Filter rules by prefixes
            matching_rule_names = self.filter_rules_by_prefixes(
                all_rules, rule_prefixes
            )

            if not matching_rule_names:
                logger.warning(f"No rules found matching prefixes: {rule_prefixes}")
                return {
                    "rules_scanned": [],
                    "compliance_summary": empty_compliance_summary(),
                    "rule_details": {},
                }

            # Get compliance status for matching rules
            compliance_results = self.get_compliance_for_config_rules(
                matching_rule_names
            )

            # Generate summary using uppercase AWS compliance types as keys.
            summary: AwsComplianceSummary = empty_compliance_summary()

            for rule_compliance in compliance_results.values():
                compliance_type_raw: str = rule_compliance.get(
                    "compliance_type", AwsComplianceType.ERROR.value
                )
                try:
                    compliance_enum = AwsComplianceType(compliance_type_raw)
                except ValueError:
                    compliance_enum = AwsComplianceType.ERROR
                summary[compliance_enum] = summary[compliance_enum] + 1

            return {
                "rules_scanned": matching_rule_names,
                "compliance_summary": summary,
                "rule_details": compliance_results,
            }

        except Exception as e:
            logger.error(f"AWS Config compliance scan failed: {e}")
            raise
