from .intent_detection import (
    detect_murder_confession,
    detect_minor_sexual_abuse
)
from .risk_modes import normal_mode, pocso_mode, high_risk_mode


def route_request(user_text: str, user_age: int | None):
    if detect_murder_confession(user_text):
        return high_risk_mode()

    if detect_minor_sexual_abuse(user_text, user_age):
        return pocso_mode()

    return normal_mode()
