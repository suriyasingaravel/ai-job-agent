import json, os, uuid
from typing import Dict, Any
from ai_job_agent.apps.api.settings import settings

PROFILE_PATH = os.path.join(settings.data_dir, "profiles.json")
os.makedirs(settings.data_dir, exist_ok=True)
if not os.path.exists(PROFILE_PATH):
    with open(PROFILE_PATH,"w",encoding="utf-8") as f: f.write("{}")

def _load() -> Dict[str, Any]:
    with open(PROFILE_PATH,"r",encoding="utf-8") as f:
        return json.load(f)

def _save(data: Dict[str, Any]):
    with open(PROFILE_PATH,"w",encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def upsert_profile(p: Dict[str, Any]) -> str:
    data = _load()
    pid = p.get("id") or str(uuid.uuid4())
    p["id"] = pid
    data[pid] = p
    _save(data)
    return pid

def get_profile(pid: str) -> Dict[str, Any] | None:
    return _load().get(pid)
