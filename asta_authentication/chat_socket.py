# chat_socket.py
# Socket.IO namespace for chat + notifications, authenticated via the
# caller's real Flask-Login session (the same session cookie the rest of
# this app uses) — never a client-supplied user_id.

from flask_socketio import Namespace, join_room, leave_room
from flask_login import current_user
from models import db, Message, User, Notification
import json
from datetime import datetime

def attach_chat_namespace(socketio):
    """Call this with the socketio instance to register the namespace."""
    socketio.on_namespace(ChatNamespace('/chat'))


class ChatNamespace(Namespace):
    def on_connect(self):
        """Reject the connection unless the caller has a real, logged-in
        Flask-Login session — join only the authenticated user's own room,
        never whatever user_id a client claims to be."""
        if not current_user.is_authenticated:
            return False  # reject the connection
        join_room(f'user_{current_user.id}')

    def on_disconnect(self):
        # No-op for now; room membership is ephemeral and handled on reconnect
        pass

    def on_join_conversation(self, data):
        conv_id = data.get('conversation_id')
        if conv_id:
            join_room(f'conversation_{conv_id}')

    def on_leave_conversation(self, data):
        conv_id = data.get('conversation_id')
        if conv_id:
            leave_room(f'conversation_{conv_id}')

    def on_send_message(self, data):
        """
        Socket event to send a message:
        data = {
            'recipient_id': <int>,
            'content': '<text>',
        }
        `sender_id` is always the caller's own authenticated identity —
        never taken from client-supplied data, or anyone could send a
        message that displays as having come from someone else.
        This creates a Message row, commits, emits 'new_message' to recipient personal room
        and emits a 'notification' for recipient.
        """
        if not current_user.is_authenticated:
            return
        try:
            sender_id = current_user.id
            recipient_id = data.get('recipient_id')
            content = data.get('content')
            if not recipient_id or not content:
                return  # malformed

            recipient_id = int(recipient_id)

            # Persist message
            msg = Message(sender_id=sender_id, recipient_id=recipient_id, content=content)
            db.session.add(msg)
            db.session.commit()

            payload = {
                'id': msg.id,
                'sender_id': sender_id,
                'recipient_id': recipient_id,
                'content': content,
                'timestamp': msg.timestamp.isoformat() if hasattr(msg, 'timestamp') else datetime.utcnow().isoformat()
            }

            # Emit message to recipient(s). Clients in conversation should handle display.
            # Emit to personal room of recipient so all tabs/devices receive it.
            self.server.emit('new_message', payload, room=f'user_{recipient_id}', namespace='/chat')

            # Create persistent notification
            notif_payload = {
                'type': 'message',
                'from': sender_id,
                'message_id': msg.id,
                'excerpt': content[:200]
            }
            notif = Notification(user_id=recipient_id, payload=notif_payload)
            db.session.add(notif)
            db.session.commit()

            # Emit notification to recipient
            self.server.emit('notification', {'id': notif.id, 'payload': notif_payload}, room=f'user_{recipient_id}', namespace='/chat')

        except Exception as exc:
            # avoid crashing namespace handlers; log if app logger available
            print("chat_socket.on_send_message error:", exc)
