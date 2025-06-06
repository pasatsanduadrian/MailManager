import os
import sys
import types
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.modules['googleapiclient.discovery'] = types.ModuleType('googleapiclient.discovery')
sys.modules['googleapiclient.discovery'].build = lambda *a, **k: None

google_mod = types.ModuleType('google')
google_auth = types.ModuleType('google.auth')
google_auth_transport = types.ModuleType('google.auth.transport')
google_auth_transport_requests = types.ModuleType('google.auth.transport.requests')
google_auth_transport_requests.Request = lambda *a, **k: None

google_auth_transport.requests = google_auth_transport_requests
google_auth.transport = google_auth_transport
google_mod.auth = google_auth
sys.modules['google'] = google_mod
sys.modules['google.auth'] = google_auth
sys.modules['google.auth.transport'] = google_auth_transport
sys.modules['google.auth.transport.requests'] = google_auth_transport_requests
import gmail_utils


def test_list_user_label_names():
    service = MagicMock()
    users = service.users.return_value
    labels = users.labels.return_value
    labels.list.return_value.execute.return_value = {
        'labels': [
            {'id': '1', 'name': 'Personal', 'type': 'user'},
            {'id': '2', 'name': 'SYSTEM', 'type': 'system'},
            {'id': '3', 'name': 'Work', 'type': 'user'}
        ]
    }

    result = gmail_utils.list_user_label_names(service)

    labels.list.assert_called_once_with(userId='me')
    assert result == ['Personal', 'Work']


