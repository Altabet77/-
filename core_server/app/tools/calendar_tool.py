"""
calendar_tool.py — سمير: Google Calendar التكامل الكامل
عرض / اضافة / حذف المواعيد بالصوت
"""

import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

from app.tools.base_tool import tool_registry

logger = logging.getLogger('samir.tools.calendar')

CALENDAR_CREDS_PATH = Path('./data/gmail_credentials.json')
CALENDAR_TOKEN_PATH = Path('./data/calendar_token.json')
CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar']


def _get_calendar_service():
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        creds = None
        if CALENDAR_TOKEN_PATH.exists():
            creds = Credentials.from_authorized_user_file(str(CALENDAR_TOKEN_PATH), CALENDAR_SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not CALENDAR_CREDS_PATH.exists():
                    return None, 'ملف credentials.json غير موجود في ./data/'
                flow = InstalledAppFlow.from_client_secrets_file(str(CALENDAR_CREDS_PATH), CALENDAR_SCOPES)
                creds = flow.run_local_server(port=0)
            CALENDAR_TOKEN_PATH.write_text(creds.to_json())

        service = build('calendar', 'v3', credentials=creds)
        return service, None
    except ImportError:
        return None, 'pip install google-api-python-client google-auth-oauthlib'
    except Exception as e:
        return None, str(e)


async def tool_get_calendar_events(
    days_ahead: int = 7,
    max_results: int = 10,
) -> Dict[str, Any]:
    """
    اجلب المواعيد القادمة من Google Calendar.
    days_ahead: عدد الايام القادمة (افتراضي 7 ايام)
    max_results: اقصى عدد مواعيد
    """
    loop = asyncio.get_event_loop()

    def _fetch():
        service, err = _get_calendar_service()
        if err:
            return {'status': 'error', 'message': err, 'events': []}

        now = datetime.utcnow().isoformat() + 'Z'
        end = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            timeMax=end,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        if not events:
            return {'status': 'success', 'message': 'لا توجد مواعيد قادمة', 'events': [], 'count': 0}

        formatted = []
        for e in events:
            start = e['start'].get('dateTime', e['start'].get('date', ''))
            formatted.append({
                'id': e['id'],
                'title': e.get('summary', 'بدون عنوان'),
                'start': start,
                'location': e.get('location', ''),
                'description': e.get('description', '')[:200],
            })

        return {
            'status': 'success',
            'count': len(formatted),
            'message': f'{len(formatted)} موعد قادم في {days_ahead} ايام',
            'events': formatted,
        }

    return await loop.run_in_executor(None, _fetch)


async def tool_add_calendar_event(
    title: str,
    start_datetime: str,
    end_datetime: Optional[str] = None,
    description: str = '',
    location: str = '',
) -> Dict[str, Any]:
    """
    اضف موعدا جديدا في Google Calendar.
    title: عنوان الموعد
    start_datetime: تاريخ ووقت البداية (صيغة: '2026-10-07T14:00:00')
    end_datetime: تاريخ ووقت النهاية (اختياري، افتراضي ساعة بعد البداية)
    description: وصف الموعد
    location: مكان الموعد
    """
    loop = asyncio.get_event_loop()

    def _add():
        service, err = _get_calendar_service()
        if err:
            return {'status': 'error', 'message': err}

        try:
            start_dt = datetime.fromisoformat(start_datetime)
        except ValueError:
            return {'status': 'error', 'message': f'صيغة التاريخ غير صحيحة: {start_datetime}'}

        end_dt_str = end_datetime or (start_dt + timedelta(hours=1)).isoformat()

        event_body = {
            'summary': title,
            'description': description,
            'location': location,
            'start': {'dateTime': start_datetime, 'timeZone': 'Asia/Riyadh'},
            'end': {'dateTime': end_dt_str, 'timeZone': 'Asia/Riyadh'},
        }

        created = service.events().insert(calendarId='primary', body=event_body).execute()
        return {
            'status': 'success',
            'message': f'تم اضافة الموعد: {title} في {start_datetime}',
            'event_id': created.get('id'),
            'event_link': created.get('htmlLink', ''),
        }

    return await loop.run_in_executor(None, _add)


# ─── Register ─────────────────────────────────────────────────────────────────

tool_registry.register(
    name='get_calendar_events',
    func=tool_get_calendar_events,
    schema={
        'name': 'get_calendar_events',
        'description': 'اجلب المواعيد القادمة من Google Calendar. استخدمه عند سؤال المستخدم عن جدوله او مواعيده.',
        'parameters': {
            'type': 'object',
            'properties': {
                'days_ahead': {'type': 'integer', 'default': 7, 'description': 'عدد الايام القادمة'},
                'max_results': {'type': 'integer', 'default': 10, 'description': 'اقصى عدد مواعيد'},
            },
            'required': [],
        },
    }
)

tool_registry.register(
    name='add_calendar_event',
    func=tool_add_calendar_event,
    schema={
        'name': 'add_calendar_event',
        'description': 'اضف موعدا جديدا في Google Calendar. استخدمه عند طلب المستخدم اضافة موعد او اجتماع.',
        'parameters': {
            'type': 'object',
            'properties': {
                'title': {'type': 'string', 'description': 'عنوان الموعد'},
                'start_datetime': {'type': 'string', 'description': 'وقت البداية (2026-10-07T14:00:00)'},
                'end_datetime': {'type': 'string', 'description': 'وقت النهاية (اختياري)'},
                'description': {'type': 'string', 'description': 'وصف الموعد', 'default': ''},
                'location': {'type': 'string', 'description': 'مكان الموعد', 'default': ''},
            },
            'required': ['title', 'start_datetime'],
        },
    }
)
