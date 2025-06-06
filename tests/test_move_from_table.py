import os
import sys
import types
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Minimal pandas stub for tests
class _DF:
    def __init__(self, rows):
        self._rows = [dict(r) for r in rows]

    def copy(self):
        return _DF(self._rows)

    def iterrows(self):
        for i, row in enumerate(self._rows):
            yield i, row


def _DataFrame(data):
    if isinstance(data, _DF):
        return data
    return _DF(data)

pd = types.SimpleNamespace(DataFrame=_DataFrame)
sys.modules['pandas'] = pd

from move_from_table import move_emails_from_table


def test_move_emails_from_table_creates_and_moves():
    service = MagicMock()
    users = service.users.return_value
    labels = users.labels.return_value
    messages = users.messages.return_value

    labels.list.return_value.execute.return_value = {
        'labels': [
            {'id': 'lbl1', 'name': 'Existing', 'type': 'user'}
        ]
    }
    labels.create.return_value.execute.return_value = {'id': 'lbl2'}
    messages.modify.return_value.execute.return_value = None

    table = pd.DataFrame([
        {'id': '111', 'label': 'Existing'},
        {'id': '222', 'label': 'NewLabel'},
        {'id': '', 'label': 'Existing'},
        {'id': '333', 'label': ''}
    ])

    result = move_emails_from_table(service, table)

    labels.create.assert_called_once_with(userId='me', body={'name': 'NewLabel'})
    assert messages.modify.call_count == 2
    messages.modify.assert_any_call(
        userId='me', id='111',
        body={'addLabelIds': ['lbl1'], 'removeLabelIds': ['INBOX']}
    )
    messages.modify.assert_any_call(
        userId='me', id='222',
        body={'addLabelIds': ['lbl2'], 'removeLabelIds': ['INBOX']}
    )

    assert '✅ Mutat: 111 -> Existing' in result
    assert '✅ Mutat: 222 -> NewLabel' in result


