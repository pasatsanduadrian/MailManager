# gemini_utils.py
import google.generativeai as genai
import re, json

def gemini_label_emails(email_list, api_key, context_rules=None):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash-latest")
    prompt = "Primești o listă cu emailuri (from, subject, date).\n"
    if context_rules:
        prompt += "Ai la dispoziție următoarele reguli deja existente, după label și lista de expeditori:\n"
        prompt += str(context_rules) + "\n"
    prompt += (
        "Pentru fiecare email, propune o etichetă potrivită (folosește întâi regulile dacă se potrivește senderul, altfel propune după conținut).\n"
        "Persoanele se pun pe formatul Persoane/NumePrenume. Returnează rezultatul ca listă JSON: [{\"from\":..., \"subject\":..., \"date\":..., \"label\":...}]\n\n"
    )
    for mail in email_list:
        prompt += f"From: {mail['from']}\nSubject: {mail['subject']}\nDate: {mail['date']}\n\n"
    prompt += "Returnează DOAR lista JSON!"
    out = model.generate_content(prompt)
    match = re.search(r'\[.*\]', out.text, re.DOTALL)
    if not match:
        return []
    return json.loads(match.group())


def gemini_summarize_emails(email_list, api_key):
    """
    Primește o listă de emailuri (dicturi cu from, subject, date), returnează un sumar extins (bullet-uri pe teme, categorii principale, exemple).
    """
    if not email_list:
        return "Nu sunt emailuri de sumarizat."
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash-latest")
    prompt = (
        "Primești o listă de emailuri din Inbox cu From, Subject și Date.\n"
        "Te rog să generezi un sumar extins pentru utilizator, structurat pe teme principale (ex: Notificări, AI, Financiar, Personal etc). "
        "Afișează pentru fiecare temă:\n"
        "- O descriere succintă\n"
        "- 2-3 exemple de subiecte (bullet)\n"
        "- Numărul de mailuri pe temă\n"
        "Grupează mailurile similar ca într-un dashboard inteligent.\n"
        "Format răspuns:\n"
        "## Temă: [ex. Notificări/servicii]\n"
        "- Descriere...\n"
        "- Subiecte:\n"
        "  * ...\n"
        "  * ...\n"
        "- Total mailuri: ...\n\n"
        "Iată lista de mailuri:\n"
    )
    for mail in email_list:
        prompt += f"From: {mail['from']}\nSubject: {mail['subject']}\nDate: {mail['date']}\n\n"
    out = model.generate_content(prompt)
    if hasattr(out, "text"):
        return out.text
    return str(out)
