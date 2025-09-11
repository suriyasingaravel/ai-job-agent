import os
import requests
import streamlit as st
from urllib.parse import urljoin

# ---------- Config ----------
DEFAULT_API = os.getenv("API_URL", "https://ai-job-hunt-agent-backend.onrender.com")
st.set_page_config(page_title="AI Job Agent", layout="wide")
st.title("AI Job Agent — Gemini + FastAPI Demo")

def api(base: str, path: str) -> str:
    """Safe join that avoids double slashes."""
    return urljoin(base if base.endswith("/") else base + "/", path.lstrip("/"))

with st.sidebar:
    st.subheader("Settings")
    API_URL = st.text_input("API URL", value=DEFAULT_API)
    st.caption("Endpoints: /health, /upload_resume, /profile/set, /search_jobs, /compose, /pipeline/run, /contact/enrich")

# ---------- Health ----------
col1, col2 = st.columns(2)
with col1:
    if st.button("Ping /health"):
        try:
            r = requests.get(api(API_URL, "/health"), timeout=10)
            st.json(r.json())
        except Exception as e:
            st.error(str(e))

# ---------- Profile ----------
st.header("1) Candidate Profile")
with st.expander("Set profile"):
    name = st.text_input("Name", "")
    email = st.text_input("Email", "")
    phone = st.text_input("Phone", "")
    years = st.number_input("Years Experience", min_value=0.0, max_value=50.0, value=2.0, step=0.5)
    roles = st.text_input("Target Roles (comma)", "Fullstack Developer, Backend Engineer")
    skills = st.text_input("Skills (comma)", "Python, FastAPI, LangChain, Streamlit, React")
    locations = st.text_input("Locations (comma)", "Bengaluru, Remote")
    portals = st.multiselect(
        "Job Portals",
        ["linkedin", "naukri", "indeed", "hirist", "timesjobs", "talentoindia"],
        default=["linkedin", "indeed", "naukri"],
    )

    if st.button("Save Profile"):
        payload = {
            "name": name,
            "email": email,
            "phone": phone,
            "years_experience": years,
            "roles": [r.strip() for r in roles.split(",") if r.strip()],
            "skills": [s.strip() for s in skills.split(",") if s.strip()],
            "locations": [l.strip() for l in locations.split(",") if l.strip()],
            "portals": portals,
        }
        try:
            r = requests.post(api(API_URL, "/profile/set"), json=payload, timeout=20)
            if r.ok:
                st.session_state["profile"] = r.json()
                st.success("Profile saved")
                st.json(st.session_state["profile"])
            else:
                st.error(r.text)
        except Exception as e:
            st.error(str(e))

# ---------- Resume ----------
st.header("2) Upload Resume (PDF)")
file = st.file_uploader("Upload your PDF resume", type=["pdf"])
if st.button("Upload Resume") and file:
    try:
        with st.spinner("Uploading & parsing resume..."):
            files = {"file": (file.name, file.getvalue(), "application/pdf")}
            r = requests.post(api(API_URL, "/upload_resume"), files=files, timeout=60)
        if r.ok:
            st.session_state["resume"] = r.json()
            st.success("Resume uploaded")
            st.json(st.session_state["resume"])
        else:
            st.error(r.text)
    except Exception as e:
        st.error(str(e))

# ---------- Search ----------
st.header("3) Search Jobs")
max_results = st.slider("Max Results", 5, 50, 20)
if st.button("Search"):
    prof = st.session_state.get("profile") or st.session_state.get("resume")
    if not prof:
        st.warning("Set profile or upload resume first.")
    else:
        try:
            with st.spinner("Searching portals..."):
                pid = prof.get("id") or prof.get("profile_id")
                r = requests.post(
                    api(API_URL, "/search_jobs"),
                    params={"profile_id": pid},
                    json={"max_results": max_results},
                    timeout=60,
                )
            if r.ok:
                st.session_state["hits"] = r.json().get("hits", [])
                st.session_state.pop("contact", None)  # clear previous contact
                for i, h in enumerate(st.session_state["hits"], 1):
                    st.markdown(
                        f"**{i}. {h.get('title','(no title)')}** — {h.get('company','')}  "
                        f"|  `{h.get('portal','')}`  |  score: **{h.get('score','?')}**"
                    )
                    if h.get("snippet"):
                        st.write(h["snippet"])
                    if h.get("url"):
                        st.write(h["url"])
                    st.divider()
            else:
                st.error(r.text)
        except Exception as e:
            st.error(str(e))

