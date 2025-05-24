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
import pandas as pd
import json

from gmail_utils import get_gmail_service, list_labels, move_email_to_label
from rules_generator import generate_rules_from_labels
from inbox_parser import parse_inbox_and_match
from gemini_utils import gemini_label_emails

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
load_dotenv()

FLASK_PORT = int(os.getenv("FLASK_PORT", 5099))
GRADIO_PORT = int(os.getenv("GRADIO_PORT", 7070))
NGROK_TOKEN = os.getenv("NGROK_TOKEN")
NGROK_HOSTNAME = os.getenv("NGROK_HOSTNAME")
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.pickle'
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
SECRET_KEY = os.getenv("SECRET_KEY", "abc123")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Flask APP (OAuth)
app = Flask(__name__)
app.secret_key = SECRET_KEY

@app.route("/")
def index():
    return "<h2>MailManager server OAuth is running.</h2>"

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

# NGROK + Flask thread
ngrok.set_auth_token(NGROK_TOKEN)
public_url = ngrok.connect(FLASK_PORT, "http", hostname=NGROK_HOSTNAME)
print("Ngrok stable link:", public_url)
def run_flask(): app.run(port=FLASK_PORT, host="0.0.0.0")
flask_thread = Thread(target=run_flask)
flask_thread.start()
time.sleep(5)

# ----- LOGIC FUNCȚII -----
def check_gmail_auth():
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "rb") as token:
                creds = pickle.load(token)
            if creds and creds.valid:
                return "✅ Ești deja autentificat!"
        except Exception as e:
            return f"❌ Eroare la token: {e}."
    return "❌ Nu ești autentificat."

def open_auth_link():
    return f"Deschide linkul <a href='https://{NGROK_HOSTNAME}/auth' target='_blank'>aici</a> pentru autentificare Gmail (OAuth2)."

def show_labels():
    service = get_gmail_service()
    if not service:
        return pd.DataFrame([{"Label": "Neautentificat!"}])
    labs = list_labels(service)
    rows = []
    for lab in labs:
        if lab["type"] == "user":
            rows.append({"Label": lab["name"], "ID": lab["id"]})
    return pd.DataFrame(rows)

def show_labels_senders(max_results=100):
    service = get_gmail_service()
    if not service:
        return pd.DataFrame([{"Label": "Neautentificat!"}])
    labs = list_labels(service)
    rows = []
    for lab in labs:
        if lab["type"] != "user":
            continue
        froms = set()
        from gmail_utils import get_emails_for_label
        emails = get_emails_for_label(service, lab['id'], max_results)
        for e in emails:
            froms.add(e['from'])
        if froms:
            for addr in froms:
                rows.append({"Label": lab["name"], "Sender": addr})
    return pd.DataFrame(rows)

def show_rules_json():
    rules = generate_rules_from_labels(max_results=100)
    return json.dumps(rules, indent=2, ensure_ascii=False)

def parse_inbox_to_df():
    try:
        # Încarcă regulile generate
        with open("rules.json") as f:
            rules_dict = json.load(f)
    except Exception:
        rules_dict = generate_rules_from_labels(max_results=100)
    rows = parse_inbox_and_match(rules_dict, max_results=100)
    return pd.DataFrame(rows)

def send_none_to_gemini(table):
    if isinstance(table, list):
        df = pd.DataFrame(table)
    else:
        df = table.copy()
    to_ai = df[df["Label"].isnull() | (df["Label"] == "") | (df["Label"] == "None")]
    if to_ai.empty:
        return df
    email_list = []
    for idx, row in to_ai.iterrows():
        email_list.append({
            "from": row["From"],
            "subject": row["Ultimul Subject"],
            "date": row["Ultima Dată"],
            "id": row["IDs"].split(";")[0]
        })
    gemini_results = gemini_label_emails(email_list, GEMINI_API_KEY)
    label_map = {e['from']: e['label'] for e in gemini_results}
    for idx in to_ai.index:
        sender = df.at[idx, "From"]
        df.at[idx, "Label"] = label_map.get(sender, None)
    return df

