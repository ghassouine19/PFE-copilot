from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path

import streamlit as st

from src.config import CV_DIR, ROOT
from src.cover_letter_generator import create_cover_letter_pdf, generate_cover_letter
from src.cv_selector import (
    extract_cv_text,
    list_profile_cvs,
    select_cv,
    validate_cv_upload,
)
from src.database import (
    add_application,
    application_stats,
    get_application,
    init_db,
    list_applications,
    update_status,
)
from src.email_generator import generate_email
from src.gmail_reader import gmail_configuration_status, search_offer_emails
from src.gmail_sender import send_application_email
from src.job_sources import import_stats
from src.matcher import match_offer
from src.spontaneous_database import (
    init_spontaneous_db,
    list_spontaneous_applications,
    record_spontaneous_application,
)

st.set_page_config(page_title="PFE Copilot", page_icon="P", layout="wide")
init_db()
init_spontaneous_db()

STATUS_LABELS = {
    "draft": "Brouillon",
    "approved": "Validée",
    "sent": "Envoyée",
    "rejected": "Refusée",
}


def display_match(match: dict) -> None:
    left, middle, right = st.columns(3)
    left.metric("Score lexical", f'{match["score"]}/100')
    middle.metric("Profil détecté", match["role_label"])
    right.metric("PFE détecté", "Oui" if match["is_pfe"] else "À vérifier")
    st.write("**Mots-clés pertinents :**", ", ".join(match["matched_keywords"]) or "Aucun")
    st.info(match["explanation"])


def create_draft(company: str, title: str, description: str, recipient: str, url: str, language: str, candidate: str, use_ai: bool = False) -> None:
    match = match_offer(title, description)
    email = generate_email(company, match["role_label"], language, candidate or "[Ton nom]", use_ai=use_ai)
    cv_path = select_cv(match["role"])
    st.session_state["draft"] = {
        "company": company.strip(),
        "title": title.strip(),
        "recipient": recipient.strip(),
        "source_url": url.strip(),
        "description": description.strip(),
        "role": match["role"],
        "score": match["score"],
        "language": language,
        "subject": email["subject"],
        "body": email["body"],
        "cv_path": str(cv_path) if cv_path else "",
        "status": "draft",
    }
    st.session_state["match"] = match


def render_dashboard() -> None:
    st.title("Dashboard")
    st.caption("Vue opérationnelle de vos candidatures et de votre activité récente.")
    stats = application_stats()
    spontaneous = list_spontaneous_applications()
    total = stats["total"] + len(spontaneous)
    drafts = stats["drafts"] + sum(item["status"] == "failed" for item in spontaneous)
    spontaneous_count = len(spontaneous)
    cards = st.columns(4)
    cards[0].metric("Candidatures", total)
    cards[1].metric("Brouillons", drafts)
    cards[2].metric("Spontanées", spontaneous_count)
    cards[3].metric("Envoyées", stats["by_status"].get("sent", 0) + sum(item["status"] == "sent" for item in spontaneous))
    st.subheader("Répartition par statut")
    status_rows = [{"Statut": STATUS_LABELS.get(key, key), "Nombre": value} for key, value in stats["by_status"].items()]
    if status_rows:
        st.bar_chart({"Nombre": [row["Nombre"] for row in status_rows]}, x=None)
        st.dataframe(status_rows, hide_index=True, use_container_width=True)
    else:
        st.info("Aucune candidature enregistrée. Commencez par analyser une offre.")
    st.subheader("Activité récente")
    recent = list_applications()[:8]
    if recent:
        st.dataframe(
            [{"Entreprise": item["company"], "Poste": item["title"], "Profil": item["role"],
              "Statut": STATUS_LABELS.get(item["status"], item["status"]), "Date": item["created_at"]} for item in recent],
            hide_index=True, use_container_width=True,
        )
    else:
        st.info("Votre activité apparaîtra ici après l'enregistrement d'un brouillon.")


