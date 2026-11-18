
from src.gmail_reader import search_offer_emails

emails = search_offer_emails(max_results=10)

print(f"{len(emails)} email(s) récupéré(s).")

for email in emails:
    print("-" * 50)
    print("Expéditeur :", email["sender"])
    print("Objet :", email["subject"])
    print("Date :", email["date"])
    print("Longueur du corps :", len(email["body"]))
    print("Corps complet :", repr(email["body"][:1000]))