# gemini_labeler.py
from .gemini_utils import gemini_label_emails

def label_inbox_with_gemini(service, rules, api_key, max_inbox=200):
    # 1. Fetch emails cu id, from, subject, date
    inbox = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=max_inbox).execute().get('messages', [])
    emails = []
    for m in inbox:
        msg = service.users().messages().get(userId='me', id=m['id'], format='metadata', metadataHeaders=['From','Subject','Date']).execute()
        headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
        emails.append({
            "id": m['id'],  # <-- adăugat id!
            "from": headers.get('From', ''),
            "subject": headers.get('Subject', ''),
            "date": headers.get('Date', '')
        })
    # 2. Trimite la Gemini doar câmpurile relevante
    gemini_input = [{"from": e["from"], "subject": e["subject"], "date": e["date"]} for e in emails]
    predictions = gemini_label_emails(gemini_input, api_key, context_rules=rules)
    # 3. Asociere predicții la id (merge pe poziție, dacă lungimile coincid)
    results = []
    for idx, pred in enumerate(predictions):
        # pred = {"from":..., "subject":..., "date":..., "label":...}
        entry = {**pred}
        if idx < len(emails):
            entry["id"] = emails[idx]["id"]
        results.append(entry)
    return results
