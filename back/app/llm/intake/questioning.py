def generate_next_question(incident_data: dict) -> str | None:
    asked = incident_data.get("asked_fields", [])

    questions = [
        ("crime_location", "Where does this usually take place?"),
        ("time_period", "When did this begin?"),
        ("frequency", "How often does this happen?"),
        ("witnesses", "Was anyone else aware of this?")
    ]

    for field, question in questions:
        if incident_data.get(field) is None and field not in asked:
            incident_data["asked_fields"] = asked + [field]
            return question

    return None
