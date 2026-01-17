from incident_assistance.safety.router import route_request
from incident_assistance.intake.entity_extraction import extract_entities
from incident_assistance.intake.questioning import generate_next_question
from incident_assistance.intake.summary import summarize_incident
from incident_assistance.responses.empathy import empathetic_response
from incident_assistance.responses.pocso import pocso_message
from incident_assistance.responses.high_risk import high_risk_message


def run_incident_assistance(
    user_text: str,
    history: list,
    user_age: int | None,
    emotions: dict,
    incident_state: dict
):
    mode = route_request(user_text, user_age)

    # Always extract facts
    entities = extract_entities(user_text)
    incident_state.update(entities)

    if mode["mode"] == "HIGH_RISK":
        return high_risk_message(), mode

    if mode["mode"] == "POCSO":
        return pocso_message(), mode

    # NORMAL MODE
    question = generate_next_question(incident_state)
    summary = summarize_incident(incident_state)

    if question:
        return question, mode

    return empathetic_response(
        user_text, summary, history, emotions
    ), mode
