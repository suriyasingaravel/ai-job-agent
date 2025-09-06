import streamlit as st
import requests
import os

API_URL = os.getenv("API_URL","http://127.0.0.1:8000")

st.set_page_config(page_title="AI Job Agent", layout="wide")
st.title("AI Job Agent — Gemini + FastAPI Demo")

with st.sidebar:
    st.subheader("Settings")
    API_URL = st.text_input("API URL", value=API_URL)
    st.caption("Endpoints: /health, /upload_resume, /profile/set, /search_jobs, /compose, /pipeline/run, /contact/enrich")

col1, col2 = st.columns(2)
with col1:
    if st.button("Ping /health"):
        try:
            r = requests.get(f"{API_URL}/health", timeout=10)
            st.json(r.json())
        except Exception as e:
            st.error(str(e))

st.header("1) Candidate Profile")
with st.expander("Set profile"):
    name = st.text_input("Name", "")
    email = st.text_input("Email", "")
    phone = st.text_input("Phone", "")
    years = st.number_input("Years Experience", min_value=0.0, max_value=50.0, value=2.0, step=0.5)
    roles = st.text_input("Target Roles (comma)", "Fullstack Developer, Backend Engineer")
    skills = st.text_input("Skills (comma)", "Python, FastAPI, LangChain, Streamlit, React")
    locations = st.text_input("Locations (comma)", "Bengaluru, Remote")
    portals = st.multiselect("Job Portals", ["linkedin","naukri","indeed","hirist","timesjobs","talentoindia"],
                              default=["linkedin","indeed","naukri"])

    if st.button("Save Profile"):
        payload = {
            "name": name, "email": email, "phone": phone, "years_experience": years,
            "roles": [r.strip() for r in roles.split(",") if r.strip()],
            "skills": [s.strip() for s in skills.split(",") if s.strip()],
            "locations": [l.strip() for l in locations.split(",") if l.strip()],
            "portals": portals
        }
        r = requests.post(f"{API_URL}/profile/set", json=payload, timeout=20)
        if r.ok:
            st.session_state["profile"] = r.json()
            st.success("Profile saved")
            st.json(st.session_state["profile"])
        else:
            st.error(r.text)

st.header("2) Upload Resume (PDF)")
file = st.file_uploader("Upload your PDF resume", type=["pdf"])
if st.button("Upload Resume") and file:
    files = {"file": (file.name, file.getvalue(), "application/pdf")}
    r = requests.post(f"{API_URL}/upload_resume", files=files, timeout=60)
    if r.ok:
        st.session_state["resume"] = r.json()
        st.success("Resume uploaded")
        st.json(st.session_state["resume"])
    else:
        st.error(r.text)

st.header("3) Search Jobs")
max_results = st.slider("Max Results", 5, 50, 20)
if st.button("Search"):
    prof = st.session_state.get("profile") or st.session_state.get("resume")
    if not prof:
        st.warning("Set profile or upload resume first.")
    else:
        pid = prof.get("id") or prof.get("profile_id")
        r = requests.post(f"{API_URL}/search_jobs", params={"profile_id": pid}, json={"max_results": max_results}, timeout=60)
        if r.ok:
            st.session_state["hits"] = r.json()["hits"]
            for i, h in enumerate(st.session_state["hits"], 1):
                st.markdown(f"**{i}. {h['title']}** — {h.get('company','')}  |  `{h['portal']}`  |  score: **{h['score']}**")
                if h.get("snippet"):
                    st.write(h["snippet"])
                if h.get("url"):
                    st.write(h["url"])
                st.divider()
        else:
            st.error(r.text)

st.header("4) Compose Outreach Email")
sel = None
hits = st.session_state.get("hits", [])
if hits:
    options = [f"{i+1}. {h['title']} @ {h.get('company','')}" for i,h in enumerate(hits)]
    idx = st.selectbox("Pick a job", list(range(len(options))), format_func=lambda i: options[i])
    sel = hits[idx]

if sel and st.button("Compose Mail"):
    prof = st.session_state.get("profile") or st.session_state.get("resume")
    pid = prof.get("id") or prof.get("profile_id")
    payload = {"job": sel, "contact": None, "profile_id": pid}
    r = requests.post(f"{API_URL}/compose", json=payload, timeout=45)
    if r.ok:
        data = r.json()
        st.subheader("Subject")
        st.write(data["subject"])
        st.subheader("Body")
        st.code(data["body"])
    else:
        st.error(r.text)
