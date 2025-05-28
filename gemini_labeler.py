# gemini_labeler.py
from gemini_utils import gemini_label_emails

def label_inbox_with_gemini(service, rules, api_key, max_inbox=200):
    """
    Prinde inboxul, îl structurează ca listă dict cu from, subject, date, și apelează Gemini pentru fiecare,
    transmițând și regulile existente ca context.
    """
    messages = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=max_inbox).execute().get('messages', [])
    inbox_list = []
    for m in messages:
        try:
            msg = service.users().messages().get(userId='me', id=m['id'], format='metadata', metadataHeaders=['From','Subject','Date']).execute()
            headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
            inbox_list.append({
                "from": headers.get('From', ''),
                "subject": headers.get('Subject', ''),
                "date": headers.get('Date', ''),
                "id": m['id'],
            })
        except Exception:
            continue
    # Apel Gemini cu contextul regulilor și lista de inbox
    results = gemini_label_emails(inbox_list, api_key, context_rules=rules)
    return results  # listă dict {from, subject, date, id, label}
