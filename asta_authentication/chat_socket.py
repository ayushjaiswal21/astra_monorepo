# chat_socket.py
# Lightweight Socket.IO namespace for chat + notifications (development-friendly).
# For production, authenticate tokens on connect instead of trusting query params.

from flask import request
from flask_socketio import Namespace, join_room, leave_room
from models import db, Message, User, Notification
import json
from datetime import datetime

def attach_chat_namespace(socketio):
    """Call this with the socketio instance to register the namespace."""
    socketio.on_namespace(ChatNamespace('/chat'))


class ChatNamespace(Namespace):
    def on_connect(self):
        """
        Expected (dev) usage: socket = io('/chat', { query: { user_id: CURRENT_USER_ID } })
        In production, verify an auth token here (JWT or session).
        """
        user_id = request.args.get('user_id')
        if user_id:
            # join personal room so server can target notifications/messages
            join_room(f'user_{user_id}')
            # Optional: also join presence room, etc.
        # Accept connection; to reject return False

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
            # optionally 'sender_id' (if provided) otherwise uses request.args user_id
        }
        This creates a Message row, commits, emits 'new_message' to recipient personal room
        and emits a 'notification' for recipient.
        """
        try:
            sender_id = data.get('sender_id') or request.args.get('user_id')
            recipient_id = data.get('recipient_id')
            content = data.get('content')
            if not sender_id or not recipient_id or not content:
                return  # malformed

            sender_id = int(sender_id)
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
