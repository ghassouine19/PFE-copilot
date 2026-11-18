
import streamlit as st

from pathlib import Path

from src.cover_letter_generator import (
    generate_cover_letter,
    create_cover_letter_pdf,
)
from src.gmail_sender import send_application_email
from src.spontaneous_database import (
    init_spontaneous_db,
    record_spontaneous_application,
    list_spontaneous_applications,
)

from src.database import init_db, add_application, list_applications
from src.matcher import match_offer, load_profile
from src.cv_selector import select_cv
from src.email_generator import generate_email
from src.gmail_reader import search_offer_emails

from src.job_sources import load_offers_csv

st.set_page_config(
    page_title="PFE Copilot",
    page_icon="🎓",
    layout="wide"
)

init_db()
init_spontaneous_db()
profile = load_profile()

st.title("🎓 PFE Copilot")
st.caption(
    "Assistant de candidature PFE — Master Big Data & Cloud Computing"
)

tab_new, tab_import, tab_gmail, tab_spontaneous, tab_tracking = st.tabs(
    [
        "Nouvelle candidature",
        "Importer des offres",
        "Importer depuis Gmail",
        "Candidature spontanée",
        "Suivi des candidatures",
    ]
)

with tab_new:
    st.subheader("Analyser une opportunité")

    with st.form("offer_form"):
        company = st.text_input("Entreprise *")
        title = st.text_input("Intitulé du poste *")
        recipient = st.text_input("Email RH (facultatif)")
        source_url = st.text_input("Lien de l'offre (facultatif)")
        description = st.text_area("Description de l'offre *", height=180)
        candidate = st.text_input("Nom à afficher dans l'email")
        language = st.selectbox(
            "Langue de candidature",
            ["fr", "en"],
            format_func=lambda x: "Français" if x == "fr" else "English"
        )

        submitted = st.form_submit_button("Analyser l'offre")

    if submitted:
        if not company.strip() or not title.strip() or not description.strip():
            st.error("Renseigne l'entreprise, le poste et la description.")
        else:
            match = match_offer(title, description)
            cv_path = select_cv(match["role"])

            email = generate_email(
                company=company.strip(),
                role=match["role_label"],
                language=language,
                candidate=candidate.strip() or "[Ton nom]"
            )

            st.session_state["draft"] = {
                "company": company.strip(),
                "title": title.strip(),
                "recipient": recipient.strip(),
                "source_url": source_url.strip(),
                "description": description.strip(),
                "role": match["role"],
                "score": match["score"],
                "language": language,
                "subject": email["subject"],
                "body": email["body"],
                "cv_path": str(cv_path) if cv_path else "",
                "status": "draft"
            }
            st.session_state["match"] = match

    if "draft" in st.session_state:
        draft = st.session_state["draft"]
        match = st.session_state["match"]

        st.divider()
        st.subheader("Résultat de l'analyse")

        col1, col2 = st.columns(2)
        col1.metric("Score lexical", f'{match["score"]}/100')
        col2.metric("Poste détecté", match["role_label"])

        st.write("**Mots-clés détectés :**",
                 ", ".join(match["matched_keywords"]) or "Aucun")
        st.write("**PFE détecté :**", "Oui" if match["is_pfe"] else "À vérifier")

        if draft["cv_path"]:
            st.success(f"CV sélectionné : {draft['cv_path']}")
        else:
            st.warning(
                "Le PDF correspondant est absent. Ajoute le CV dans le dossier cvs."
            )

        st.subheader("Email à vérifier")
        edited_subject = st.text_input("Objet", value=draft["subject"])
        edited_body = st.text_area("Message", value=draft["body"], height=260)

        if st.button("Enregistrer le brouillon"):
            draft["subject"] = edited_subject
            draft["body"] = edited_body
            add_application(draft)
            del st.session_state["draft"]
            del st.session_state["match"]
            st.success("Brouillon enregistré dans le suivi.")

        st.info(
            "Aucun email n'est envoyé à ce stade. "
            "L'intégration Gmail sera ajoutée après validation du MVP."
        )


