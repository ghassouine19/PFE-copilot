
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    HRFlowable,
)


def generate_cover_letter(
    candidate: str,
    profile: str,
    company: str = "",
    language: str = "fr",
) -> str:
    """Génère une lettre de motivation personnalisable."""

    company_line = (
        f"au sein de {company.strip()}"
        if company.strip()
        else "au sein de votre entreprise"
    )

    if language == "en":
        return f"""Dear Hiring Team,

I am currently pursuing a Master's degree in Big Data and Cloud Computing
and would like to apply spontaneously for a final-year internship
in {profile} {company_line}.

My academic background and practical projects have allowed me to develop
skills in data processing, database systems, analytics and modern
data technologies. I am particularly interested in contributing to
real-world projects while strengthening my technical and professional skills.

I would welcome the opportunity to discuss how my background and motivation
could contribute to your team.

Please find my CV attached for your consideration.

Yours faithfully,
{candidate}"""

    return f"""Madame, Monsieur,

Actuellement étudiant en Master Big Data et Cloud Computing, je souhaite
vous soumettre ma candidature spontanée pour un stage de fin d'études
(PFE) en {profile} {company_line}.

Ma formation et mes projets pratiques m'ont permis de développer des
compétences en traitement et exploitation des données, bases de données,
analyse et technologies modernes de la data. Je souhaite mettre ces
compétences au service de projets concrets, tout en approfondissant
mon expérience au sein d'une équipe professionnelle.

Motivé, rigoureux et désireux d'apprendre, je serais heureux de pouvoir
échanger avec vous sur les opportunités de stage correspondant à mon profil.

Vous trouverez mon CV en pièce jointe. Je reste à votre disposition
pour tout complément d'information ou entretien.

Je vous prie d'agréer, Madame, Monsieur, l'expression de mes salutations
distinguées.

{candidate}"""


def create_cover_letter_pdf(letter_text: str) -> bytes:
    """Crée un PDF en mémoire, prêt à être joint à un e-mail."""

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2.2 * cm,
        leftMargin=2.2 * cm,
        topMargin=2.2 * cm,
        bottomMargin=2.2 * cm,
        title="Lettre de motivation - Candidature PFE",
        author="PFE Copilot",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "LetterTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#17365D"),
        spaceAfter=8,
    )

    body_style = ParagraphStyle(
        "LetterBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10.5,
        leading=16,
        spaceAfter=12,
        alignment=0,
    )

    story = [
        Paragraph("LETTRE DE MOTIVATION", title_style),
        Spacer(1, 8),
        HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor("#B7C9E2"),
        ),
        Spacer(1, 24),
    ]

    for paragraph in letter_text.split("\n\n"):
        safe_text = escape(paragraph).replace("\n", "<br/>")
        story.append(Paragraph(safe_text, body_style))

    document.build(story)
    return buffer.getvalue()
