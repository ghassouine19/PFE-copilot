
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
