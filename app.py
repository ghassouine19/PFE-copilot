
import streamlit as st

from src.database import init_db, add_application, list_applications
from src.matcher import match_offer, load_profile
from src.cv_selector import select_cv
from src.email_generator import generate_email

from src.job_sources import load_offers_csv

st.set_page_config(
    page_title="PFE Copilot",
    page_icon="🎓",
    layout="wide"
)

init_db()
profile = load_profile()

st.title("🎓 PFE Copilot")
st.caption(
    "Assistant de candidature PFE — Master Big Data & Cloud Computing"
)

tab_new, tab_import, tab_tracking = st.tabs(
    [
        "Nouvelle candidature",
        "Importer des offres",
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
