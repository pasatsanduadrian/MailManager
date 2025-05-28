# rules_from_labels.py
def generate_rules_from_labels(service, max_per_label=300):
    """
    Generează reguli JSON pe baza labelurilor existente, asociind fiecare label cu lista adreselor de email
    care apar în respectivele labeluri (max_per_label = câte emailuri citește din fiecare label).
    """
    labels = service.users().labels().list(userId='me').execute().get('labels', [])
    label_rules = []
    for label in labels:
        if label.get("type") != "user":
            continue
        label_id = label["id"]
        # extrage mailuri pentru fiecare label
        try:
            messages = service.users().messages().list(userId='me', labelIds=[label_id], maxResults=max_per_label).execute().get('messages', [])
        except Exception:
            messages = []
        senders = set()
        for m in messages:
            try:
                msg = service.users().messages().get(userId='me', id=m['id'], format='metadata', metadataHeaders=['From']).execute()
                headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
                senders.add(headers.get('From', ''))
            except Exception:
                continue
        if senders:
            label_rules.append({"label": label["name"], "senders": list(senders)})
    return label_rules
