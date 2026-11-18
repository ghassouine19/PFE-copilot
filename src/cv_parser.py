from pathlib import Path

import fitz


def extract_pdf_text(pdf_path: str | Path) -> str:
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(f"PDF introuvable : {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError("Le CV doit être au format PDF.")
    if path.stat().st_size > 10 * 1024 * 1024:
        raise ValueError("Le PDF dépasse la taille maximale autorisée de 10 Mo.")

    parts = []
    with fitz.open(path) as document:
        for page in document:
            parts.append(page.get_text("text"))
    return "\n".join(parts).strip()