def render_matching() -> None:
    st.title("Nouvelle candidature")
    st.caption("Analysez une offre, vérifiez le profil détecté et préparez un email modifiable.")
    with st.form("offer_form"):
        company = st.text_input("Entreprise *")
        title = st.text_input("Intitulé du poste *")
        recipient = st.text_input("Email RH (facultatif)")
        source_url = st.text_input("Lien de l'offre (facultatif)")
        description = st.text_area("Description de l'offre *", height=190)
        candidate = st.text_input("Nom à afficher dans l'email")
        language = st.selectbox("Langue", ["fr", "en"], format_func=lambda value: "Français" if value == "fr" else "English")
        use_ai = st.checkbox("Utiliser l'assistance IA si OPENAI_API_KEY est configurée", disabled=not bool(__import__("os").getenv("OPENAI_API_KEY")))
        submitted = st.form_submit_button("Analyser l'offre", type="primary")
    if submitted:
        if not company.strip() or not title.strip() or not description.strip():
            st.error("Renseignez l'entreprise, le poste et la description.")
        else:
            try:
                create_draft(company, title, description, recipient, source_url, language, candidate, use_ai)
                st.success("Analyse terminée. Vérifiez le résultat ci-dessous.")
            except Exception as exc:
                st.error(f"Analyse impossible : {exc}")
    if "draft" not in st.session_state:
        st.info("Aucun résultat à afficher. Soumettez une offre pour commencer.")
        return
    draft, match = st.session_state["draft"], st.session_state["match"]
    st.divider()
    st.subheader("Résultat de l'analyse")
    display_match(match)
    if draft["cv_path"]:
        st.success(f"CV recommandé : {Path(draft['cv_path']).name}")
    else:
        st.warning("Le CV du profil détecté est absent du dossier cvs/.")
    st.subheader("Email à vérifier")
    edited_subject = st.text_input("Objet", value=draft["subject"], key="matching_subject")
    edited_body = st.text_area("Message", value=draft["body"], height=260, key="matching_body")
    if st.button("Enregistrer le brouillon", type="primary"):
        draft.update(subject=edited_subject.strip(), body=edited_body.strip())
        add_application(draft)
        st.session_state.pop("draft", None)
        st.session_state.pop("match", None)
        st.success("Brouillon enregistré dans SQLite.")


def render_cvs() -> None:
    st.title("Gestion des CV")
    st.caption("Vérifiez les CV associés aux quatre profils et testez l'extraction de texte.")
    rows = list_profile_cvs()
    st.dataframe(
        [{"Profil": row["label"], "Fichier": Path(row["path"]).name, "Disponible": "Oui" if row["available"] else "Non"} for row in rows],
        hide_index=True, use_container_width=True,
    )
    selected = st.selectbox("CV à prévisualiser", [row["role"] for row in rows], format_func=lambda role: next(item["label"] for item in rows if item["role"] == role))
    path = select_cv(selected)
    if path:
        if st.button("Extraire le texte du CV"):
            try:
                text = extract_cv_text(path)
                st.text_area("Texte extrait", text, height=260)
            except Exception as exc:
                st.error(f"Extraction impossible : {exc}")
    else:
        st.warning("Aucun CV disponible pour ce profil.")
    st.subheader("Ajouter un CV PDF")
    upload = st.file_uploader("PDF compatible", type=["pdf"])
    upload_role = st.selectbox("Profil associé au fichier", [row["role"] for row in rows], format_func=lambda role: next(item["label"] for item in rows if item["role"] == role), key="upload_role")
    if upload and st.button("Valider et enregistrer le CV"):
        valid, error = validate_cv_upload(upload)
        if not valid:
            st.error(error)
        else:
            CV_DIR.mkdir(parents=True, exist_ok=True)
            target = CV_DIR / "uploads" / f"{upload_role}.pdf"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(upload.getvalue())
            st.success(f"CV validé et enregistré dans {target.relative_to(ROOT)}.")


def render_generators() -> None:
    st.title("Générateurs")
    email_tab, letter_tab = st.tabs(["Email", "Lettre de motivation"])
    with email_tab:
        with st.form("email_generator"):
            company = st.text_input("Entreprise", key="generator_company")
            role = st.text_input("Poste", key="generator_role")
            candidate = st.text_input("Candidat", value="[Ton nom]", key="generator_candidate")
            language = st.selectbox("Langue", ["fr", "en"], format_func=lambda value: "Français" if value == "fr" else "English", key="generator_language")
            generate = st.form_submit_button("Générer")
        if generate:
            st.session_state["generated_email"] = generate_email(company, role, language, candidate)
        result = st.session_state.get("generated_email")
        if result:
            st.text_input("Objet", value=result["subject"], key="generated_subject")
            st.text_area("Corps (modifiable et copiable)", value=result["body"], height=300, key="generated_body")
    with letter_tab:
        with st.form("letter_generator"):
            candidate = st.text_input("Nom du candidat", key="letter_candidate")
            profile = st.text_input("Profil", value="Data Engineer", key="letter_profile")
            company = st.text_input("Entreprise", key="letter_company")
            language = st.selectbox("Langue", ["fr", "en"], format_func=lambda value: "Français" if value == "fr" else "English", key="letter_language")
            generate = st.form_submit_button("Générer la lettre")
        if generate:
            st.session_state["generated_letter"] = generate_cover_letter(candidate or "Candidat", profile, company, language)
        letter = st.session_state.get("generated_letter")
        if letter:
            edited = st.text_area("Lettre (modifiable)", value=letter, height=380, key="generated_letter_text")
            pdf = create_cover_letter_pdf(edited)
            st.download_button("Télécharger le PDF professionnel", pdf, "lettre_motivation_pfe.pdf", "application/pdf")


