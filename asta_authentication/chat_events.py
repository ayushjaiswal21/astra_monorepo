from flask import request
from flask_login import current_user
from flask_socketio import join_room, leave_room, send
from app import socketio, db
from models import User, Message

@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        # Join a room named after the user's ID
        join_room(current_user.id)
        print(f'[CONNECT] User {current_user.username} (ID: {current_user.id}) has joined their personal room.', flush=True)
    else:
        print('[CONNECT] Unauthenticated user connected.', flush=True)

@socketio.on('join_chat')
def handle_join_chat(data):
    if not current_user.is_authenticated:
        return
    username = data.get('username')
    user = User.query.filter_by(username=username).first()
    if user:
        room = get_room_name(current_user.id, user.id)
        join_room(room)
        print(f"[DEBUG] User {current_user.username} is joining room: {room}")

@socketio.on('send_message')
def handle_send_message(data):
    if not current_user.is_authenticated:
        return

    recipient_username = data.get('recipient')
    content = data.get('content')
    recipient = User.query.filter_by(username=recipient_username).first()

    if recipient and content:
        message = Message(sender_id=current_user.id, recipient_id=recipient.id, content=content)
        db.session.add(message)
        db.session.commit()

        # 1. This is the existing shared conversation room
        conversation_room = get_room_name(current_user.id, recipient.id)
        print(f'[SEND_MSG] Emitting to CONVERSATION room: {conversation_room}', flush=True)
        socketio.emit('receive_message', {
            'sender_id': current_user.id,
            'sender': current_user.username,
            'recipient': recipient.username,
            'content': data['content'],
            'timestamp': message.timestamp.isoformat()
        }, room=conversation_room)

        # 2. This is the NEW emit to the recipient's personal room
        personal_room = recipient.id
        print(f'[SEND_MSG] Emitting to PERSONAL room: {personal_room}', flush=True)
        socketio.emit('receive_message', {
            'sender_id': current_user.id,
            'sender': current_user.username,
            'recipient': recipient.username,
            'content': data['content'],
            'timestamp': message.timestamp.isoformat()
        }, room=personal_room)

@socketio.on('typing')
def handle_typing(data):
    if not current_user.is_authenticated:
        return
    recipient_username = data.get('recipient')
    recipient = User.query.filter_by(username=recipient_username).first()
    if recipient:
        room = get_room_name(current_user.id, recipient.id)
        socketio.emit('typing', {'user': current_user.username}, room=room, include_self=False)

@socketio.on('stop_typing')
def handle_stop_typing(data):
    if not current_user.is_authenticated:
        return
    recipient_username = data.get('recipient')
    recipient = User.query.filter_by(username=recipient_username).first()
    if recipient:
        room = get_room_name(current_user.id, recipient.id)
        socketio.emit('stop_typing', {'user': current_user.username}, room=room, include_self=False)

def get_room_name(user1_id, user2_id):
    return '-'.join(sorted([str(user1_id), str(user2_id)]))