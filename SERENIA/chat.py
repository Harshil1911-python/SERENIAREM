import os, json, uuid
from datetime import datetime
from data import load_data, save_data

def get_conversations():
    """Get all conversations."""
    return load_data().get('conversations', [])

def get_or_create_conversation(client_type, client_id, client_name):
    """Get existing conversation or create new one for a client."""
    d = load_data()
    convos = d.setdefault('conversations', [])
    conv   = next((c for c in convos if c['client_id'] == client_id and c['client_type'] == client_type), None)
    if not conv:
        conv = {
            'id':          str(uuid.uuid4())[:8].upper(),
            'client_id':   client_id,
            'client_type': client_type,
            'client_name': client_name,
            'created_at':  datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_message': '',
            'last_time':    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'unread_agent':  0,  # unread count for agent
            'unread_client': 0,  # unread count for client
            'messages': [],
        }
        convos.append(conv)
        save_data(d)
    return conv

def send_message(conversation_id, sender_type, sender_name, text):
    """Send a message. sender_type: 'agent' or 'client'."""
    try:
        d     = load_data()
        convos = d.get('conversations', [])
        conv  = next((c for c in convos if c['id'] == conversation_id), None)
        if not conv: return False, 'Conversation not found'

        msg = {
            'id':          str(uuid.uuid4())[:8],
            'sender_type': sender_type,
            'sender_name': sender_name,
            'text':        text.strip(),
            'time':        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'read':        False,
        }
        conv['messages'].append(msg)
        conv['last_message'] = text[:80]
        conv['last_time']    = msg['time']

        # Increment unread for the OTHER side
        if sender_type == 'agent':
            conv['unread_client'] = conv.get('unread_client', 0) + 1
        else:
            conv['unread_agent'] = conv.get('unread_agent', 0) + 1

        save_data(d)
        return True, msg
    except Exception as e:
        return False, str(e)

def get_messages(conversation_id, mark_read_for=None):
    """Get messages for a conversation. mark_read_for: 'agent' or 'client'."""
    d     = load_data()
    conv  = next((c for c in d.get('conversations', []) if c['id'] == conversation_id), None)
    if not conv: return None

    if mark_read_for == 'agent':
        conv['unread_agent'] = 0
        save_data(d)
    elif mark_read_for == 'client':
        conv['unread_client'] = 0
        save_data(d)

    return conv

def get_client_conversation(client_type, client_id):
    """Get conversation for a specific client (for portal use)."""
    d = load_data()
    return next((c for c in d.get('conversations', [])
                 if c['client_id'] == client_id and c['client_type'] == client_type), None)

def get_total_unread_for_agents():
    """Total unread messages from clients to agents."""
    d = load_data()
    return sum(c.get('unread_agent', 0) for c in d.get('conversations', []))
