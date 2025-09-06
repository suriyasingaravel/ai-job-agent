def clamp_text(s: str, n: int=1200) -> str:
    s = s or ""
    return s[:n]
