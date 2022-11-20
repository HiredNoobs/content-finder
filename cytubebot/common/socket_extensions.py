"""
Functions to extend or wrap socket io functionality.
"""
import os
from textwrap import wrap

MSG_LIMIT = int(os.environ.get('CYTUBE_MSG_LIMIT'))


def send_chat_msg(sio, message: str) -> None:
    """
    Wrapper for socketio's .emit
    """
    msgs = wrap(message, MSG_LIMIT)
    for msg in msgs:
        sio.emit('chatMsg', {'msg': msg})
