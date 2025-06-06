# 📧 MailManager – Gmail Workflow AI & Automation

**MailManager** este o aplicație completă de workflow pentru Gmail care integrează autentificare OAuth2, export/import masiv de emailuri în Excel, procesare etichete, statistici avansate, integrare AI (Gemini LLM), vizualizare și mutare automată a mailurilor în funcție de reguli și clasificare asistată AI.

---

## 🚀 Funcționalități principale

- **Autentificare Gmail OAuth2** (Google, via Flask + Ngrok)
- **Export Inbox și etichete Gmail** în XLSX (Excel) – pentru editare manuală rapidă
- **Import și mutare masivă** a mailurilor pe etichete, direct din fișierul XLSX
- **Generare reguli automate** pentru etichete pe baza istoricului de emailuri
- **Vizualizare grafică a regulilor** (relație label – expeditor) cu Plotly
- **Clasificare automată Inbox** cu Gemini LLM și reguli custom, cu editare manuală și mutare rapidă
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

## 🧑‍💻 Cum rulezi proiectul în Google Colab

1.  **Clonează repo-ul și intră în director**
    ```python
    !git clone https://github.com/pasatsanduadrian/MailManager.git
    %cd MailManager
    ```

2.  **Instalează dependințele**
    ```bash
    !pip install -r requirements.txt
    ```

3.  **Configurare Ngrok (pentru tunelare locală necesară OAuth2)**
    * Creează un cont gratuit pe [Ngrok](https://ngrok.com/).
    * Obține-ți `AUTHTOKEN` din dashboard-ul Ngrok.
    * Adaugă-l la variabilele de mediu în Colab:
       
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
    
6.  **Rulează aplicația in Colab**
    ```python
    !git clone https://github.com/pasatsanduadrian/MailManager.git
    %cd MailManager
    
    !pip install -r requirements.txt
    
    with open(".env", "w") as f:
        f.write("SECRET_KEY=random123\n")
        f.write("GEMINI_API_KEY=tokenul_tău_aici\n")
        f.write("NGROK_TOKEN=tokenul_tău_aici\n")
        f.write("NGROK_HOSTNAME=stable-xxxxx-xxxxx.ngrok-free.app\n")
    
    !python3 main.py

    ```
    După rulare, Colab îți va afișa un link public la care poți accesa interfața Gradio în browser.

---

## 🤝 Contribuții

Contribuțiile sunt binevenite! Dacă ai sugestii, raportezi bug-uri sau vrei să adaugi noi funcționalități, te rog să deschizi un issue sau să creezi un pull request.
