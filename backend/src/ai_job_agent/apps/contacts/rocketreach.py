from typing import Optional, Dict, Any
import requests
from ai_job_agent.apps.api.settings import settings

# Placeholder – replace with your plan's correct RocketReach endpoint & params.
BASE = "https://api.rocketreach.co/v2/api/lookupProfile"

def lookup_hr(company: str, role_hint: str="recruiter") -> Optional[Dict[str, Any]]:
    if not settings.rocketreach_api_key:
        return None
    params = {
        "api_key": settings.rocketreach_api_key,
        "company": company,
        "current_title": role_hint
    }
    try:
        r = requests.get(BASE, params=params, timeout=20)
        if r.status_code != 200:
            return None
        data = r.json()
        return {
            "found": True,
            "name": data.get("name"),
            "email": data.get("email"),
            "linkedin": data.get("linkedin_url"),
            "company": company,
            "title": data.get("current_title")
        }
    except Exception:
        return None
