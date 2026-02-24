# services/report_service.py

from typing import List, Dict
from app.etl.s3.utils.s3_paths import ai_key  # optional if needed later


class ReportService:

    def __init__(self, s3):
        self.s3 = s3

    def get_gap_report(self, org_id: str, audit_id: str) -> List[Dict]:
        prefix = f"organizations/{org_id}/audits/{audit_id}/current/ai_analysis/"

        results = []

        continuation_token = None

        while True:
            params = {
                "Bucket": self.s3.bucket,
                "Prefix": prefix
            }

            if continuation_token:
                params["ContinuationToken"] = continuation_token

            response = self.s3.client.list_objects_v2(**params)

            contents = response.get("Contents", [])

            for obj in contents:
                data = self.s3.read_json(obj["Key"])
                if data:
                    results.append(data)

            # Handle pagination
            if response.get("IsTruncated"):
                continuation_token = response.get("NextContinuationToken")
            else:
                break

        # Optional: sort by question_id (useful for UI consistency)
        results.sort(key=lambda x: x.get("question_id", ""))

        return results