import os
import pickle
import time
from threading import Thread
from dotenv import load_dotenv
from pyngrok import ngrok
from flask import Flask, request, redirect, session
from google_auth_oauthlib.flow import Flow
import gradio as gr
import plotly.express as px
import pandas as pd
import html

from gmail_utils import get_gmail_service, list_user_label_names
from export_gmail_to_xlsx import export_labels_and_inbox_xlsx
from move_from_xlsx import move_emails_from_xlsx
from move_from_table import move_emails_from_table  # <-- Import nou!
from gemini_utils import gemini_summarize_emails
from rules_from_labels import generate_rules_from_labels
from gemini_labeler import label_inbox_with_gemini
from rules_graph import rules_to_plot

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
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

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

def export_xlsx_ui(_):
    service = get_gmail_service()
    if not service:
        return None, "Eroare: nu ești autentificat Gmail!"
    path = "gmail_labels_inbox.xlsx"
    export_labels_and_inbox_xlsx(service, path)
    return path, f"Export XLSX gata: {path}"

def move_xlsx_ui(file):
    service = get_gmail_service()
    if not service:
        return "Eroare: nu ești autentificat Gmail!"
    move_emails_from_xlsx(service, file.name)
    return "Mutare finalizată! (vezi Gmail)"

def get_label_stats(service):
    labels = service.users().labels().list(userId='me').execute().get('labels', [])
    label_stats = []
    for l in labels:
        if l.get("type") == "user":
            total = 0
            page_token = None
            while True:
                resp = service.users().messages().list(userId='me', labelIds=[l['id']], maxResults=500, pageToken=page_token).execute()
                total += len(resp.get('messages', []))
                page_token = resp.get('nextPageToken')
                if not page_token:
                    break
            label_stats.append({"Label": l["name"], "Count": total})
    df = pd.DataFrame(label_stats).sort_values("Count", ascending=False)
    return df

def datalist_html(options, list_id="labels-datalist"):
    """Returnează un snippet <datalist> cu opțiuni escapate."""
    escaped = [f"<option value='{html.escape(str(l))}'>" for l in options]
    return f"<datalist id='{list_id}'>\n" + "\n".join(escaped) + "\n</datalist>"

def show_label_stats_and_plot():
    service = get_gmail_service()
    if not service:
        return pd.DataFrame([{"Label": "Neautentificat!", "Count": 0}]), None
    df = get_label_stats(service)
    fig = px.bar(
        df, x='Label', y='Count',
        text_auto=True,
        title="Distribuție mailuri pe labeluri Gmail",
        template="plotly_white",
        color_discrete_sequence=['#3983E2']
    )
    fig.update_layout(
        xaxis_title="Label",
        yaxis_title="Nr. mailuri",
        font=dict(size=16, family="Segoe UI"),
        xaxis_tickangle=-45,
        margin=dict(l=40, r=20, t=60, b=200),
        height=450
    )
    fig.update_traces(textfont_size=14)
    return df, fig

def datalist_html(labels):
    options = "".join(f"<option value='{l}'></option>" for l in labels)
    return f"""
    <datalist id='label-options'>
    {options}
    </datalist>
    <script>
    function attachList(){{
        const cells=document.querySelectorAll('#label-table td:nth-child(5) input');
        cells.forEach(c=>c.setAttribute('list','label-options'));
    }}
    const ob = new MutationObserver(attachList);
    ob.observe(document.getElementById('label-table'), {{childList:true, subtree:true}});
    attachList();
    </script>
    """

def gemini_summarizer_tab(nr_mails):
    service = get_gmail_service()
    if not service:
        return "Eroare: nu ești autentificat Gmail!"
    inbox = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=nr_mails).execute().get('messages', [])
    emails = []
    for m in inbox:
        msg = service.users().messages().get(userId='me', id=m['id'], format='metadata', metadataHeaders=['From','Subject','Date']).execute()
        headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
        emails.append({
            "from": headers.get('From', ''),
            "subject": headers.get('Subject', ''),
            "date": headers.get('Date', ''),
        })
    summary = gemini_summarize_emails(emails, GEMINI_API_KEY)
    return gr.Markdown(summary)

def gen_rules_func():
    service = get_gmail_service()
    if not service:
        return "Eroare autentificare Gmail.", None
    rules = generate_rules_from_labels(service)
    import json
    fig = rules_to_plot(rules)
    return json.dumps(rules, indent=2, ensure_ascii=False), fig

def classify_gemini_func():
    service = get_gmail_service()
    if not service:
        return pd.DataFrame([{"Status": "Neautentificat"}]), ""
    rules = generate_rules_from_labels(service)
    out = label_inbox_with_gemini(service, rules, GEMINI_API_KEY, max_inbox=200)
    if not out:
        return pd.DataFrame([{"Status": "Niciun rezultat"}]), ""
    df = pd.DataFrame(out)
    # asigură-te că ai 'id', 'from', 'subject', 'date', 'label'
    cols = [col for col in ['id', 'from', 'subject', 'date', 'label'] if col in df.columns]
    labels = list_user_label_names(service)
    html = datalist_html(labels)
    return df[cols], html

