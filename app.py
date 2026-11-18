from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.cover_letter_generator import create_cover_letter_pdf, generate_cover_letter
from src.cv_selector import recommend_cv
from src.database import (
    OPPORTUNITY_STATUSES,
    dashboard_metrics,
    init_db,
    list_applications,
    list_opportunities,
    upsert_opportunity,
    update_opportunity,
)
from src.email_generator import generate_personalized_email, validate_email_address
from src.gmail_reader import get_gmail_profile, search_offer_emails
from src.gmail_sender import send_application_email
from src.job_sources import load_offers_csv
from src.matcher import load_profile, match_offer
from src.spontaneous_database import (
    init_spontaneous_db,
    list_spontaneous_applications,
    record_spontaneous_application,
)

st.set_page_config(page_title="PFE Copilot", page_icon="🎓", layout="wide")

init_db()
init_spontaneous_db()
profile = load_profile()
candidate_name = profile["candidate"].get("name", "Candidat")

st.markdown(
    """
    <style>
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
    [data-testid="stMetric"] {background: #F7F9FC; border: 1px solid #E6ECF2; border-radius: 12px; padding: 12px;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.sidebar.title("PFE Copilot")
st.sidebar.caption("Assistant de candidatures")
page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Opportunities",
        "Job Matching",
        "CV Management",
        "Spontaneous Applications",
        "Email Generator",
        "Application Tracking",
        "Gmail Settings",
        "Profile & Configuration",
    ],
)


def opportunity_source_labels():
    return {"Manuel": "manual", "CSV": "csv", "Gmail": "gmail"}


if page == "Dashboard":
    st.title("Tableau de bord")
    metrics = dashboard_metrics()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Opportunités", metrics["total"])
    c2.metric("Analysées", metrics["analyzed"])
    c3.metric("Envoyées", metrics["applications_sent"])
    c4.metric("Entretiens", metrics["interviews"])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Acceptées", metrics["accepted"])
    c2.metric("Refusées", metrics["rejected"])
    c3.metric("Taux de conversion", f"{metrics['conversion_rate']} %")
    c4.metric("Nouveau statut", len(metrics["status_distribution"]))

    if metrics["status_distribution"]:
        st.subheader("Répartition des statuts")
        st.bar_chart(pd.DataFrame(
            {"Statut": list(metrics["status_distribution"]),
             "Nombre": list(metrics["status_distribution"].values())}
        ).set_index("Statut"))

    recent = list_opportunities()
    st.subheader("Activité récente")
    if recent:
        st.dataframe(
            [{k: o[k] for k in ("company", "title", "status", "score", "deadline", "updated_at")}
             for o in recent[:10]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Ajoutez une opportunité pour démarrer le suivi.")


elif page == "Opportunities":
    st.title("Opportunités")
    left, right = st.columns([2, 1])
    with left:
        search = st.text_input("Rechercher")
    with right:
        status_filter = st.selectbox("Statut", [""] + list(OPPORTUNITY_STATUSES))

    opportunities = list_opportunities(search=search, status=status_filter)
    if opportunities:
        st.dataframe(opportunities, use_container_width=True, hide_index=True)
        selected_id = st.selectbox(
            "Modifier une opportunité",
            options=[o["id"] for o in opportunities],
            format_func=lambda oid: next(
                f"{o['company']} — {o['title']}" for o in opportunities if o["id"] == oid
            ),
        )
        selected = next(o for o in opportunities if o["id"] == selected_id)
        new_status = st.selectbox(
            "Nouveau statut",
            list(OPPORTUNITY_STATUSES),
            index=list(OPPORTUNITY_STATUSES).index(selected["status"])
            if selected["status"] in OPPORTUNITY_STATUSES else 0,
        )
        if st.button("Mettre à jour le statut"):
            update_opportunity(selected_id, status=new_status)
            st.success("Statut enregistré.")
            st.rerun()
    else:
        st.info("Aucune opportunité ne correspond.")

    st.divider()
    st.subheader("Ajouter une opportunité")
    with st.form("manual_opportunity"):
        company = st.text_input("Entreprise *")
        title = st.text_input("Poste *")
        location = st.text_input("Localisation")
        description = st.text_area("Description *", height=180)
        source_url = st.text_input("URL")
        deadline = st.text_input("Date limite (AAAA-MM-JJ)")
        recipient = st.text_input("Email RH")
        submit = st.form_submit_button("Enregistrer")
    if submit:
        if not company.strip() or not title.strip() or not description.strip():
            st.error("Entreprise, poste et description sont requis.")
        elif recipient.strip() and not validate_email_address(recipient):
            st.error("Adresse RH invalide.")
        else:
            oid, created = upsert_opportunity({
                "company": company.strip(), "title": title.strip(),
                "location": location.strip(), "description": description.strip(),
                "source": "manual", "source_url": source_url.strip(),
                "deadline": deadline.strip(), "recipient": recipient.strip(),
            })
            st.success("Nouvelle opportunité enregistrée." if created else "Opportunité mise à jour.")

    st.subheader("Importer un CSV")
    uploaded = st.file_uploader("CSV avec company, title, description", type=["csv"])
    if uploaded:
        try:
            offers = load_offers_csv(uploaded)
            created = 0
            for offer in offers:
                _, is_created = upsert_opportunity({
                    **offer,
                    "source": "csv",
                    "location": offer.get("location", ""),
                    "deadline": offer.get("deadline", ""),
                })
                created += int(is_created)
            st.success(f"{len(offers)} offre(s) lue(s), dont {created} nouvelle(s).")
        except Exception as exc:
            st.error(f"Import impossible : {exc}")


elif page == "Job Matching":
    st.title("Analyse et compatibilité")
    opportunities = list_opportunities()
    if opportunities:
        choice = st.selectbox(
            "Opportunité",
            options=[o["id"] for o in opportunities],
            format_func=lambda oid: next(
                f"{o['company']} — {o['title']}" for o in opportunities if o["id"] == oid
            ),
        )
        offer = next(o for o in opportunities if o["id"] == choice)
        company, title, description = offer["company"], offer["title"], offer["description"]
    else:
        company = st.text_input("Entreprise")
        title = st.text_input("Poste")
        description = st.text_area("Description", height=220)

    if st.button("Analyser", type="primary"):
        if not title.strip() or not description.strip():
            st.error("Poste et description sont requis.")
        else:
            match = match_offer(title, description)
            cv = recommend_cv(match["role"], f"{title} {description}")
            if opportunities:
                update_opportunity(choice, role=match["role"], score=match["score"],
                                   status="Analyzed", cv_path=str(cv["cv_path"]) if cv["cv_path"] else "")
            st.session_state["match_draft"] = {
                "company": company, "title": title, "description": description,
                "recipient": offer["recipient"] if opportunities else "",
                "match": match, "cv": cv,
            }

    draft = st.session_state.get("match_draft")
    if draft:
        match = draft["match"]
        cv = draft["cv"]
        c1, c2 = st.columns(2)
        c1.metric("Score de compatibilité", f"{match['score']} / 100")
        c2.metric("Profil recommandé", match["role_label"])
        st.write("**Compétences correspondantes :**", ", ".join(match["matching_skills"]) or "Aucune")
        st.write("**Compétences à renforcer :**", ", ".join(match["missing_skills"][:8]) or "Aucune")
        st.write("**Pourquoi ce score :**")
        for reason in match["reasons"]:
            st.write(f"- {reason}")
        if cv["exists"]:
            st.success(cv["reason"])
        else:
            st.error(cv["reason"])


elif page == "CV Management":
    st.title("Gestion des CV")
    for role_id, role in profile["roles"].items():
        cv_path = Path(role["cv"])
        if not cv_path.is_absolute():
            cv_path = Path.cwd() / cv_path
        c1, c2 = st.columns([3, 1])
        c1.write(f"**{role['label']}** — `{cv_path}`")
        c2.write("Disponible" if cv_path.is_file() else "PDF manquant")

    st.divider()
    st.subheader("Ajouter une version PDF")
    uploaded = st.file_uploader("PDF du CV", type=["pdf"])
    orientation = st.selectbox("Orientation", [role["label"] for role in profile["roles"].values()])
    if uploaded:
        if uploaded.size > 10 * 1024 * 1024:
            st.error("Le PDF dépasse 10 Mo.")
        else:
            target_dir = Path("cvs")
            target_dir.mkdir(exist_ok=True)
            target = target_dir / f"{orientation.lower().replace(' ', '_').replace('/', '-')}.pdf"
            target.write_bytes(uploaded.read())
            st.success(f"CV enregistré : {target}")


elif page == "Spontaneous Applications":
    st.title("Candidature spontanée")
    role_labels = {role["label"]: role_id for role_id, role in profile["roles"].items()}
    with st.form("spontaneous"):
        recipient = st.text_input("Email RH *")
        company = st.text_input("Entreprise")
        website = st.text_input("Site web")
        position = st.text_input("Poste souhaité", value="Data Engineer")
        language = st.selectbox("Langue", ["fr", "en"],
                                format_func=lambda v: "Français" if v == "fr" else "English")
        role_label = st.selectbox("Orientation CV", list(role_labels))
        generate = st.form_submit_button("Préparer")
    if generate:
        if not validate_email_address(recipient):
            st.error("Adresse RH invalide.")
        elif not position.strip():
            st.error("Le poste est requis.")
        else:
            role_id = role_labels[role_label]
            cv = recommend_cv(role_id, position)
            if not cv["exists"]:
                st.error(cv["reason"])
            else:
                letter = generate_cover_letter(candidate_name, role_label, company, language)
                subject = (
                    f"Candidature spontanée — {position}"
                    if language == "fr"
                    else f"Spontaneous application — {position}"
                )
                body = (
                    "Madame, Monsieur,\n\n"
                    f"Je souhaite proposer ma candidature spontanée pour un poste de {position}. "
                    f"Vous trouverez mon CV en pièce jointe.\n\n"
                    "Cordialement,\n" + candidate_name
                    if language == "fr"
                    else
                    "Dear Hiring Team,\n\n"
                    f"I would like to submit my spontaneous application for {position}. "
                    f"My CV is attached for your consideration.\n\n"
                    "Kind regards,\n" + candidate_name
                )
                st.session_state["spont_draft"] = {
                    "recipient": recipient, "company": company, "website": website,
                    "position": position, "language": language, "cv": cv,
                    "subject": subject, "body": body, "letter": letter,
                    "profile": role_label,
                }

    draft = st.session_state.get("spont_draft")
    if draft:
        st.divider()
        st.subheader("Vérification avant envoi")
        st.write("**Destinataire :**", draft["recipient"])
        st.write("**Pièce jointe :**", Path(draft["cv"]["cv_path"]).name)
        subject = st.text_input("Objet", draft["subject"], key="spont_subject")
        body = st.text_area("Message", draft["body"], height=220, key="spont_body")
        letter = st.text_area("Lettre de motivation", draft["letter"], height=260, key="spont_letter")
        confirmed = st.checkbox("Je confirme le destinataire, le contenu et les pièces jointes.",
                                key="spont_confirm")
        if st.button("Envoyer via Gmail", type="primary",
                     disabled=not (confirmed and subject.strip() and body.strip())):
            try:
                gmail_id = send_application_email(
                    draft["recipient"], subject.strip(), body.strip(),
                    str(draft["cv"]["cv_path"]), create_cover_letter_pdf(letter),
                )
                record_spontaneous_application(
                    recipient=draft["recipient"], company=draft["company"],
                    profile=draft["profile"], subject=subject.strip(), body=body.strip(),
                    cover_letter=letter, cv_path=str(draft["cv"]["cv_path"]),
                    status="sent", gmail_message_id=gmail_id,
                )
                st.success(f"Candidature envoyée. Gmail ID : {gmail_id}")
                del st.session_state["spont_draft"]
            except Exception as exc:
                record_spontaneous_application(
                    recipient=draft["recipient"], company=draft["company"],
                    profile=draft["profile"], subject=subject.strip(), body=body.strip(),
                    cover_letter=letter, cv_path=str(draft["cv"]["cv_path"]),
                    status="failed", error_message=str(exc),
                )
                st.error(f"Envoi échoué : {exc}")

    history = list_spontaneous_applications()
    if history:
        st.subheader("Historique")
        st.dataframe(history, use_container_width=True, hide_index=True)


elif page == "Email Generator":
    st.title("Générateur d'e-mail")
    draft = st.session_state.get("match_draft")
    if not draft:
        st.info("Analysez d'abord une opportunité dans « Job Matching ».")
    else:
        match = draft["match"]
        recipient = st.text_input("Destinataire", draft["recipient"])
        language = st.selectbox("Langue", ["fr", "en"],
                                format_func=lambda v: "Français" if v == "fr" else "English")
        candidate = st.text_input("Nom", candidate_name)
        if st.button("Générer"):
            email = generate_personalized_email(
                draft["company"], draft["title"], draft["description"], match,
                str(draft["cv"]["cv_path"]) if draft["cv"]["exists"] else "",
                language, candidate,
            )
            st.session_state["email_draft"] = {"recipient": recipient, **email}

        email_draft = st.session_state.get("email_draft")
        if email_draft:
            subject = st.text_input("Objet", email_draft["subject"])
            body = st.text_area("Corps", email_draft["body"], height=260)
            st.write("**Pièce jointe :**", draft["cv"]["reason"] if draft["cv"]["exists"] else "CV manquant")
            confirm = st.checkbox("Je confirme explicitement cet envoi.")
            if st.button("Envoyer via Gmail", type="primary",
                         disabled=not (confirm and validate_email_address(recipient)
                                       and draft["cv"]["exists"])):
                try:
                    gmail_id = send_application_email(
                        recipient, subject.strip(), body.strip(),
                        str(draft["cv"]["cv_path"]),
                    )
                    st.success(f"E-mail envoyé. Gmail ID : {gmail_id}")
                except Exception as exc:
                    st.error(f"Envoi échoué : {exc}")


elif page == "Application Tracking":
    st.title("Suivi des candidatures")
    applications = list_applications()
    if applications:
        st.dataframe(applications, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune candidature enregistrée.")


elif page == "Gmail Settings":
    st.title("Paramètres Gmail")
    st.write("Scopes minimaux utilisés :")
    st.code("gmail.readonly\ngmail.send", language="text")
    if st.button("Vérifier la connexion"):
        try:
            profile_data = get_gmail_profile()
            st.success(f"Connecté : {profile_data.get('emailAddress', 'Compte Gmail')}")
        except Exception as exc:
            st.error(f"Connexion indisponible : {exc}")
            st.caption("Configurez OAuth 2.0 avec credentials.json ou GMAIL_CREDENTIALS_FILE.")
    st.info("Les jetons OAuth sont stockés localement hors de l'interface et peuvent être définis via GMAIL_TOKEN_FILE.")


else:
    st.title("Profil & Configuration")
    c1, c2 = st.columns(2)
    c1.json(profile["candidate"])
    c2.json(profile["roles"])
