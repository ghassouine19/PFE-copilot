
def send_application(
    recipient: str,
    subject: str,
    body: str,
    cv_path: str,
):
    """
    Envoi Gmail à implémenter après configuration OAuth 2.0.

    Ne jamais envoyer sans validation explicite de l'utilisateur.
    """
    raise NotImplementedError(
        "Gmail n'est pas encore connecté. "
        "Configure OAuth 2.0 avant tout envoi."
    )
