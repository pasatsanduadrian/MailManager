# rules_generator.py
import json
from gmail_utils import get_gmail_service, list_labels, get_emails_for_label

def generate_rules_from_labels(max_results=100):
    service = get_gmail_service()
    if not service:
        return {}
    labels = list_labels(service)
    rules = {}
    for label in labels:
        # Excludem labeluri standard (INBOX, SENT etc.)
        if label['type'] != 'user':
            continue
        emails = get_emails_for_label(service, label['id'], max_results)
        senders = set()
        for email in emails:
            sender = email['from']
            if sender:
                senders.add(sender)
        if senders:
            rules[label['name']] = list(senders)
    # Poți salva ca rules.json dacă vrei
    with open("rules.json", "w") as f:
        json.dump(rules, f, indent=2)
    return rules