def move_selected_to_label(table, label_name):
    service = get_gmail_service()
    if not service:
        return "Nu ești autentificat!"
    if isinstance(table, list):
        df = pd.DataFrame(table)
    else:
        df = table.copy()
    moved = []
    for idx, row in df.iterrows():
        if row.get("Select") and label_name:
            for msg_id in row["IDs"].split(";"):
                ok = move_email_to_label(service, msg_id, label_name)
                if ok:
                    moved.append(f"{row['From']} (ID: {msg_id})")
    if moved:
        return f"Mutate cu succes pe label '{label_name}':\n" + "\n".join(moved)
    return "Nicio mutare efectuată!"

# -------- GRADIO UI --------
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    <div style='text-align:left; margin:8px 0 0 0'>
        <img src='https://ssl.gstatic.com/ui/v1/icons/mail/rfr/gmail.ico' style='width:48px;vertical-align:middle;margin-right:12px;'/><span style='font-size:2.3em; font-weight:700; color:#3983E2;'>MailManager</span>
    </div>
    <div style='margin-top:8px; margin-bottom:12px; font-size:1.1em; color:#444;'>Etichete Gmail, Inbox, reguli și clasificare Gemini<br><hr style="margin:10px 0;"></div>
    """)

    with gr.Tab("Autentificare"):
        auth_status = gr.Markdown("Status: neautentificat.")
        auth_btn = gr.Button("🔐 Authenticate Gmail", scale=1)
        check_btn = gr.Button("🔍 Check Auth Status", scale=1)
        auth_btn.click(open_auth_link, outputs=auth_status)
        check_btn.click(check_gmail_auth, outputs=auth_status)

    with gr.Tab("Etichete & Reguli"):
        labels_btn = gr.Button("🔄 Vezi Labeluri Gmail")
        labels_df = gr.Dataframe(label="Labeluri Gmail", interactive=False)
        senders_btn = gr.Button("🔄 Vezi label + senders")
        senders_df = gr.Dataframe(label="Label & Senders", interactive=False)
        rules_btn = gr.Button("⚙️ Generează/vezi reguli (JSON)")
        rules_out = gr.Code(label="Rules JSON", language="json")

        labels_btn.click(show_labels, outputs=labels_df)
        senders_btn.click(show_labels_senders, outputs=senders_df)
        rules_btn.click(show_rules_json, outputs=rules_out)

    with gr.Tab("Inbox & Clasificare"):
        inbox_btn = gr.Button("🔄 Parsare Inbox + Matching Rules")
        inbox_df = gr.Dataframe(label="Inbox (Unique Senders, cu Label)", interactive=True, wrap=True)
        gemini_btn = gr.Button("✨ Clasifică senderii fără label (Gemini)")
        gemini_df = gr.Dataframe(label="Inbox actualizat cu Gemini", interactive=True, wrap=True)
        move_label = gr.Textbox(label="Label pentru mutare", value="")
        move_btn = gr.Button("📦 Mută pe labelul ales doar rândurile selectate")
        move_out = gr.Textbox(label="Rezultat mutare", lines=4)

        # Parsare inbox
        inbox_btn.click(parse_inbox_to_df, outputs=inbox_df)
        # Clasificare Gemini pentru cei fără label
        gemini_btn.click(send_none_to_gemini, inputs=inbox_df, outputs=gemini_df)
        # Mutare pe label (doar rânduri selectate)
        move_btn.click(move_selected_to_label, inputs=[gemini_df, move_label], outputs=move_out)

    gr.Markdown("""
    ---
    <details>
      <summary><b>Instrucțiuni complete</b></summary>
      <ol>
        <li>Autentifică-te cu Gmail (Tab 1)</li>
        <li>Vezi/Exportă reguli și labeluri (Tab 2)</li>
        <li>Tab 3: Parsare Inbox, clasificare Gemini, selectezi rânduri și le poți muta pe label</li>
      </ol>
    </details>
    """)

if __name__ == "__main__":
    print("Gradio app running.")
    demo.launch(share=True, server_port=GRADIO_PORT)