with tab_import:
    st.subheader("Importer des offres de PFE")

    uploaded_file = st.file_uploader(
        "Sélectionner un fichier CSV",
        type=["csv"],
        key="offers_csv",
    )

    if uploaded_file:
        try:
            offers = load_offers_csv(uploaded_file)
            st.success(f"{len(offers)} offre(s) valide(s) importée(s).")
            st.dataframe(offers, use_container_width=True)

            st.info(
                "Prochaine étape : enregistrer les offres en base, "
                "calculer leur score et préparer les emails."
            )

        except (ValueError, Exception) as exc:
            st.error(f"Erreur lors de l'import : {exc}")


with tab_gmail:
    st.subheader("Récupérer les offres depuis Gmail")

    st.write(
        "Récupère tes e-mails, vérifie leur contenu, "
        "puis sélectionne ceux que tu souhaites analyser."
    )

    if st.button("📩 Récupérer les e-mails Gmail"):
        try:
            with st.spinner("Lecture de la boîte Gmail..."):
                st.session_state["gmail_emails"] = search_offer_emails(
                    max_results=30
                )
            st.success(
                f"{len(st.session_state['gmail_emails'])} "
                "e-mail(s) récupéré(s)."
            )
        except Exception as exc:
            st.error(f"Impossible de lire Gmail : {exc}")

    emails = st.session_state.get("gmail_emails", [])

    if not emails:
        st.info(
            "Aucun e-mail chargé. Clique sur le bouton ci-dessus "
            "pour récupérer les messages."
        )
    else:
        selected_email = st.selectbox(
            "Choisir un e-mail",
            options=emails,
            format_func=lambda e: (
                f"{e.get('subject') or '(Sans objet)'} — "
                f"{e.get('date', '')}"
            ),
            key="gmail_selected_email",
        )

        st.write("**Expéditeur :**", selected_email.get("sender", ""))
        st.write("**Objet :**", selected_email.get("subject", ""))

        with st.expander("Afficher le contenu complet"):
            st.text(selected_email.get("body", "") or "Corps vide")

        st.divider()
        st.subheader("Préparer une analyse")

        st.caption(
            "Vérifie le contenu avant de continuer. "
            "L'expéditeur du message n'est pas automatiquement "
            "considéré comme le contact RH."
        )

        message_id = selected_email.get("message_id", "unknown")
        body = selected_email.get("body", "")
        subject = selected_email.get("subject", "")

        with st.form(f"gmail_offer_form_{message_id}"):
            company = st.text_input(
                "Entreprise *",
                key=f"gmail_company_{message_id}",
            )
            title = st.text_input(
                "Intitulé du poste *",
                value=subject,
                key=f"gmail_title_{message_id}",
            )
            recipient = st.text_input(
                "Email RH (facultatif)",
                key=f"gmail_recipient_{message_id}",
            )
            source_url = st.text_input(
                "Lien de l'offre (facultatif)",
                key=f"gmail_url_{message_id}",
            )
            description = st.text_area(
                "Description de l'offre *",
                value=body,
                height=180,
                key=f"gmail_description_{message_id}",
            )
            candidate = st.text_input(
                "Nom à afficher dans l'email",
                key=f"gmail_candidate_{message_id}",
            )
            language = st.selectbox(
                "Langue de candidature",
                ["fr", "en"],
                format_func=lambda x: (
                    "Français" if x == "fr" else "English"
                ),
                key=f"gmail_language_{message_id}",
            )

            analyze_email = st.form_submit_button(
                "Analyser et préparer le brouillon"
            )

        if analyze_email:
            if not company.strip() or not title.strip() or not description.strip():
                st.error(
                    "Renseigne l'entreprise, le poste et la description."
                )
            else:
                match = match_offer(title, description)
                cv_path = select_cv(match["role"])

                email_draft = generate_email(
                    company=company.strip(),
                    role=match["role_label"],
                    language=language,
                    candidate=candidate.strip() or "[Ton nom]",
                )

                st.session_state["draft"] = {
                    "company": company.strip(),
                    "title": title.strip(),
                    "recipient": recipient.strip(),
                    "source_url": source_url.strip(),
                    "description": description.strip(),
                    "role": match["role"],
                    "score": match["score"],
                    "language": language,
                    "subject": email_draft["subject"],
                    "body": email_draft["body"],
                    "cv_path": str(cv_path) if cv_path else "",
                    "status": "draft",
                }
                st.session_state["match"] = match

                st.success(
                    "Analyse terminée. Ouvre l'onglet "
                    "« Nouvelle candidature » pour vérifier le brouillon."
                )


