
import pandas as pd


def load_offers_csv(file) -> list[dict]:
    """
    Charge les offres importées depuis un CSV.
    Colonnes attendues :
    company, title, description, recipient, source_url
    """
    df = pd.read_csv(file).fillna("")

    required = {"company", "title", "description"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Colonnes obligatoires manquantes : {', '.join(sorted(missing))}"
        )

    for column in ["recipient", "source_url"]:
        if column not in df.columns:
            df[column] = ""

    return df.to_dict(orient="records")