def render_csv() -> None:
    st.title("Importer des offres CSV")
    st.caption("Validez les colonnes, inspectez les lignes et préparez les offres pour le moteur de matching.")
    upload = st.file_uploader("Fichier CSV UTF-8", type=["csv"], key="csv_upload")
    if upload:
        try:
            stats = import_stats(BytesIO(upload.getvalue()))
            st.session_state["csv_offers"] = stats["offers"]
            metrics = st.columns(4)
            metrics[0].metric("Lignes", stats["total_rows"])
            metrics[1].metric("Valides", stats["valid_rows"])
            metrics[2].metric("Invalides", stats["invalid_rows"])
            metrics[3].metric("Doublons", stats["duplicates"])
            st.dataframe(stats["offers"], use_container_width=True, hide_index=True)
            if st.button("Analyser et enregistrer les offres valides"):
                for offer in stats["offers"]:
                    match = match_offer(offer["title"], offer["description"])
                    email = generate_email(offer["company"], match["role_label"], "fr")
                    add_application({**offer, **match, "role": match["role"], "score": match["score"], "language": "fr", "subject": email["subject"], "body": email["body"], "cv_path": str(select_cv(match["role"]) or ""), "status": "draft"})
                st.success(f'{len(stats["offers"])} offre(s) enregistrée(s) comme brouillons.')
        except Exception as exc:
            st.error(f"Erreur CSV : {exc}")


def render_gmail() -> None:
    st.title("Intégration Gmail")
    status = gmail_configuration_status()
    if status["connected"]:
        st.success("Configuration Gmail locale détectée.")
    elif status["credentials_available"]:
        st.warning("Les identifiants existent, mais aucune session OAuth locale n'est encore enregistrée.")
    else:
        st.info("Gmail est optionnel. Ajoutez credentials.json à la racine pour activer OAuth 2.0.")
    if st.button("Récupérer les offres Gmail"):
        try:
            with st.spinner("Lecture de la boîte Gmail..."):
                st.session_state["gmail_emails"] = search_offer_emails(max_results=30)
            st.success(f'{len(st.session_state["gmail_emails"])} email(s) récupéré(s).')
        except Exception as exc:
            st.error(f"Lecture Gmail impossible : {exc}")
    emails = st.session_state.get("gmail_emails", [])
    if not emails:
        st.info("Aucun email chargé.")
        return
    selected = st.selectbox("Email à examiner", emails, format_func=lambda item: f'{item.get("subject") or "(Sans objet)"} — {item.get("date", "")}')
    st.write("**Expéditeur :**", selected.get("sender", ""))
    st.write("**Objet :**", selected.get("subject", ""))
    with st.expander("Contenu complet"):
        st.text(selected.get("body", ""))
    st.info("Le contenu doit être vérifié et analysé manuellement avant toute candidature.")


