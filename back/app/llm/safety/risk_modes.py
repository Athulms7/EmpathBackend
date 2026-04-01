def normal_mode():
    return {
        "mode": "NORMAL",
        "prompt": "app/llm/prompts/normal.txt",
        "allow_questions": True,
        "allow_empathy": True
    }

def pocso_mode():
    return {
        "mode": "POCSO",
        "prompt": "app/llm/prompts/pocso.txt",
        "allow_questions": False,
        "allow_empathy": False
    }

def high_risk_mode():
    return {
        "mode": "HIGH_RISK",
        "prompt": "app/llm/prompts/high_risk.txt",
        "allow_questions": False,
        "allow_empathy": False
    }
