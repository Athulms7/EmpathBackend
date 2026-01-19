def generate_next_question(incident_data: dict) -> str | None:
    asked = incident_data.get("asked_fields", [])

    priority_questions = [
        ("crime_location", "Where does this incident usually take place?"),
        ("time_period", "When did this situation first begin?"),
        ("frequency", "How often does this happen?"),
        ("witnesses", "Was anyone else present or aware of what happened?"),
        ("evidence_available", "Do you have any evidence such as messages or recordings?"),
        ("injury_present", "Have you been physically injured in any way?")
    ]

    for field, question in questions:
        if incident_data.get(field) is None and field not in asked:
            incident_data["asked_fields"] = asked + [field]
            return question

    return None