def render_spontaneous() -> None:
    st.title("Candidature spontanée")
    labels = {"Data Engineer": "data_engineer", "Data Scientist": "data_scientist", "BI / Data Analyst": "bi_analyst", "AI Engineer": "ai_engineer"}
    with st.form("spontaneous_form"):
        recipient = st.text_input("Email RH *")
        company = st.text_input("Entreprise")
        candidate = st.text_input("Nom du candidat", value="Abderrahmane Ghassouine")
        profile_label = st.selectbox("Profil", list(labels))
        language = st.selectbox("Langue", ["fr", "en"], format_func=lambda value: "Français" if value == "fr" else "English")
        generate = st.form_submit_button("Préparer la candidature")
    if generate:
        if "@" not in recipient:
            st.error("Adresse email invalide.")
        else:
            role = labels[profile_label]
            st.session_state["spontaneous_draft"] = {
                "recipient": recipient.strip(), "company": company.strip(), "profile": profile_label, "role_key": role,
                "cv_path": str(select_cv(role) or ""), "subject": f"{'Spontaneous Application' if language == 'en' else 'Candidature spontanée'} — {profile_label}",
                "body": generate_email(company or "votre entreprise", profile_label, language, candidate or "Candidat")["body"],
                "cover_letter": generate_cover_letter(candidate or "Candidat", profile_label, company, language),
            }
    draft = st.session_state.get("spontaneous_draft")
    if draft:
        st.subheader("Prévisualisation et confirmation")
        subject = st.text_input("Objet", draft["subject"], key="spont_subject")
        body = st.text_area("Email", draft["body"], height=240, key="spont_body")
        letter = st.text_area("Lettre jointe", draft["cover_letter"], height=300, key="spont_letter")
        st.write("**CV joint :**", Path(draft["cv_path"]).name if draft["cv_path"] else "Absent")
        confirm = st.checkbox("Je confirme le destinataire, le contenu et l'envoi réel.", key="spont_confirm")
        ready = bool(draft["cv_path"]) and Path(draft["cv_path"]).is_file() and bool(subject.strip()) and bool(body.strip()) and bool(letter.strip())
        if st.button("Envoyer via Gmail", type="primary", disabled=not (ready and confirm)):
            try:
                message_id = send_application_email(draft["recipient"], subject.strip(), body.strip(), draft["cv_path"], create_cover_letter_pdf(letter))
                record_spontaneous_application(draft["recipient"], draft["company"], draft["profile"], subject.strip(), body.strip(), letter, draft["cv_path"], "sent", gmail_message_id=message_id)
                st.success(f"Candidature envoyée et enregistrée ({message_id}).")
                st.session_state.pop("spontaneous_draft", None)
            except Exception as exc:
                record_spontaneous_application(draft["recipient"], draft["company"], draft["profile"], subject.strip(), body.strip(), letter, draft["cv_path"], "failed", error_message=str(exc))
                st.error(f"Envoi échoué : {exc}")
    st.subheader("Historique")
    history = list_spontaneous_applications()
    if history:
        st.dataframe(history, hide_index=True, use_container_width=True)
    else:
        st.info("Aucune candidature spontanée enregistrée.")


def render_tracking() -> None:
    st.title("Suivi des candidatures")
    search = st.text_input("Rechercher par entreprise, poste ou profil")
    status = st.selectbox("Filtrer par statut", ["Tous"] + list(STATUS_LABELS.values()))
    status_key = next((key for key, value in STATUS_LABELS.items() if value == status), "")
    applications = list_applications(search, status_key)
    if not applications:
        st.info("Aucune candidature ne correspond à ces filtres.")
        return
    st.dataframe(
        [{"ID": item["id"], "Entreprise": item["company"], "Poste": item["title"], "Profil": item["role"],
          "Score": item["score"], "Statut": STATUS_LABELS.get(item["status"], item["status"]), "Date": item["created_at"]} for item in applications],
        hide_index=True, use_container_width=True,
    )
    selected_id = st.selectbox("Candidature à consulter", [item["id"] for item in applications])
    selected = get_application(selected_id)
    if selected:
        st.write(selected["description"])
        new_status = st.selectbox("Nouveau statut", list(STATUS_LABELS), index=list(STATUS_LABELS).index(selected["status"]) if selected["status"] in STATUS_LABELS else 0)
        if st.button("Enregistrer le statut"):
            update_status(selected_id, new_status)
            st.success("Statut mis à jour.")


st.sidebar.title("PFE Copilot")
st.sidebar.caption("Assistant de candidature PFE")
page = st.sidebar.radio("Navigation", ["Dashboard", "Nouvelle candidature", "CV management", "Générateurs", "Import CSV", "Gmail", "Candidature spontanée", "Suivi"])
st.sidebar.divider()
st.sidebar.caption("Données locales SQLite · Aucun envoi sans confirmation")

if page == "Dashboard":
    render_dashboard()
elif page == "Nouvelle candidature":
    render_matching()
elif page == "CV management":
    render_cvs()
elif page == "Générateurs":
    render_generators()
elif page == "Import CSV":
    render_csv()
elif page == "Gmail":
    render_gmail()
elif page == "Candidature spontanée":
    render_spontaneous()
else:
    render_tracking()
