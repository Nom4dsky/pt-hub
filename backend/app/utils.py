import re


def slugify(text: str) -> str:
    """'Single-Leg RDL' -> 'single-leg-rdl'"""
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")
