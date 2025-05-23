import google.generativeai as genai
import os
import re
import json

def gemini_label_emails(email_list, api_key):
    """
    Trimite la Gemini API o listă de emailuri (listă de dicturi cu from, subject, date)
    și returnează propuneri de label (ca listă de dicturi {id, label}).
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash-latest")

    prompt = (
        "Primești o listă de emailuri cu metadate (From, Subject, Date). "
        "Propune o clasificare/etichetare pentru fiecare email, folosind ca răspuns o listă JSON cu formatul: "
        "[{\"id\":..., \"label\":...}]. Dacă nu poți propune un label, folosește \"UNSORTED\".\n"
        "Lista emailuri:\n"
    )
    for email in email_list:
        prompt += f"\nID: {email['id']}\nFrom: {email['from']}\nSubject: {email['subject']}\nDate: {email['date']}\n"
    prompt += "\nReturnează doar lista JSON!"

    response = model.generate_content(prompt)
    match = re.search(r'\[.*\]', response.text, re.DOTALL)
    if not match:
        return [{"id": e['id'], "label": "UNSORTED"} for e in email_list]
    try:
        return json.loads(match.group())
    except Exception:
        return [{"id": e['id'], "label": "UNSORTED"} for e in email_list]