def move_table_labels_func(table):
    service = get_gmail_service()
    if not service:
        return "Eroare: nu ești autentificat Gmail!"
    return move_emails_from_table(service, table)

css = """#label-table td:nth-child(5){background-color:#fffbea;}"""

with gr.Blocks(theme=gr.themes.Soft(), css=css) as demo:
    gr.Markdown("""
    <h2 style='color:#1a73e8'>MailManager – Gmail OAuth2 + Workflow Inbox/Labels</h2>
    <ol>
    <li>Click pe butonul de autentificare, urmează pașii din browser (vei genera token.pickle)</li>
    <li>Exportă inbox și labels în XLSX (download)</li>
    <li>Editează manual sheet-ul Inbox (coloana Label) în Excel</li>
    <li>Încarcă XLSX modificat și rulează mutarea automată a mailurilor în Labels</li>
    </ol>
    <hr>
    """)


    with gr.Tab("Autentificare & Export/Mutare"):
        auth_status = gr.Markdown(check_auth())
        auth_btn = gr.Button("🔐 Deschide autentificarea Gmail în browser")
        auth_btn.click(open_auth_link, outputs=auth_status)
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

        
    with gr.Tab("Clasificare Gemini & Reguli"):
        gr.Markdown("### 1️⃣ Generează reguli pentru labeluri Gmail")
        gen_rules_btn = gr.Button("Generează reguli JSON")
        rules_out = gr.Code(label="Rules JSON", language="json")
        rules_plot = gr.Plot(label="Grafic Reguli")
        gen_rules_btn.click(fn=gen_rules_func, outputs=[rules_out, rules_plot])

        gr.Markdown("### 2️⃣ Clasifică Inbox folosind reguli + Gemini LLM")
        classify_btn = gr.Button("Clasifică Inbox cu Gemini")
     
        classify_table = gr.Dataframe(
            label="Inbox classificat (cu etichete, editabilă doar coloana 'label')",
            interactive=True,
            headers=["id", "from", "subject", "date", "label"],
            datatype=["str", "str", "str", "str", "str"],
            row_count=(10, "dynamic"),
            col_count=(5, "Fixed"),
            elem_id="label-table",
        )
        label_suggest = gr.HTML(datalist_html([]))

        classify_btn.click(fn=classify_gemini_func, outputs=[classify_table, label_suggest])

        gr.Markdown("#### 3️⃣ Mută emailurile pe labelurile editate")
        move_labels_btn = gr.Button("Mută mailurile pe labeluri din tabel")
        move_labels_status = gr.Textbox(label="Status mutare", lines=6)
        move_labels_btn.click(fn=move_table_labels_func, inputs=classify_table, outputs=move_labels_status)

    

    with gr.Tab("Statistici & Grafice"):
        gr.Markdown("#### Distribuție pe labeluri și sumarizare Inbox cu grafice moderne")
        stats_btn = gr.Button("Afișează distribuție labeluri & grafic")
        label_table = gr.Dataframe(label="Statistici Labeluri", interactive=False, datatype=["str", "number"])
        stats_plot = gr.Plot(label="Grafic distribuție")
        stats_btn.click(show_label_stats_and_plot, outputs=[label_table, stats_plot])

    with gr.Tab("Sumar Gemini (AI)"):
        gr.Markdown("#### Sumar extins cu Gemini LLM pentru ultimele N mailuri din Inbox")
        nr_emails = gr.Number(label="Câte emailuri să sumarizeze Gemini?", value=30, precision=0)
        gemini_btn = gr.Button("Generează sumar cu Gemini")
        gemini_sum = gr.Markdown()
        gemini_btn.click(fn=gemini_summarizer_tab, inputs=nr_emails, outputs=gemini_sum)

    gr.Markdown("""
    ---
    <details>
    <summary><b>Instrucțiuni complete</b></summary>
    <ol>
      <li>Click pe butonul de autentificare Gmail de mai sus și urmează pașii din browser (vei genera <code>token.pickle</code>).</li>
      <li>Folosește butonul de export pentru a salva un fișier XLSX cu două sheet-uri (<b>Labels</b> și <b>Inbox</b>).</li>
      <li>Deschide fișierul în Excel și completează/editează coloana <b>Label</b> din sheet Inbox.</li>
      <li>Încarcă fișierul modificat și apasă <b>Mută automat emailurile</b>.</li>
      <li>Pentru statistici și sumar AI, folosește taburile dedicate!</li>
    </ol>
    </details>
    """)

if __name__ == "__main__":
    demo.launch(share=True, server_port=7070)
