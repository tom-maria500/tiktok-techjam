from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import base64
from bs4 import BeautifulSoup

def get_gmail_service(credentials):
    return build('gmail', 'v1', credentials=credentials)

def get_emails(service, query, max_results=6):
    results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
    print(results)
    messages = results.get('messages', [])
    
    emails = []
    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        email = {}
        email['id'] = msg['id']
        email['snippet'] = msg['snippet']
        email['subject'] = next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'Subject'), 'No Subject')
        email['from'] = next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'From'), 'Unknown')
        email['date'] = next((header['value'] for header in msg['payload']['headers'] if header['name'] == 'Date'), 'Unknown')
        email['body'] = get_message_body(msg)
        emails.append(email)
    
    return emails
def get_message_body(message):
    if 'payload' not in message:
        return "No payload found in message."
    
    payload = message['payload']
    if 'parts' in payload:
        return get_body_from_parts(payload['parts'])
    else:
        return get_body_from_payload(payload)

def get_body_from_parts(parts):
    for part in parts:
        if part['mimeType'] == 'text/plain':
            if 'body' in part and 'data' in part['body']:
                return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
        elif part['mimeType'] == 'text/html':
            if 'body' in part and 'data' in part['body']:
                html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                return BeautifulSoup(html, 'html.parser').get_text()
        elif 'parts' in part:
            # Recursively check nested parts
            return get_body_from_parts(part['parts'])
    return "No readable content found."

def get_body_from_payload(payload):
    if payload['mimeType'] == 'text/plain':
        if 'body' in payload and 'data' in payload['body']:
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
    elif payload['mimeType'] == 'text/html':
        if 'body' in payload and 'data' in payload['body']:
            html = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            return BeautifulSoup(html, 'html.parser').get_text()
    elif 'parts' in payload:
        return get_body_from_parts(payload['parts'])
    return "No readable content found."

def search_emails(credentials, query):
    service = get_gmail_service(credentials)
    return get_emails(service, query)