# inbox_parser.py
import re
from gmail_utils import get_gmail_service, get_inbox_messages

def parse_inbox_and_match(rules_dict, max_results=100):
    service = get_gmail_service()
    if not service:
        return []
    emails = get_inbox_messages(service, max_results)
    sender_map = {}
    for email in emails:
        sender = email['from']
        if not sender:
            continue
        if sender not in sender_map:
            sender_map[sender] = {
                "count": 1,
                "subject": email.get("subject", ""),
                "date": email.get("date", ""),
                "ids": [email.get("id", "")]
            }
        else:
            sender_map[sender]["count"] += 1
            sender_map[sender]["ids"].append(email.get("id", ""))
    rows = []
    for sender, info in sender_map.items():
        # Caută label existent (după rules_dict)
        label = None
        for lbl, senders in rules_dict.items():
            if sender in senders:
                label = lbl
                break
        # Regula pentru persoane
        if not label:
            m = re.match(r"([A-Za-zăîâșțĂÎÂȘȚ]+ [A-Za-zăîâșțĂÎÂȘȚ]+)", sender)
            if m and not any(x in sender.lower() for x in ["noreply", "newsletter", "no-reply", "emag", "notification", "update"]):
                label = f"Persoane/{m.group(1).replace(' ','')}"
        rows.append({
            "Select": False,
            "From": sender,
            "Count": info["count"],
            "Ultimul Subject": info["subject"],
            "Ultima Dată": info["date"],
            "IDs": ";".join(info["ids"]),
            "Label": label if label else None
        })
    return rows
