# move_from_table.py
import pandas as pd

def move_emails_from_table(service, table):
    """
    Primește DataFrame/listă cu mailuri și labeluri (editate).
    Mută fiecare mail la labelul dorit. Creează label dacă nu există.
    """
    # Normalizează inputul
    if isinstance(table, list):
        df = pd.DataFrame(table)
    else:
        df = table.copy()

    # Listează etichete existente
    labels_gmail = service.users().labels().list(userId='me').execute().get('labels', [])
    labels_dict = {l['name']: l['id'] for l in labels_gmail}

    results = []
    for _, row in df.iterrows():
        label = str(row.get('label', '')).strip()
        msg_id = row.get('id', '') or row.get('ID', '')
        if not label or not msg_id or label.lower() in ["", "none", "nan"]:
            continue
        # Creează label dacă nu există deja
        if label not in labels_dict:
            label_res = service.users().labels().create(userId='me', body={'name': label}).execute()
            label_id = label_res['id']
            labels_dict[label] = label_id
        else:
            label_id = labels_dict[label]
        try:
            service.users().messages().modify(
                userId='me', id=msg_id,
                body={'addLabelIds': [label_id], 'removeLabelIds': ['INBOX']}
            ).execute()
            results.append(f"✅ Mutat: {msg_id} -> {label}")
        except Exception as e:
            results.append(f"❌ Eroare la {msg_id}: {str(e)}")
    return "\n".join(results) if results else "Nicio mutare efectuată (vezi coloana 'label' și 'id')!"
