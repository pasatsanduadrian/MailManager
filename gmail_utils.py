# gmail_utils.py
import os
import pickle
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

TOKEN_FILE = "token.pickle"

def get_gmail_service():
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE, "rb") as f:
        creds = pickle.load(f)
    if creds and creds.valid:
        return build("gmail", "v1", credentials=creds)
    elif creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
        return build("gmail", "v1", credentials=creds)
    return None

def list_labels(service):
    results = service.users().labels().list(userId='me').execute()
    return results.get('labels', [])

def get_emails_for_label(service, label_id, max_results=100):
    results = service.users().messages().list(userId='me', labelIds=[label_id], maxResults=max_results).execute()
    messages = results.get('messages', [])
    emails = []
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['From','Subject','Date']).execute()
        headers = {h['name']: h['value'] for h in msg_data.get('payload', {}).get('headers', [])}
        emails.append({
            'id': msg['id'],
            'from': headers.get('From', ''),
            'subject': headers.get('Subject', ''),
            'date': headers.get('Date', ''),
            'label': label_id
        })
    return emails

def get_inbox_messages(service, max_results=100):
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=max_results).execute()
    messages = results.get('messages', [])
    emails = []
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['From','Subject','Date']).execute()
        headers = {h['name']: h['value'] for h in msg_data.get('payload', {}).get('headers', [])}
        emails.append({
            'id': msg['id'],
            'from': headers.get('From', ''),
            'subject': headers.get('Subject', ''),
            'date': headers.get('Date', '')
        })
    return emails

def move_email_to_label(service, msg_id, label_name):
    """Mută email la un label; creează label dacă nu există."""
    # Găsește sau creează label
    labels = list_labels(service)
    label_id = None
    for lbl in labels:
        if lbl['name'] == label_name:
            label_id = lbl['id']
            break
    if not label_id:
        label_obj = service.users().labels().create(userId='me', body={'name': label_name, 'labelListVisibility':'labelShow', 'messageListVisibility':'show'}).execute()
        label_id = label_obj['id']
    try:
        service.users().messages().modify(userId='me', id=msg_id, body={"addLabelIds": [label_id], "removeLabelIds": ['INBOX']}).execute()
        return True
    except Exception as e:
        print("Eroare la mutare:", e)
        return False
