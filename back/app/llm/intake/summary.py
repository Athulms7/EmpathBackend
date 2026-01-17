def summarize_incident(data: dict) -> str:
    parts = []

    if data.get("relationship_to_accused"):
        parts.append(f"The accused is a {data['relationship_to_accused']}.")

    if data.get("crime_location"):
        parts.append(f"The incident occurred at {data['crime_location']}.")

    if data.get("ongoing"):
        parts.append("The situation appears to be ongoing.")

    return " ".join(parts) if parts else "An incident has been reported."
