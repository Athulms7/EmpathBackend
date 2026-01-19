def summarize_incident(data: dict) -> str:
    """
    Generate a neutral, factual case summary.
    Replace with Gemini / GPT call later.
    """

    parts = []

    if data.get("relationship_to_accused"):
        parts.append(
            f"The incident involves a {data['relationship_to_accused']}."
        )

    if data.get("medium"):
        parts.append(
            f"The actions primarily occurred through {data['medium']} communication."
        )

    if data.get("frequency"):
        parts.append(
            f"The behavior occurred {data['frequency']}."
        )

    if data.get("threat_present") is True:
        parts.append("Threatening behavior has been reported.")

    if data.get("injury_present") is True:
        parts.append("Physical injury has been reported.")

    if data.get("ongoing") is True:
        parts.append("The situation is ongoing.")

    if not parts:
        return "The user has reported an incident and further details are being collected."

    return " ".join(parts)