with tab_spontaneous:
    st.subheader("Candidature spontanée")
    st.write(
        "Saisis l'adresse RH. L'entreprise et le poste sont facultatifs. "
        "Le CV et la lettre de motivation seront joints au message."
    )

    profile_options = {
        "Data Engineer": "data_engineer",
        "Data Scientist": "data_scientist",
        "BI Analyst": "bi_analyst",
        "AI Engineer": "ai_engineer",
    }

    with st.form("spontaneous_application_form"):
        recipient = st.text_input(
            "Adresse e-mail RH *",
            placeholder="recrutement@entreprise.ma",
        )
        profile_label = st.selectbox(
            "Profil ciblé",
            list(profile_options.keys()),
            index=0,
        )
        company = st.text_input(
            "Entreprise (facultatif)",
            placeholder="Nom de l'entreprise",
        )
        candidate = st.text_input(
            "Nom du candidat",
            value="Abderrahmane Ghassouine",
        )
        language = st.selectbox(
            "Langue",
            ["fr", "en"],
            format_func=lambda x: "Français" if x == "fr" else "English",
        )

        generate = st.form_submit_button(
            "Générer la candidature"
        )

    if generate:
        if not recipient.strip() or "@" not in recipient:
            st.error("Saisis une adresse e-mail RH valide.")
        else:
            role_key = profile_options[profile_label]
            cv_path = select_cv(role_key)

            if cv_path:
                cv_path = str(Path(cv_path).resolve())

            letter = generate_cover_letter(
                candidate=candidate.strip() or "Candidat",
                profile=profile_label,
                company=company.strip(),
                language=language,
            )

            if language == "en":
                subject = (
                    f"Spontaneous Application — Final-Year Internship "
                    f"in {profile_label}"
                )
                body = (
                    "Dear Hiring Team,\n\n"
                    f"I am currently pursuing a Master's degree in "
                    f"Big Data and Cloud Computing and would like to "
                    f"submit my spontaneous application for a final-year "
                    f"internship in {profile_label}.\n\n"
                    "Please find my CV and cover letter attached. "
                    "I would welcome the opportunity to discuss my "
                    "application with you.\n\n"
                    "Kind regards,\n"
                    f"{candidate.strip() or 'Candidate'}"
                )
            else:
                subject = (
                    f"Candidature spontanée — Stage PFE en {profile_label}"
                )
                body = (
                    "Madame, Monsieur,\n\n"
                    "Actuellement étudiant en Master Big Data et Cloud "
                    "Computing, je souhaite vous proposer ma candidature "
                    f"spontanée pour un stage PFE en {profile_label}.\n\n"
                    "Vous trouverez mon CV et ma lettre de motivation "
                    "en pièces jointes. Je serais heureux de pouvoir "
                    "échanger avec vous au sujet d'une éventuelle "
                    "opportunité au sein de votre entreprise.\n\n"
                    "Je vous remercie pour votre attention et reste "
                    "à votre disposition pour tout complément "
                    "d'information.\n\n"
                    "Cordialement,\n"
                    f"{candidate.strip() or 'Candidat'}"
                )

            # Réinitialiser les champs de prévisualisation précédents.
            for key in (
                "spont_subject",
                "spont_body",
                "spont_letter",
                "spont_confirm",
            ):
                st.session_state.pop(key, None)

            st.session_state["spontaneous_draft"] = {
                "recipient": recipient.strip(),
                "company": company.strip(),
                "profile": profile_label,
                "role_key": role_key,
                "cv_path": cv_path or "",
                "subject": subject,
                "body": body,
                "cover_letter": letter,
                "language": language,
                "candidate": candidate.strip() or "Candidat",
            }

    draft = st.session_state.get("spontaneous_draft")

    if draft:
        st.divider()
        st.subheader("Vérification avant envoi")

        st.write("**Destinataire :**", draft["recipient"])
        st.write("**Profil :**", draft["profile"])

        if draft["cv_path"] and Path(draft["cv_path"]).is_file():
            st.success(f"CV prêt : {Path(draft['cv_path']).name}")
        else:
            st.error(
                "Le CV de ce profil est introuvable. "
                "Ajoute le PDF correspondant au dossier cvs "
                "ou corrige le chemin dans config/profile.json."
            )

        edited_subject = st.text_input(
            "Objet de l'e-mail",
            value=draft["subject"],
            key="spont_subject",
        )
        edited_body = st.text_area(
            "Corps de l'e-mail",
            value=draft["body"],
            height=220,
            key="spont_body",
        )
        edited_letter = st.text_area(
            "Lettre de motivation (le texte sera joint en PDF)",
            value=draft["cover_letter"],
            height=320,
            key="spont_letter",
        )

        can_send = (
            bool(draft["cv_path"])
            and Path(draft["cv_path"]).is_file()
            and bool(draft["recipient"])
            and bool(edited_subject.strip())
            and bool(edited_body.strip())
            and bool(edited_letter.strip())
        )

        confirmed = st.checkbox(
            "Je confirme le destinataire, le contenu et les deux pièces "
            "jointes. Je souhaite envoyer réellement cette candidature.",
            key="spont_confirm",
        )

        if st.button(
            "Envoyer la candidature via Gmail",
            type="primary",
            disabled=not (can_send and confirmed),
        ):
            pdf_bytes = create_cover_letter_pdf(edited_letter)

            try:
                gmail_id = send_application_email(
                    recipient=draft["recipient"],
                    subject=edited_subject.strip(),
                    body=edited_body.strip(),
                    cv_path=draft["cv_path"],
                    cover_letter_pdf=pdf_bytes,
                )

                try:
                    record_spontaneous_application(
                        recipient=draft["recipient"],
                        company=draft["company"],
                        profile=draft["profile"],
                        subject=edited_subject.strip(),
                        body=edited_body.strip(),
                        cover_letter=edited_letter,
                        cv_path=draft["cv_path"],
                        status="sent",
                        gmail_message_id=gmail_id,
                    )
                except Exception as db_error:
                    st.error(
                        "Gmail a accepté l'envoi, mais l'enregistrement "
                        f"dans SQLite a échoué : {db_error}. "
                        f"Identifiant Gmail : {gmail_id}"
                    )
                else:
                    st.success(
                        "Candidature envoyée ! "
                        f"Identifiant Gmail : {gmail_id}"
                    )

                del st.session_state["spontaneous_draft"]
                for key in (
                    "spont_subject",
                    "spont_body",
                    "spont_letter",
                    "spont_confirm",
                ):
                    st.session_state.pop(key, None)

            except Exception as exc:
                try:
                    record_spontaneous_application(
                        recipient=draft["recipient"],
                        company=draft["company"],
                        profile=draft["profile"],
                        subject=edited_subject.strip(),
                        body=edited_body.strip(),
                        cover_letter=edited_letter,
                        cv_path=draft["cv_path"],
                        status="failed",
                        error_message=str(exc),
                    )
                except Exception as db_error:
                    st.error(
                        f"Échec de l'envoi : {exc}. "
                        f"Échec de l'enregistrement : {db_error}"
                    )
                else:
                    st.error(
                        f"Envoi échoué : {exc}. "
                        "La tentative a été enregistrée dans SQLite."
                    )

    st.divider()
    st.subheader("Historique des candidatures spontanées")

    history = list_spontaneous_applications()

    if history:
        st.dataframe(
            [
                {
                    "ID": item["id"],
                    "Destinataire": item["recipient"],
                    "Entreprise": item["company"],
                    "Profil": item["profile"],
                    "Objet": item["subject"],
                    "Statut": item["status"],
                    "Date": item["created_at"],
                    "Erreur": item["error_message"],
                }
                for item in history
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Aucune candidature spontanée enregistrée.")


with tab_tracking:
    st.subheader("Historique des candidatures")
    applications = list_applications()

    if applications:
        st.dataframe(
            [
                {
                    "ID": a["id"],
                    "Entreprise": a["company"],
                    "Poste": a["title"],
                    "Profil": a["role"],
                    "Score": a["score"],
                    "Statut": a["status"],
                    "Date": a["created_at"]
                }
                for a in applications
            ],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Aucune candidature enregistrée pour le moment.")
