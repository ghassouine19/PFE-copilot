
import hashlib
import re

import pandas as pd


REQUIRED_COLUMNS = {"company", "title", "description"}
OPTIONAL_COLUMNS = {"recipient", "source_url"}


def normalize(value: str) -> str:
    value = str(value or "").lower().strip()
    return re.sub(r"\s+", " ", value)


def make_offer_id(offer: dict) -> str:
    source_url = normalize(offer.get("source_url", ""))

    if source_url:
        identity = source_url
    else:
        identity = "|".join([
            normalize(offer.get("company", "")),
            normalize(offer.get("title", "")),
            normalize(offer.get("description", "")),
        ])

    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def load_offers_csv(file) -> list[dict]:
    df = pd.read_csv(file).fillna("")

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Colonnes manquantes : {', '.join(sorted(missing))}"
        )

    for column in OPTIONAL_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    offers = []
    seen = set()

    for row in df.to_dict(orient="records"):
        offer = {
            key: str(value).strip()
            for key, value in row.items()
        }

        if not offer["company"] or not offer["title"] or not offer["description"]:
            continue

        offer["offer_id"] = make_offer_id(offer)

        if offer["offer_id"] in seen:
            continue

        seen.add(offer["offer_id"])
        offers.append(offer)

    return offers


def import_stats(file) -> dict:
    df = pd.read_csv(file).fillna("")
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Colonnes manquantes : {', '.join(sorted(missing))}")
    valid_rows = sum(
        bool(str(row["company"]).strip() and str(row["title"]).strip() and str(row["description"]).strip())
        for _, row in df.iterrows()
    )
    if hasattr(file, "seek"):
        file.seek(0)
    offers = load_offers_csv(file)
    return {
        "total_rows": len(df),
        "valid_rows": valid_rows,
        "invalid_rows": len(df) - valid_rows,
        "duplicates": valid_rows - len(offers),
        "offers": offers,
    }
