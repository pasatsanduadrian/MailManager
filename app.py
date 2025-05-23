!pip install flask pyngrok google-auth google-auth-oauthlib google-api-python-client gradio --quiet

import os
import pickle
import time
import subprocess
from pyngrok import ngrok
import gradio as gr
from threading import Thread
from flask import Flask, request, redirect, session
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request

# --- CONFIG ---
FLASK_PORT = 5099
GRADIO_PORT = 7070
NGROK_TOKEN = "2cG2rxJFIVn5C7WH1QJjo1wzJML_t9S5469X8q9E9VeEZbhP"
NGROK_HOSTNAME = "stable-guided-buck.ngrok-free.app"
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.pickle'
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
SECRET_KEY = os.urandom(24)

# --- 1. Flask APP (OAuth) ---
app = Flask(__name__)
app.secret_key = SECRET_KEY

@app.route("/")
def index():
    return "<h2>Gmail API OAuth2 server is running.<br>This server handles OAuth for the Gradio app.</h2>"

@app.route("/auth")
def auth():
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=f"https://{NGROK_HOSTNAME}/oauth2callback"
    )
    auth_url, state = flow.authorization_url(prompt='consent', access_type='offline')
    session['state'] = state
    return redirect(auth_url)

@app.route("/oauth2callback")
def oauth2callback():
    state = session.get('state')
    if not state:
        return "Missing OAuth state! Please restart the authentication.", 400
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=f"https://{NGROK_HOSTNAME}/oauth2callback",
        state=state
    )
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    with open(TOKEN_FILE, "wb") as token:
        pickle.dump(creds, token)
    return "<h3>PAS /oauth2callback - Token salvat. Autentificare reușită!<br>Poți închide acest tab și reveni în Gradio.</h3>"

# --- 2. PORNIRE NGROK + FLASK ---
ngrok.set_auth_token(NGROK_TOKEN)
public_url = ngrok.connect(FLASK_PORT, "http", hostname=NGROK_HOSTNAME)
print("Ngrok stable link:", public_url)
print(f"Adaugă la Google Console: {public_url}/oauth2callback")

def run_flask():
    app.run(port=FLASK_PORT, host="0.0.0.0")

flask_thread = Thread(target=run_flask)
flask_thread.start()
time.sleep(5) # Lasă Flask să pornească

# --- 3. GRADIO FRONTEND ---
def authenticate_gmail():
    """Trimite utilizatorul să înceapă autentificarea Gmail."""
    auth_url = f"https://{NGROK_HOSTNAME}/auth"
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "rb") as token:
                creds = pickle.load(token)
            if creds and creds.valid:
                return f"✅ Ești deja autentificat cu Gmail API!<br><a href='{auth_url}' target='_blank'>Reautentifică (dacă vrei)</a>"
            elif creds and creds.expired and creds.refresh_token:
                return f"⚠️ Tokenul a expirat, dar e reîmprospătabil. Click <a href='{auth_url}' target='_blank'>aici</a> pentru reautentificare."
        except Exception as e:
            return f"❌ Eroare la încărcarea tokenului: {e}. Click <a href='{auth_url}' target='_blank'>aici</a> pentru autentificare."
    return f"Click <a href='{auth_url}' target='_blank'>aici</a> pentru a începe autentificarea Gmail (OAuth2)."

def check_auth_status():
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'rb') as token_file:
                creds = pickle.load(token_file)
            if creds and creds.valid:
                return "✅ Successfully authenticated with Gmail API!"
            elif creds and creds.expired and creds.refresh_token:
                return "⚠️ Token expired, but refreshable. Try re-authenticating."
            else:
                return "❌ Token found but invalid/unrefreshable. Please re-authenticate."
        except Exception as e:
            return f"❌ Error loading token file: {e}. Please re-authenticate."
    return "❌ Not authenticated with Gmail API."

def get_gmail_service():
    from googleapiclient.discovery import build
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
        if creds and creds.valid:
            return build('gmail', 'v1', credentials=creds)
        elif creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
            return build('gmail', 'v1', credentials=creds)
    return None

def fetch_gmail_labels():
    service = get_gmail_service()
    if service:
        try:
            results = service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            if not labels:
                return "No labels found."
            else:
                label_names = [label['name'] for label in labels]
                return "Your Gmail Labels:\n" + "\n".join(label_names[:10]) + ("..." if len(label_names) > 10 else "")
        except Exception as e:
            return f"Error fetching labels: {e}. Is your token valid?"
    return "Not authenticated or service unavailable. Please authenticate first."

with gr.Blocks() as demo:
    gr.Markdown("# Gmail API Authentication with Gradio & Ngrok Stable Link")
    gr.Markdown("Autentificare Gmail API cu stable ngrok (OAuth2) și Gradio UI.")

    with gr.Row():
        auth_btn = gr.Button("Authenticate Gmail")
        auth_status_output = gr.Markdown("Click 'Authenticate Gmail' să începi.")

    with gr.Row():
        check_status_btn = gr.Button("Check Authentication Status")
        current_status_output = gr.Markdown("Status: Not checked.")

    with gr.Row():
        fetch_labels_btn = gr.Button("Fetch Gmail Labels (Requires Auth)")
        labels_output = gr.Textbox(label="Gmail Labels", lines=10)

    auth_btn.click(authenticate_gmail, outputs=auth_status_output)
    check_status_btn.click(check_auth_status, outputs=current_status_output)
    fetch_labels_btn.click(fetch_gmail_labels, outputs=labels_output)

    gr.Markdown(f"""
    ---
    **Instrucțiuni:**  
    1. Asigură-te că `credentials.json` e în același folder cu scriptul.  
    2. Pune la Google Cloud Console, la OAuth redirect-uri, EXACT:  
       `https://{NGROK_HOSTNAME}/oauth2callback`  
    3. Apasă "Authenticate Gmail" și urmează pașii.  
    4. După succes, verifică cu "Check Authentication Status" și apoi "Fetch Gmail Labels".
    """)

print("Gradio app running.")
demo.launch(share=True, server_port=GRADIO_PORT)
