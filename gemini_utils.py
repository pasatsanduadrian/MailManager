# gemini_utils.py
import google.generativeai as genai

def gemini_label_emails(email_list, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash-latest")
    prompt = "Primești o listă cu expeditori (from) și subiecte, propune câte un label pentru fiecare, ca JSON cu format: [{\"from\":\"...\", \"label\":\"...\"}]\n\n"
    for mail in email_list:
        prompt += f"From: {mail['from']}\nSubject: {mail['subject']}\nDate: {mail['date']}\n\n"
    prompt += "Persoanele se pun pe formatul Persoane/NumePrenume dacă e vorba de o persoană. Returnează DOAR lista JSON!"
    out = model.generate_content(prompt)
    import re, json
    match = re.search(r'\[.*\]', out.text, re.DOTALL)
    if not match:
        return []
    return json.loads(match.group())
