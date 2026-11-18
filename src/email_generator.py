
def generate_email(
    company: str,
    role: str,
    language: str = "fr",
    candidate: str = "[Ton nom]",
) -> dict:
    if language == "en":
        subject = f"Application for a final-year internship - {role}"

        body = f"""Dear Recruitment Team,

I am currently pursuing a Master's degree in Big Data & Cloud Computing (BD2C), and I would like to apply for a final-year internship opportunity in {role} at {company}.

My background includes data engineering, SQL, data processing and cloud-oriented projects. I would welcome the opportunity to contribute to your team and further develop my skills.

Please find my CV attached for your consideration. I would be happy to discuss my application with you.

Kind regards,
{candidate}
"""
    else:
        subject = f"Candidature PFE - {role} - Master BD2C"

        body = f"""Bonjour,

Actuellement étudiant en Master Big Data & Cloud Computing (BD2C), je suis à la recherche d'un stage de fin d'études et souhaite vous proposer ma candidature pour une opportunité en {role} au sein de {company}.

Mon parcours comprend des projets autour de l'ingénierie des données, de SQL, du traitement de données et des technologies cloud. Je souhaiterais mettre ces compétences au service de votre équipe et les approfondir dans un contexte professionnel.

Vous trouverez mon CV en pièce jointe. Je reste à votre disposition pour échanger sur ma candidature.

Cordialement,
{candidate}
"""

    return {"subject": subject, "body": body}


def validate_email_address(email: str) -> bool:
    import re
    email = email.strip()
    return bool(re.fullmatch(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+", email))


def generate_personalized_email(
    company: str,
    position: str,
    description: str,
    match: dict,
    cv_path: str,
    language: str = "fr",
    candidate: str = "[Ton nom]",
) -> dict:
    """Generate locally by default; optionally use an OpenAI-compatible API."""
    base = generate_email(company, position, language, candidate)
    skills = match.get("matching_skills") or match.get("matched_keywords") or []
    if skills:
        joined = ", ".join(skills[:6])
        if language == "en":
            base["body"] = base["body"].replace(
                "My background includes",
                f"My profile particularly matches {joined}. My background includes",
            )
        else:
            base["body"] = base["body"].replace(
                "Mon parcours comprend",
                f"Mon profil correspond notamment à {joined}. Mon parcours comprend",
            )

    import os
    import requests

    api_key = os.getenv("LLM_API_KEY", "").strip()
    api_url = os.getenv("LLM_API_URL", "").strip()
    model = os.getenv("LLM_MODEL", "gpt-4o-mini").strip()
    if not api_key or not api_url:
        return base

    prompt_language = "French" if language == "fr" else "English"
    prompt = (
        f"Write a concise professional {prompt_language} application email. "
        f"Candidate: {candidate}. Company: {company}. Position: {position}. "
        f"Matching skills: {', '.join(skills[:8])}. "
        f"Job description: {description[:3000]}.\n"
        "Return only valid JSON with keys subject and body."
    )
    try:
        response = requests.post(
            api_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a professional career assistant."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
            },
            timeout=20,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        import json
        parsed = json.loads(content.strip().strip("`"))
        if parsed.get("subject") and parsed.get("body"):
            return {"subject": parsed["subject"].strip(), "body": parsed["body"].strip()}
    except Exception:
        return base
    return base
