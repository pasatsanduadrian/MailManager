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
