import os
import pickle
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

TOKEN_FILE = "token.pickle"

def get_gmail_service():
    """
    Returnează serviciul Gmail API folosind tokenul OAuth2 salvat.
    """
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

def get_inbox_messages(service, max_results=10):
    """
    Extrage cele mai recente emailuri din Inbox.
    """
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=max_results).execute()
    messages = results.get('messages', [])
    return messages

def get_message_metadata(service, msg_id):
    """
    Returnează un dict cu metadate pentru un mesaj.
    """
    msg = service.users().messages().get(userId='me', id=msg_id, format='metadata', metadataHeaders=['From','Subject','Date']).execute()
    headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
    return {
        'id': msg_id,
        'from': headers.get('From', ''),
        'subject': headers.get('Subject', ''),
        'date': headers.get('Date', ''),
    }

def get_inbox_table(service, max_results=10):
    """
    Returnează o listă cu dicturi pentru cele mai noi emailuri (From, Subject, Date).
    """
    messages = get_inbox_messages(service, max_results)
    out = []
    for m in messages:
        meta = get_message_metadata(service, m['id'])
        out.append(meta)
    return out

def get_labels(service):
    """
    Returnează lista tuturor labelurilor (doar nume).
    """
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])
    return [label['name'] for label in labels]

def get_label_id(service, label_name):
    """
    Returnează ID-ul labelului după nume sau îl creează dacă nu există.
    """
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])
    for label in labels:
        if label['name'].lower() == label_name.lower():
            return label['id']
    # Dacă nu există, îl creează:
    label_body = {
        "name": label_name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show"
    }
    created = service.users().labels().create(userId='me', body=label_body).execute()
    return created['id']

def move_email_to_label(service, msg_id, label_name):
    """
    Mută un email pe labelul dorit. Creează labelul dacă nu există.
    """
    try:
        label_id = get_label_id(service, label_name)
        # Scoate INBOX, adaugă label nou
        service.users().messages().modify(
            userId='me',
            id=msg_id,
            body={
                "addLabelIds": [label_id],
                "removeLabelIds": ["INBOX"]
            }
        ).execute()
        return True
    except Exception as e:
        print(f"Eroare la mutare email {msg_id} pe label {label_name}: {e}")
        return False
