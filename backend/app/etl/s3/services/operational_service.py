# services/operational_service.py

from typing import List, Dict, Optional
from app.etl.s3.utils.s3_paths import domain_lookup_key, auditor_master_key


class OperationalService:

    def __init__(self, s3):
        self.s3 = s3

    # 🔹 A. Get org_id from domain
    def get_org_by_domain(self, domain: str) -> Optional[str]:
        data = self.s3.read_json(domain_lookup_key(domain))
        if not data:
            return None
        return data.get("org_id")

    # 🔹 B. Get all auditors
    def get_auditors(self) -> List[Dict]:
        data = self.s3.read_json(auditor_master_key())
        return data if data else []

    # 🔹 C. Assign org to auditor
    def assign_org(self, auditor_id: str, org_id: str) -> Dict:
        auditors = self.get_auditors()

        if not auditors:
            raise ValueError("Auditor master is empty")

        updated = False

        for auditor in auditors:
            if auditor.get("auditor_id") == auditor_id:

                # Ensure organizations field exists
                if "organizations" not in auditor:
                    auditor["organizations"] = []

                # Avoid duplicates
                if org_id not in auditor["organizations"]:
                    auditor["organizations"].append(org_id)

                updated = True
                break

        if not updated:
            raise ValueError(f"Auditor {auditor_id} not found")

        self.s3.write_json(auditor_master_key(), auditors)

        return {
            "status": "success",
            "auditor_id": auditor_id,
            "org_id": org_id
        }