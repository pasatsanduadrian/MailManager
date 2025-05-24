import os
import pickle
import time
from pyngrok import ngrok
import gradio as gr
from threading import Thread
from flask import Flask, request, redirect, session
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from dotenv import load_dotenv

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

load_dotenv()
FLASK_PORT = int(os.getenv("FLASK_PORT", 5099))
GRADIO_PORT = int(os.getenv("GRADIO_PORT", 7070))
NGROK_TOKEN = os.getenv("NGROK_TOKEN")
NGROK_HOSTNAME = os.getenv("NGROK_HOSTNAME")
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.pickle'
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
SECRET_KEY = os.getenv("SECRET_KEY", "abc123")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 1. Flask APP (OAuth)
app = Flask(__name__)
app.secret_key = SECRET_KEY

@app.route("/")
def index():
    return """<div style='text-align:center; margin-top:32px; font-family:sans-serif;'>
    <img src='https://upload.wikimedia.org/wikipedia/commons/4/4e/Gmail_Icon.png' style='width:60px; margin-bottom:16px;'/>
    <h2 style='color:#d93025;'>MailManager</h2>
    <p>Server OAuth2 Gmail (stable ngrok link)</p>
    <a href='/auth' style='background:#1a73e8; color:white; padding:10px 30px; border-radius:6px; text-decoration:none;'>🔐 Autentificare Gmail</a>
    </div>"""

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
    return "<h3 style='color:green;'>PAS /oauth2callback - Token salvat. Autentificare reușită!<br>Poți închide acest tab și reveni în Gradio.</h3>"

# 2. PORNIRE NGROK + FLASK
ngrok.set_auth_token(NGROK_TOKEN)
public_url = ngrok.connect(FLASK_PORT, "http", hostname=NGROK_HOSTNAME)
print("Ngrok stable link:", public_url)
print(f"Adaugă la Google Console: {public_url}/oauth2callback")

def run_flask():
    app.run(port=FLASK_PORT, host="0.0.0.0")

flask_thread = Thread(target=run_flask)
flask_thread.start()
time.sleep(5)

# 3. Gmail & Gemini Utils
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

def parse_inbox(max_results=10):
    service = get_gmail_service()
    if not service:
        return []
    response = service.users().messages().list(userId='me', maxResults=max_results).execute()
    messages = response.get('messages', [])
    result = []
    for msg in messages:
        meta = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['From', 'Subject', 'Date', 'Labels']).execute()
        headers = {h['name']: h['value'] for h in meta['payload']['headers']}
        labels = meta.get('labelIds', [])
        result.append({
            "From": headers.get("From", ""),
            "Subject": headers.get("Subject", ""),
            "Date": headers.get("Date", ""),
            "Labels": ", ".join(labels)
        })
    return result

def get_labels():
    service = get_gmail_service()
    if not service:
        return []
    res = service.users().labels().list(userId='me').execute()
    return [label['name'] for label in res.get('labels', [])]

def gemini_label_emails(email_list):
    if not GEMINI_API_KEY:
        return "Nu există cheie Gemini API configurată în .env!"
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash-latest")
    prompt = (
        "Primești o listă de emailuri cu metadate (From, Subject, Date).\n"
        "Propune o etichetă/categorie pentru fiecare, răspunde în format tabel Markdown cu coloanele: From | Subject | Date | Etichetă propusă.\n"
        "Dacă nu poți propune etichetă, lasă '-' la Etichetă propusă.\n\n"
    )
    for mail in email_list:
        prompt += f"From: {mail['From']}\nSubject: {mail['Subject']}\nDate: {mail['Date']}\n\n"
    prompt += "\nReturnează DOAR tabelul Markdown, fără explicații."
    out = model.generate_content(prompt)
    return out.text if hasattr(out, "text") else str(out)

