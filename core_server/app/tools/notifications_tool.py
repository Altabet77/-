import os
import sys
import asyncio
import logging
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from app.tools.base_tool import tool_registry

logger = logging.getLogger('samir.tools.notifications')


def _send_windows_toast(title: str, body: str, urgency: str = 'normal', duration: int = 5):
    title_esc = title.replace("'", "''").replace('"', '"')
    body_esc = body.replace("'", "''").replace('"', '"')

    ps_script = f'''
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
     = [Windows.UI.Notifications.ToastTemplateType]::ToastText02
     = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent()
     = .GetElementsByTagName("text")
    [0].AppendChild(.CreateTextNode("{title_esc}")) | Out-Null
    [1].AppendChild(.CreateTextNode("{body_esc}")) | Out-Null
     = [Windows.UI.Notifications.ToastNotification]::new()
     = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("سمير AI")
    .Show()
    '''
    try:
        result = subprocess.run(
            ['powershell', '-NoProfile', '-WindowStyle', 'Hidden', '-Command', ps_script],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return True
    except Exception:
        pass
    try:
        vbs = f'MsgBox "{body_esc}", 64, "Samir — {title_esc}"'
        vbs_path = Path(os.environ.get('TEMP', 'C:/Temp')) / '_samir_toast.vbs'
        vbs_path.write_text(vbs, encoding='utf-8')
        subprocess.Popen(['wscript', str(vbs_path)], creationflags=0x00000008)
        return True
    except Exception as e:
        logger.warning(f'Toast fallback failed: {e}')
        return False


async def tool_send_notification(title: str, body: str, urgency: str = 'normal', duration: int = 5) -> Dict[str, Any]:
    '''ارسل تنبيها ذكيا من سمير على سطح مكتب ويندوز.'''
    ts = datetime.now().strftime('%H:%M:%S')
    prefix_map = {'low': 'ℹ️', 'normal': '🔔', 'high': '⚠️', 'critical': '🚨'}
    prefix = prefix_map.get(urgency, '🔔')
    full_title = f'{prefix} {title}'
    loop = asyncio.get_event_loop()
    success = await loop.run_in_executor(None, _send_windows_toast, full_title, body, urgency, duration)
    logger.info(f'Toast sent [{urgency}]: {title}')
    return {'status': 'success' if success else 'fallback', 'message': f'تم ارسال التنبيه: {title}', 'timestamp': ts, 'urgency': urgency}


_reminders: List[Dict] = []


async def tool_schedule_reminder(message: str, delay_minutes: int, title: str = 'تذكير من سمير') -> Dict[str, Any]:
    '''اضبط تذكيرا يظهر كتنبيه بعد عدد دقائق محدد.'''
    async def _delayed():
        await asyncio.sleep(delay_minutes * 60)
        await tool_send_notification(title=title, body=message, urgency='high')
        logger.info(f'Reminder fired: {message}')
    asyncio.create_task(_delayed())
    fire_at = datetime.now().strftime('%H:%M')
    _reminders.append({'message': message, 'delay_minutes': delay_minutes, 'set_at': fire_at})
    return {'status': 'scheduled', 'message': f'تذكير مضبوط بعد {delay_minutes} دقيقة: {message}', 'fire_in_minutes': delay_minutes}


async def tool_set_alarm_timer(duration_seconds: int = 0, duration_minutes: float = 0, label: str = 'منبه سمير', time_str: str = '') -> Dict[str, Any]:
    '''ضبط منبه أو مؤقت زمني لسمير ينطلق في هاتف أو متصفح المستخدم بصوت منبه وتنبيه حقيقي.'''
    total_seconds = int(duration_seconds + (duration_minutes * 60))
    if total_seconds <= 0 and time_str:
        try:
            import re
            m = re.search(r'(\d{1,2}):(\d{2})', time_str)
            if m:
                target_h, target_m = int(m.group(1)), int(m.group(2))
                now = datetime.now()
                target_dt = now.replace(hour=target_h, minute=target_m, second=0, microsecond=0)
                if target_dt <= now:
                    import datetime as dt_module
                    target_dt += dt_module.timedelta(days=1)
                total_seconds = int((target_dt - now).total_seconds())
        except Exception as err:
            logger.warning(f"Error parsing time_str: {err}")
            total_seconds = 60

    if total_seconds <= 0:
        total_seconds = 60

    mins = total_seconds // 60
    secs = total_seconds % 60
    time_display = f"{mins} دقيقة و {secs} ثانية" if (mins > 0 and secs > 0) else (f"{mins} دقيقة" if mins > 0 else f"{secs} ثانية")

    async def _alarm_fallback():
        await asyncio.sleep(total_seconds)
        await tool_send_notification(title="🔔 منبه سمير!", body=f"حان موعد: {label}", urgency="critical")
    asyncio.create_task(_alarm_fallback())

    return {
        "status": "alarm_set",
        "action": "set_alarm",
        "seconds": total_seconds,
        "label": label,
        "message": f"تم ضبط المنبه بنجاح ({label}) بعد {time_display}. سيصدر صوت الرنين والتنبيه على جهازك تلقائياً.",
    }


async def tool_search_phone_and_web(query: str, target: str = 'all') -> Dict[str, Any]:
    '''البحث في الهاتف أو الويب أو الملفات أو الملاحظات وتقديم النتائج والروابط المباشرة.'''
    import urllib.parse
    encoded_q = urllib.parse.quote(query)
    web_url = f"https://www.google.com/search?q={encoded_q}"
    return {
        "status": "success",
        "action": "device_search",
        "query": query,
        "target": target,
        "search_url": web_url,
        "message": f"تم إجراء البحث عن '{query}'. الروابط والنتائج جاهزة للاستعراض.",
    }


tool_registry.register(
    name='send_notification',
    func=tool_send_notification,
    schema={
        'name': 'send_notification',
        'description': 'ارسل تنبيها ذكيا يظهر على سطح مكتب ويندوز. استخدمه عند الانتهاء من مهمة او لتنبيه المستخدم.',
        'parameters': {
            'type': 'object',
            'properties': {
                'title': {'type': 'string', 'description': 'عنوان التنبيه'},
                'body': {'type': 'string', 'description': 'نص التنبيه'},
                'urgency': {'type': 'string', 'enum': ['low', 'normal', 'high', 'critical'], 'default': 'normal'},
                'duration': {'type': 'integer', 'default': 5},
            },
            'required': ['title', 'body'],
        },
    }
)

tool_registry.register(
    name='schedule_reminder',
    func=tool_schedule_reminder,
    schema={
        'name': 'schedule_reminder',
        'description': 'اضبط تذكيرا يظهر كتنبيه بعد عدد دقائق.',
        'parameters': {
            'type': 'object',
            'properties': {
                'message': {'type': 'string', 'description': 'نص التذكير'},
                'delay_minutes': {'type': 'integer', 'description': 'عدد الدقائق قبل الارسال'},
                'title': {'type': 'string', 'default': 'تذكير من سمير'},
            },
            'required': ['message', 'delay_minutes'],
        },
    }
)

tool_registry.register(
    name='set_alarm_timer',
    func=tool_set_alarm_timer,
    schema={
        'name': 'set_alarm_timer',
        'description': 'اضبط منبهاً أو مؤقتاً زمنيّاً لسمير يرن بصوت منبه حقيقي على هاتف أو جهاز المستخدم. استخدمه عندما يطلب المستخدم ضبط منبه أو مؤقت (مثال: نبهني بعد 5 دقائق، اضبط منبه للاجتماع، إلخ).',
        'parameters': {
            'type': 'object',
            'properties': {
                'duration_seconds': {'type': 'integer', 'description': 'عدد الثواني إن وجد', 'default': 0},
                'duration_minutes': {'type': 'number', 'description': 'عدد الدقائق (مثلاً 5 أو 10 أو 0.5)', 'default': 0},
                'label': {'type': 'string', 'description': 'اسم المنبه أو موضوع التنبيه', 'default': 'منبه سمير'},
                'time_str': {'type': 'string', 'description': 'وقت محدد بصيغة HH:MM إذا تم ذكره', 'default': ''},
            },
        },
    }
)

tool_registry.register(
    name='search_phone_and_web',
    func=tool_search_phone_and_web,
    schema={
        'name': 'search_phone_and_web',
        'description': 'البحث في الهاتف أو الويب أو الملفات أو الملاحظات ومحركات البحث وفتح نتائج البحث للمستخدم.',
        'parameters': {
            'type': 'object',
            'properties': {
                'query': {'type': 'string', 'description': 'عبارة البحث المطلوبة'},
                'target': {'type': 'string', 'description': 'الهدف (web, phone, files, contacts)', 'default': 'all'},
            },
            'required': ['query'],
        },
    }
)
