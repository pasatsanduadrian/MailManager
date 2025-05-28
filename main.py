import os
import pickle
import time
from threading import Thread
from dotenv import load_dotenv
from pyngrok import ngrok
from flask import Flask, request, redirect, session
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import gradio as gr
import pandas as pd
import matplotlib.pyplot as plt
import io

from gmail_utils import get_gmail_service
from export_gmail_to_xlsx import export_labels_and_inbox_xlsx
from move_from_xlsx import move_emails_from_xlsx
from gemini_utils import summarize_with_gemini

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Config ---
FLASK_PORT = int(os.getenv("FLASK_PORT", 5099))
GRADIO_PORT = int(os.getenv("GRADIO_PORT", 7070))
NGROK_TOKEN = os.getenv("NGROK_TOKEN")
NGROK_HOSTNAME = os.getenv("NGROK_HOSTNAME")  # ex: stable-guided-buck.ngrok-free.app
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.pickle'
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
SECRET_KEY = os.getenv("SECRET_KEY", "abc123")

# --- Flask pentru OAuth2 ---
app = Flask(__name__)
app.secret_key = SECRET_KEY

@app.route("/")
def index():
    return """
    <div style='text-align:center;margin-top:32px;'>
      <h2 style='color:#1a73e8;'>MailManager - Gmail OAuth2</h2>
      <a href='/auth' style='font-size:1.3em;background:#1a73e8;color:white;padding:12px 36px;border-radius:8px;text-decoration:none;'>🔐 Autentificare Gmail</a>
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

# --- Pornește Flask pe thread separat + ngrok stable ---
ngrok.set_auth_token(NGROK_TOKEN)
public_url = ngrok.connect(FLASK_PORT, "http", hostname=NGROK_HOSTNAME)
print("Ngrok stable link:", public_url)
print(f"Adaugă la Google Console: {public_url}/oauth2callback")

def run_flask():
    app.run(port=FLASK_PORT, host="0.0.0.0")

flask_thread = Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()
time.sleep(5)

# --- Gradio UI functions ---

def check_auth():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            try:
                creds = pickle.load(f)
                if creds and creds.valid:
                    return "✅ Ești autentificat cu Gmail!"
            except Exception as e:
                return f"Eroare token: {e}"
    return ("❌ Nu ești autentificat. Click butonul de mai jos pentru autentificare și urmează pașii în browser.")

def open_auth_link():
    return f"Deschide <a href='https://{NGROK_HOSTNAME}/auth' target='_blank'>aici</a> pentru autentificare Gmail (OAuth2)."

def export_xlsx_ui(_):  # _ = ignoră inputul, îl cere doar pentru compatibilitate UI
    service = get_gmail_service()
    if not service:
        return None, "Eroare: nu ești autentificat Gmail!"
    path = "gmail_labels_inbox.xlsx"
    export_labels_and_inbox_xlsx(service, path)   # FĂRĂ inbox_max, pentru all
    return path, f"Export XLSX gata: {path}"

def move_xlsx_ui(file):
    service = get_gmail_service()
    if not service:
        return "Eroare: nu ești autentificat Gmail!"
    move_emails_from_xlsx(service, file.name)
    return "Mutare finalizată! (vezi Gmail)"

# -- New: Statistics & Gemini Tab --
def labels_stats_ui():
    service = get_gmail_service()
    labels = service.users().labels().list(userId='me').execute().get('labels', [])
    stats = []
    for l in labels:
        if l.get("type") == "user":
            count = service.users().messages().list(userId='me', labelIds=[l['id']], maxResults=1000).execute().get('resultSizeEstimate', 0)
            stats.append({'Label': l['name'], 'Count': count})
    df = pd.DataFrame(stats)
    # Grafic
    fig, ax = plt.subplots(figsize=(8,3))
    bars = ax.bar(df['Label'], df['Count'], color='#1a73e8', alpha=0.85)
    ax.set_ylabel("Nr. mailuri", fontsize=11)
    ax.set_xlabel("Label", fontsize=11)
    ax.set_title("Distribuție mailuri pe labeluri Gmail", fontsize=13, color="#1a73e8")
    plt.setp(ax.get_xticklabels(), rotation=40, ha="right", fontsize=9)
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f"{int(height)}", xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0,3), textcoords="offset points", ha='center', va='bottom', fontsize=9)
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    return df, buf

def inbox_stats_ui():
    service = get_gmail_service()
    inbox_msgs = []
    page_token = None
    while True:
        resp = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=500, pageToken=page_token).execute()
        inbox_msgs.extend(resp.get('messages', []))
        page_token = resp.get('nextPageToken')
        if not page_token:
            break
    counter = len(inbox_msgs)
    return f"Total mailuri în inbox: {counter}"

def gemini_inbox_summary():
    service = get_gmail_service()
    msgs = []
    page_token = None
    # Extragem doar ultimele 50 pentru Gemini
    while len(msgs) < 50:
        resp = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=50, pageToken=page_token).execute()
        batch = resp.get('messages', [])
        msgs.extend(batch)
        page_token = resp.get('nextPageToken')
        if not page_token or len(msgs) >= 50:
            break
    subjects = []
    for m in msgs[:50]:
        meta = service.users().messages().get(userId='me', id=m['id'], format='metadata', metadataHeaders=['Subject']).execute()
        hdr = {h['name']: h['value'] for h in meta.get('payload', {}).get('headers', [])}
        subj = hdr.get('Subject', '[fără subiect]')
        subjects.append(subj)
    summary = summarize_with_gemini(subjects, GEMINI_API_KEY)
    return summary

# --- Gradio App UI ---
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    <h2 style='color:#1a73e8'>MailManager – Gmail OAuth2 + Workflow Inbox/Labels & Gemini Stats</h2>
    <ol>
    <li>Click pe butonul de autentificare, urmează pașii din browser (vei genera token.pickle)</li>
    <li>Exportă inbox și labels în XLSX (download)</li>
    <li>Editează manual sheet-ul Inbox (coloana Label) în Excel</li>
    <li>Încarcă XLSX modificat și rulează mutarea automată a mailurilor în Labels</li>
    </ol>
    <hr>
    """)
    auth_status = gr.Markdown(check_auth())
    auth_btn = gr.Button("🔐 Deschide autentificarea Gmail în browser")
    auth_btn.click(open_auth_link, outputs=auth_status)

    with gr.Tab("Export & Mutare"):
        gr.Markdown("### 1️⃣ Exportă Labels & Inbox în XLSX pentru editare")
        exp_btn = gr.Button("Export XLSX")
        exp_file = gr.File(label="Fișierul XLSX generat pentru download", interactive=False)
        exp_msg = gr.Textbox(label="Status export", lines=1)
        exp_btn.click(fn=export_xlsx_ui, outputs=[exp_file, exp_msg])

        gr.Markdown("### 2️⃣ Încarcă XLSX editat pentru mutare automată în Labels")
        upl_file = gr.File(label="Încarcă XLSX editat (Inbox cu labeluri)", file_types=['.xlsx'])
        move_btn = gr.Button("Mută automat emailurile din fișier")
        move_msg = gr.Textbox(label="Status mutare", lines=2)
        move_btn.click(fn=move_xlsx_ui, inputs=upl_file, outputs=move_msg)

    with gr.Tab("Statistici & Gemini"):
        gr.Markdown("#### Distribuție pe labeluri și sumarizare Inbox cu Gemini")
        lbl_btn = gr.Button("Afișează distribuție labeluri & grafic")
        lbl_df = gr.Dataframe(label="Statistici Labeluri", interactive=False)
        lbl_img = gr.Image(label="Grafic distribuție")
        lbl_btn.click(labels_stats_ui, outputs=[lbl_df, lbl_img])

        inbox_btn = gr.Button("Afișează număr mailuri Inbox")
        inbox_out = gr.Textbox(label="Nr. mailuri Inbox")
        inbox_btn.click(inbox_stats_ui, outputs=inbox_out)

        gemini_btn = gr.Button("Sumarizează ultimele 50 de mailuri Inbox (Gemini)")
        gemini_out = gr.Textbox(label="Sumar Gemini Inbox", lines=10)
        gemini_btn.click(gemini_inbox_summary, outputs=gemini_out)

    gr.Markdown("""
    ---
    <details>
    <summary><b>Instrucțiuni complete</b></summary>
    <ol>
      <li>Click pe butonul de autentificare Gmail de mai sus și urmează pașii din browser (vei genera <code>token.pickle</code>).</li>
      <li>Folosește butonul de export pentru a salva un fișier XLSX cu două sheet-uri (<b>Labels</b> și <b>Inbox</b>).</li>
      <li>Deschide fișierul în Excel și completează/editează coloana <b>Label</b> din sheet Inbox.</li>
      <li>Încarcă fișierul modificat și apasă <b>Mută automat emailurile</b>.</li>
      <li>Pentru statistici și sumar Inbox: folosește tabul „Statistici & Gemini”.</li>
    </ol>
    </details>
    """)

if __name__ == "__main__":
    demo.launch(share=True, server_port=7070)
