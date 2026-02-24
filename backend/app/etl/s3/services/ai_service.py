# services/ai_service.py

from datetime import datetime
from typing import Dict, Optional
from app.etl.s3.utils.s3_paths import ai_key


class AIService:

    def __init__(self, s3, llm):
        self.s3 = s3
        self.llm = llm

    def process_org(
        self,
        org_id: str,
        audit_id: str,
        question_id: Optional[str] = None
    ) -> Dict:

        prefix = f"organizations/{org_id}/audits/{audit_id}/current/answers/"

        processed = 0
        skipped = 0
        failed = 0

        continuation_token = None

        while True:
            params = {
                "Bucket": self.s3.bucket,
                "Prefix": prefix
            }

            if continuation_token:
                params["ContinuationToken"] = continuation_token

            response = self.s3.client.list_objects_v2(**params)

            for obj in response.get("Contents", []):
                answer = self.s3.read_json(obj["Key"])

                if not answer:
                    skipped += 1
                    continue

                qid = answer.get("question_id")

                # 🔹 Filter by specific question if provided
                if question_id and qid != question_id:
                    continue

                # 🔹 Only process submitted answers
                if answer.get("state") != "submitted":
                    skipped += 1
                    continue

                version = answer.get("version", 0)

                # 🔹 Fetch existing AI result
                ai = self.s3.read_json(
                    ai_key(org_id, audit_id, qid)
                )

                if ai and ai.get("last_analyzed_version", 0) >= version:
                    skipped += 1
                    continue

                try:
                    # 🔹 Call LLM
                    result = self.llm.analyze(answer.get("answer", ""))

                    if not isinstance(result, dict):
                        raise ValueError("Invalid AI response format")

                    ai_data = {
                        "question_id": qid,
                        "last_analyzed_version": version,
                        "analyzed_at": datetime.utcnow().isoformat(),
                        **result
                    }

                    self.s3.write_json(
                        ai_key(org_id, audit_id, qid),
                        ai_data
                    )

                    processed += 1

                except Exception as e:
                    failed += 1
                    # Optional: log error
                    print(f"[AI ERROR] {qid}: {str(e)}")

            if response.get("IsTruncated"):
                continuation_token = response.get("NextContinuationToken")
            else:
                break

        return {
            "processed": processed,
            "skipped": skipped,
            "failed": failed
        }