"""Text processing utilities."""


def split_text(text: str, delimiter: str = " ") -> list[str]:
    """Split text by delimiter."""
    if not text:
        return []
    return [part.strip() for part in text.split(delimiter) if part.strip()]


def clean_text(text: str) -> str:
    """Clean and normalize text."""
    if not text:
        return ""
    return text.strip().replace("\n", " ").replace("\r", "")
