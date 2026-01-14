INCIDENT_TEMPLATE = {
    "suspect": None,
    "relationship_to_accused": None,
    "crime_location": None,
    "time_period": None,
    "frequency": None,
    "witnesses": None,
    "threat_present": None,
    "injury_present": None,
    "identity_known": None,
    "evidence_available": None,
    "medium": None,
    "secondary_action": None,
    "consent_present": None,
    "shared_residence": None,
    "workplace_related": None,
    "ongoing": None,
    "asked_fields": [],
    "final_question_asked": False
}

def merge_entities(existing, extracted):
    for k, v in extracted.items():
        if v is not None and existing.get(k) is None:
            existing[k] = v
    return existing

def completion_percentage(data):
    total = len(data)
    filled = sum(1 for v in data.values() if v is not None)
    return filled / total
