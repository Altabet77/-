"""
gmail_tool.py — سمير: تكامل Gmail الكامل
قراءة / إرسال / رد / بحث في الإيميلات صوتياً
يستخدم Gmail API عبر OAuth2
"""

import os
import base64
import logging
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

from app.tools.base_tool import tool_registry

logger = logging.getLogger('samir.tools.gmail')

GMAIL_CREDS_PATH = Path('./data/gmail_credentials.json')
GMAIL_TOKEN_PATH = Path('./data/gmail_token.json')
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
]


def _get_gmail_service():
    """بناء خدمة Gmail API مع OAuth2."""
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = None
        if GMAIL_TOKEN_PATH.exists():
            creds = Credentials.from_authorized_user_file(str(GMAIL_TOKEN_PATH), GMAIL_SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not GMAIL_CREDS_PATH.exists():
                    return None, 'ملف credentials.json غير موجود في ./data/gmail_credentials.json'
                flow = InstalledAppFlow.from_client_secrets_file(str(GMAIL_CREDS_PATH), GMAIL_SCOPES)
                creds = flow.run_local_server(port=0)
            GMAIL_TOKEN_PATH.write_text(creds.to_json())

        service = build('gmail', 'v1', credentials=creds)
        return service, None
    except ImportError:
        return None, 'مكتبات Gmail غير مثبتة. شغّل: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib'
    except Exception as e:
        return None, str(e)


def _decode_part(part) -> str:
    data = part.get('body', {}).get('data', '')
    if data:
        return base64.urlsafe_b64decode(data + '==').decode('utf-8', errors='replace')
    return ''


def _extract_email_body(payload) -> str:
    mime = payload.get('mimeType', '')
    if mime == 'text/plain':
        return _decode_part(payload)
    if mime.startswith('multipart'):
        for part in payload.get('parts', []):
            text = _extract_email_body(part)
            if text:
                return text
    return ''


async def tool_read_emails(
    max_count: int = 5,
    query: str = 'is:unread',
    include_body: bool = False,
) -> Dict[str, Any]:
    """
    اقرا اخر الايميلات من Gmail.
    max_count: عدد الايميلات (افتراضي 5)
    query: فلتر البحث (مثال: 'is:unread', 'from:boss@example.com', 'subject:فاتورة')
    include_body: هل تريد محتوى الايميل كاملا؟
    """
    loop = asyncio.get_event_loop()

    def _fetch():
        service, err = _get_gmail_service()
        if err:
            return {'status': 'error', 'message': err, 'emails': []}

        results = service.users().messages().list(
            userId='me', q=query, maxResults=max_count
        ).execute()

        messages = results.get('messages', [])
        if not messages:
            return {'status': 'success', 'message': 'لا توجد ايميلات تطابق البحث', 'emails': [], 'count': 0}

        emails = []
        for msg_ref in messages[:max_count]:
            msg = service.users().messages().get(
                userId='me', id=msg_ref['id'], format='full'
            ).execute()

            headers = {h['name']: h['value'] for h in msg['payload'].get('headers', [])}
            body = ''
            if include_body:
                body = _extract_email_body(msg['payload'])[:800]

            emails.append({
                'id': msg_ref['id'],
                'subject': headers.get('Subject', '(بدون عنوان)'),
                'from': headers.get('From', 'غير معروف'),
                'date': headers.get('Date', ''),
                'snippet': msg.get('snippet', '')[:200],
                'body': body,
                'unread': 'UNREAD' in msg.get('labelIds', []),
            })

        return {
            'status': 'success',
            'count': len(emails),
            'message': f'وجدت {len(emails)} ايميل',
            'emails': emails,
        }

    return await loop.run_in_executor(None, _fetch)


async def tool_send_email(
    to: str,
    subject: str,
    body: str,
    reply_to_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    ارسل ايميلا عبر Gmail.
    to: عنوان البريد الالكتروني للمستلم
    subject: عنوان الايميل
    body: محتوى الايميل
    reply_to_id: (اختياري) ID الايميل للرد عليه
    """
    loop = asyncio.get_event_loop()

    def _send():
        service, err = _get_gmail_service()
        if err:
            return {'status': 'error', 'message': err}

        msg = MIMEText(body, 'plain', 'utf-8')
        msg['to'] = to
        msg['subject'] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
        body_payload = {'raw': raw}

        if reply_to_id:
            original = service.users().messages().get(userId='me', id=reply_to_id).execute()
            headers = {h['name']: h['value'] for h in original['payload'].get('headers', [])}
            thread_id = original.get('threadId', '')
            body_payload['threadId'] = thread_id

        sent = service.users().messages().send(userId='me', body=body_payload).execute()
        return {
            'status': 'success',
            'message': f'تم ارسال الايميل الى {to}',
            'message_id': sent.get('id'),
            'to': to,
            'subject': subject,
        }

    return await loop.run_in_executor(None, _send)


async def tool_search_emails(query: str, max_count: int = 10) -> Dict[str, Any]:
    """
    ابحث في Gmail عن ايميلات محددة.
    query: نص البحث (مثال: 'from:ahmed@company.com subject:عقد')
    """
    return await tool_read_emails(max_count=max_count, query=query, include_body=False)


# ─── Register ─────────────────────────────────────────────────────────────────

tool_registry.register(
    name='read_emails',
    func=tool_read_emails,
    schema={
        'name': 'read_emails',
        'description': 'اقرا اخر الايميلات من Gmail. استخدمه عندما يسال المستخدم عن ايميلاته او الرسائل الجديدة.',
        'parameters': {
            'type': 'object',
            'properties': {
                'max_count': {'type': 'integer', 'default': 5, 'description': 'عدد الايميلات'},
                'query': {'type': 'string', 'default': 'is:unread', 'description': 'فلتر البحث'},
                'include_body': {'type': 'boolean', 'default': False, 'description': 'تضمين نص الايميل الكامل'},
            },
            'required': [],
        },
    }
)

tool_registry.register(
    name='send_email',
    func=tool_send_email,
    schema={
        'name': 'send_email',
        'description': 'ارسل ايميلا عبر Gmail. استخدمه عندما يطلب المستخدم ارسال رسالة او رد على ايميل.',
        'parameters': {
            'type': 'object',
            'properties': {
                'to': {'type': 'string', 'description': 'عنوان البريد الالكتروني للمستلم'},
                'subject': {'type': 'string', 'description': 'عنوان الايميل'},
                'body': {'type': 'string', 'description': 'محتوى نص الايميل'},
                'reply_to_id': {'type': 'string', 'description': 'ID الايميل للرد عليه (اختياري)'},
            },
            'required': ['to', 'subject', 'body'],
        },
    }
)

tool_registry.register(
    name='search_emails',
    func=tool_search_emails,
    schema={
        'name': 'search_emails',
        'description': 'ابحث في Gmail عن ايميلات محددة باستخدام كلمات مفتاحية.',
        'parameters': {
            'type': 'object',
            'properties': {
                'query': {'type': 'string', 'description': 'نص البحث'},
                'max_count': {'type': 'integer', 'default': 10},
            },
            'required': ['query'],
        },
    }
)
