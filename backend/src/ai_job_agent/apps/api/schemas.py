from typing import List, Optional
from pydantic import BaseModel, HttpUrl

class HealthResponse(BaseModel):
    status: str
    data_dir: str

class ProfileIn(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    years_experience: Optional[float] = None
    locations: List[str] = []
    roles: List[str] = []
    skills: List[str] = []
    portals: List[str] = ["linkedin","naukri","indeed","hirist","timesjobs","talentoindia"]
    resume_text: Optional[str] = None

class ProfileOut(ProfileIn):
    id: str

class UploadResponse(BaseModel):
    ok: bool
    tokens: int
    extracted_skills: List[str]
    profile_id: str

class JobHit(BaseModel):
    title: str
    company: str = ""
    location: Optional[str] = None
    url: Optional[str] = None
    portal: Optional[str] = None
    snippet: Optional[str] = None
    score: float

class SearchRequest(BaseModel):
    max_results: int = 20

class SearchResponse(BaseModel):
    hits: List[JobHit]

class ContactInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    linkedin: Optional[HttpUrl] = None
    company: Optional[str] = None
    title: Optional[str] = None
    found: bool = False

# ---------- NEW: Enrichment payload ----------

class EnrichQuery(BaseModel):
    # All optional so UI can pass either company OR urls
    company: Optional[str] = None
    job_title: Optional[str] = None
    job_url: Optional[str] = None         # keep as str for leniency
    linkedin_url: Optional[str] = None    # HR/Recruiter LinkedIn URL

class EnrichRequest(BaseModel):
    job: JobHit
    profile_id: Optional[str] = None
    query: Optional[EnrichQuery] = None

# Endpoint can return the found contact
class EnrichResponse(ContactInfo):
    pass

# ---------- Compose & pipeline ----------

class ComposeRequest(BaseModel):
    job: JobHit
    contact: Optional[ContactInfo] = None
    profile_id: str

class ComposeResponse(BaseModel):
    subject: str
    body: str

class PipelineRequest(BaseModel):
    profile_id: str
    portals: List[str]
    max_results: int = 20
