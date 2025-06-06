# 📧 MailManager – Gmail Workflow AI & Automation

**MailManager** este o aplicație completă de workflow pentru Gmail care integrează autentificare OAuth2, export/import masiv de emailuri în Excel, procesare etichete, statistici avansate, integrare AI (Gemini LLM), vizualizare și mutare automată a mailurilor în funcție de reguli și clasificare asistată AI.

---

## 🚀 Funcționalități principale

- **Autentificare Gmail OAuth2** (Google, via Flask + Ngrok)
- **Export Inbox și etichete Gmail** în XLSX (Excel) – pentru editare manuală rapidă
- **Import și mutare masivă** a mailurilor pe etichete, direct din fișierul XLSX
- **Generare reguli automate** pentru etichete pe baza istoricului de emailuri
- **Vizualizare grafică a regulilor** (relație label – expeditor) cu Plotly
- **Grafic interactiv al regulilor** – click pe o etichetă pentru a deschide
  subgraficul într-un tab nou
- **Clasificare automată Inbox** cu Gemini LLM și reguli custom, cu editare manuală și mutare rapidă
- **Editare ușoară a labelurilor** direct în tabel, cu autocomplete din labelurile existente
- **Statistici și grafice interactive** (Plotly) privind distribuția mailurilor pe etichete
- **Sumarizare AI** a Inbox-ului sau a oricărui set de emailuri folosind Gemini LLM
- **Interfață Gradio**, organizată pe tab-uri pentru un flux clar și intuitiv

---

## 📦 Structura principală a proiectului

- `main.py` – orchestrare completă (Flask server pentru OAuth, Gradio UI, workflow)
- `gmail_utils.py` – autentificare, acces Gmail API, funcții ajutătoare
- `export_gmail_to_xlsx.py` – export Inbox & etichete în XLSX
- `move_from_xlsx.py` – mutare mailuri pe etichete din fișier XLSX
- `move_from_table.py` – mutare mailuri direct din tabel editabil (clasificare Gemini)
- `gemini_utils.py` – integrare Google Gemini pentru sumarizare și clasificare
- `rules_from_labels.py` – generare reguli pe baza istoricului de etichete
- `gemini_labeler.py` – clasificare Inbox cu reguli & Gemini LLM
- `requirements.txt` – toate dependințele necesare
- `.env` – variabile pentru configurare rapidă (key-uri, token-uri etc.)

---

## 🇬🇧 Quick start (English summary)

MailManager is a Gmail workflow toolkit that runs a Flask server behind an
ngrok tunnel. The application requires a few environment variables which are
loaded from a `.env` file:

- `NGROK_TOKEN` – your ngrok auth token.
- `NGROK_HOSTNAME` – the stable hostname reserved in ngrok. This hostname must
  also be configured as an authorized redirect in Google Cloud Console using the
  URL `https://<NGROK_HOSTNAME>/oauth2callback`.
- `SECRET_KEY` – secret key for the Flask session.
- `GEMINI_API_KEY` – API key for the optional Google Gemini features.

After cloning the repo and installing the dependencies run `python3 main.py`.
ngrok will print a public address where you can complete the Google OAuth flow
and access the Gradio interface.

## 🧑‍💻 Cum rulezi proiectul în Google Colab

1.  **Clonează repo-ul și intră în director**
    ```python
    !git clone https://github.com/pasatsanduadrian/MailManager.git
    %cd MailManager
    ```

2.  **Instalează dependințele**
    Colab are deja versiuni recente pentru majoritatea bibliotecilor.
    Fișierul `requirements.txt` indică doar versiuni minime, astfel
    instalarea nu va face downgrade și nu mai este necesară repornirea
    sesiunii.
    ```bash
    !pip install -q -r requirements.txt
    ```

3.  **Configurare Ngrok (pentru tunelare locală necesară OAuth2)**
    * Creează un cont gratuit pe [Ngrok](https://ngrok.com/).
    * Obține-ți `AUTHTOKEN` din dashboard-ul Ngrok.
    * Adaugă-l la variabilele de mediu în Colab:
      ```python
      import os
      os.environ["NGROK_TOKEN"] = "tokenul_tău_aici"
      os.environ["NGROK_HOSTNAME"] = "stable-xxxxx-xxxxx.ngrok-free.app"
      ```
       
4.  **Configurare Credențiale Google API (OAuth2)**
    * Accesează [Google Cloud Console](https://console.cloud.google.com/).
    * Creează un nou proiect (sau selectează unul existent).
    * Navighează la "APIs & Services" > "Enabled APIs & Services" și asigură-te că **"Gmail API"** este activat.
    * Mergi la "Credentials" > "Create Credentials" > "OAuth client ID".
    * Alege "Desktop app" ca tip de aplicație și dă-i un nume.
    * Descarcă fișierul JSON cu credențialele (de obicei `client_secret_XXXX.apps.googleusercontent.com.json`).
    * **Încarcă acest fișier JSON în directorul rădăcină al proiectului în Colab.** Poți redenumi fișierul, de exemplu, în `credentials.json` pentru simplitate.
    * Asigură-te că numele fișierului din codul sursă (în `gmail_utils.py` sau unde este specificat) corespunde cu numele fișierului pe care l-ai încărcat.

5.  **Configurare Google Gemini API Key**
    * Obține o cheie API pentru Google Gemini de la [Google AI Studio](https://aistudio.google.com/app/apikey).
    * Adaugă cheia API la variabilele de mediu în Colab:
      ```python
      import os
      os.environ["GEMINI_API_KEY"] = "cheia_ta_api"
      ```
    
6.  **Rulează aplicația în Colab**
    ```python
    !git clone https://github.com/pasatsanduadrian/MailManager.git
    %cd MailManager

    !pip install -q -r requirements.txt

    with open(".env", "w") as f:
        f.write("SECRET_KEY=random123\n")
        # Înlocuiește valorile de mai jos cu token-urile tale reale
        f.write("GEMINI_API_KEY=cheia_ta_api\n")
        f.write("NGROK_TOKEN=tokenul_tau_ngrok\n")
        f.write("NGROK_HOSTNAME=stable-xxxxx-xxxxx.ngrok-free.app\n")

    !python3 main.py
    ```
    După rulare, Colab îți va afișa un link public la care poți accesa interfața Gradio în browser.

## 🔐 Fișierul `token.pickle`

La prima autentificare Gmail se generează local `token.pickle`. În el sunt stocate credențialele OAuth2 care permit accesul ulterior la Gmail fără a repeta pașii de login.
Fișierul conține date sensibile, deci nu îl partaja și nu îl include în controlul versiunilor (este deja trecut în `.gitignore`).
Dacă rulezi proiectul într-un mediu public sau partajat, șterge `token.pickle` după utilizare sau păstrează-l într-un loc sigur.

---

## 🤝 Contribuții

Contribuțiile sunt binevenite! Dacă ai sugestii, raportezi bug-uri sau vrei să adaugi noi funcționalități, te rog să deschizi un issue sau să creezi un pull request.

---

## 📜 Licență

Acest proiect este disponibil sub licența MIT. Vezi [LICENSE](LICENSE) pentru detalii.
