def detect_murder_confession(text: str) -> bool:
    keywords = [
        "i killed", "i murdered", "i stabbed",
        "i shot", "i strangled", "i buried the body"
    ]
    text = text.lower()
    return any(k in text for k in keywords)


def detect_minor_sexual_abuse(text: str, user_age: int | None) -> bool:
    if user_age is None or user_age >= 18:
        return False

    abuse_terms = [
        "molested", "touched me", "rape",
        "sexual abuse", "forced me", "uncle touched"
    ]
    text = text.lower()
    return any(t in text for t in abuse_terms)
