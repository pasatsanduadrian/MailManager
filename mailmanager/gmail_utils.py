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

def get_inbox_table(service, max_results=100):
    """
    Returnează o listă cu dicturi pentru cele mai noi emailuri (From, Subject, Date, ID, snippet).
    """
    messages = service.users().messages().list(
        userId='me', labelIds=['INBOX'], maxResults=max_results
    ).execute().get('messages', [])
    out = []
    for m in messages:
        msg = service.users().messages().get(
            userId='me', id=m['id'],
            format='metadata',
            metadataHeaders=['From', 'Subject', 'Date']
        ).execute()
        headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
        snippet = msg.get('snippet', '')
        out.append({
            'id': m['id'],
            'from': headers.get('From', ''),
            'subject': headers.get('Subject', ''),
            'date': headers.get('Date', ''),
            'snippet': snippet
        })
    return out
