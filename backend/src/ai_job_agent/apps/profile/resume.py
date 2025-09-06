from pypdf import PdfReader

BASIC_SKILLS = {
    "python","fastapi","langchain","langgraph","crewai","streamlit",
    "aws","gcp","azure","docker","kubernetes","sql","nosql","mongodb","postgres",
    "react","node","typescript","rest","graphql","ml","nlp","llm","gemini","openai",
}

def extract_text_from_pdf(path: str) -> str:
    r = PdfReader(path)
    return "\n".join([p.extract_text() or "" for p in r.pages])

def guess_skills(text: str) -> list[str]:
    low = (text or "").lower()
    return sorted({s for s in BASIC_SKILLS if s in low})

def token_count(text: str) -> int:
    return max(1, len((text or "").split()))