# ---------- Compose ----------
st.header("4) Compose Outreach Email")
sel = None
hits = st.session_state.get("hits", [])
if hits:
    options = [f"{i+1}. {h.get('title','')} @ {h.get('company','')}" for i, h in enumerate(hits)]
    idx = st.selectbox("Pick a job", list(range(len(options))), format_func=lambda i: options[i])
    sel = hits[idx]

if sel and st.button("Compose Mail (no contact)"):
    prof = st.session_state.get("profile") or st.session_state.get("resume")
    if not prof:
        st.warning("Set profile or upload resume first.")
    else:
        try:
            with st.spinner("Composing email..."):
                pid = prof.get("id") or prof.get("profile_id")
                payload = {"job": sel, "contact": None, "profile_id": pid}
                r = requests.post(api(API_URL, "/compose"), json=payload, timeout=45)
            if r.ok:
                data = r.json()
                st.subheader("Subject")
                st.write(data.get("subject", ""))
                st.subheader("Body")
                st.code(data.get("body", ""), language="markdown")
            else:
                st.error(r.text)
        except Exception as e:
            st.error(str(e))

# ---------- Recruiter/HR Contact Enrichment ----------
st.header("5) Find Recruiter / HR Contact")
if sel:
    st.caption("Uses backend route: POST /contact/enrich (RocketReach/LinkedIn enrichment)")

    # show company so user can fix/enter it if we didn't scrape one
    default_company = (sel.get("company") or "").strip()
    company_input = st.text_input("Company (required)", value=default_company)

    manual_url = st.text_input(
        "Optional: Paste a job posting URL or an HR LinkedIn URL",
        value=sel.get("url", "")
    )

    if st.button("Find Contact"):
        if not company_input.strip():
            st.warning("Please enter the company name.")
        else:
            prof = st.session_state.get("profile") or st.session_state.get("resume")
            pid = prof.get("id") or prof.get("profile_id") if prof else None

            job_payload = dict(sel)
            if manual_url:
                job_payload["url"] = manual_url

            query = {
                "company": company_input.strip(),           # REQUIRED
                "job_title": (sel.get("title") or "").strip() or None,
                "job_url": manual_url or sel.get("url") or None,
            }
            if "linkedin.com/in/" in (manual_url or "").lower():
                query["linkedin_url"] = manual_url

            query = {k: v for k, v in query.items() if v}

            r = requests.post(
                f"{API_URL}/contact/enrich",
                json={"job": job_payload, "profile_id": pid, "query": query},
                timeout=45,
            )
            if r.ok:
                contact = r.json()
                st.session_state["contact"] = contact
                st.success("Contact found (if available)")
                st.json(contact)
            else:
                st.error(r.text)

    if st.session_state.get("contact") and st.button("Compose Mail (with contact)"):
        prof = st.session_state.get("profile") or st.session_state.get("resume")
        pid = prof.get("id") or prof.get("profile_id") if prof else None
        payload = {"job": sel, "contact": st.session_state["contact"], "profile_id": pid}
        r = requests.post(f"{API_URL}/compose", json=payload, timeout=45)
        if r.ok:
            data = r.json()
            st.subheader("Subject"); st.write(data.get("subject",""))
            st.subheader("Body");    st.code(data.get("body",""), language="markdown")
        else:
            st.error(r.text)
else:
    st.info("Search jobs and select one to enable contact enrichment.")