# 4. GRADIO UI
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    <div style='text-align:center; margin-bottom:6px;'>
        <img src='https://upload.wikimedia.org/wikipedia/commons/4/4e/Gmail_Icon.png' style='width:48px; vertical-align:middle;'/>
        <span style='font-size:2.2em; font-weight:600; color:#1a73e8;'>MailManager</span>
    </div>
    <p style='text-align:center; color:#666;'>Autentificare Gmail, vizualizare inbox și categorii Gemini AI<br>—</p>
    """)

    auth_status = gr.Markdown("Pasul 1: Click <b>Authenticate Gmail</b> și autorizează aplicația.")
    with gr.Row():
        auth_btn = gr.Button("🔐 Authenticate Gmail")
        check_btn = gr.Button("🔍 Check Auth Status")
    with gr.Row():
        inbox_btn = gr.Button("📥 Inbox (tabel, 10 emailuri)")
        inbox_output = gr.Dataframe(label="Inbox (Ultimele 10 emailuri)", interactive=False, wrap=True)
    with gr.Row():
        gemini_btn = gr.Button("✨ Categorize Inbox cu Gemini", visible=True)
        gemini_out = gr.Markdown("Aici vor apărea categoriile Gemini pentru inbox.")
    with gr.Row():
        labels_btn = gr.Button("🏷️ List Gmail Labels")
        labels_out = gr.Textbox(label="Gmail Labels", lines=3)

    def authenticate_gmail():
        auth_url = f"https://{NGROK_HOSTNAME}/auth"
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, "rb") as token:
                    creds = pickle.load(token)
                if creds and creds.valid:
                    return f"✅ Ești deja autentificat!<br><a href='{auth_url}' target='_blank'>Reautentifică (dacă vrei)"
            except Exception as e:
                return f"❌ Eroare la token: {e}. Click <a href='{auth_url}' target='_blank'>pentru autentificare."
        return f"Click <a href='{auth_url}' target='_blank'>aici</a> pentru autentificare Gmail (OAuth2)."

    def check_auth_status():
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, 'rb') as token_file:
                    creds = pickle.load(token_file)
                if creds and creds.valid:
                    return "✅ Successfully authenticated!"
                elif creds and creds.expired and creds.refresh_token:
                    return "⚠️ Token expired, but refreshable."
                else:
                    return "❌ Token invalid. Reautentifică."
            except Exception as e:
                return f"❌ Eroare token: {e}."
        return "❌ Not authenticated."

    def get_inbox_df():
        import pandas as pd
        emails = parse_inbox(10)
        if not emails:
            return pd.DataFrame([{"Inbox": "Neautentificat sau inbox gol!"}])
        return pd.DataFrame(emails)

    def gemini_categorize():
        emails = parse_inbox(6)
        if not emails:
            return "Inbox gol sau neautentificat!"
        markdown_table = gemini_label_emails(emails)
        # Render as markdown for color and layout
        return "### 📊 Categorii AI Gemini pentru inbox:\n\n" + markdown_table

    def get_labels_md():
        labs = get_labels()
        if not labs:
            return "Nicio etichetă găsită sau nu ești autentificat."
        return "\n".join([f"🏷️ {x}" for x in labs])

    # Legături UI <-> funcții
    auth_btn.click(authenticate_gmail, outputs=auth_status)
    check_btn.click(check_auth_status, outputs=auth_status)
    inbox_btn.click(get_inbox_df, outputs=inbox_output)
    gemini_btn.click(gemini_categorize, outputs=gemini_out)
    labels_btn.click(get_labels_md, outputs=labels_out)

    gr.Markdown("""
    ---
    <details>
      <summary><b>Instrucțiuni (click pentru detalii)</b></summary>
      <ol>
        <li>Rulează cu <code>.env</code> și <code>credentials.json</code> setat + redirect-uri corecte.</li>
        <li>Autentifică-te cu Gmail &rarr; vezi inbox &rarr; Categorizează cu Gemini AI.</li>
        <li>Pentru Gemini, setează cheie în <code>.env</code> la <b>GEMINI_API_KEY</b>.</li>
      </ol>
    </details>
    """)

if __name__ == "__main__":
    print("Gradio app running.")
    demo.launch(share=True, server_port=GRADIO_PORT)
