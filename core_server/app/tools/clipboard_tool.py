import asyncio
import logging
import subprocess
import sys
from typing import Dict, Any

from app.tools.base_tool import tool_registry

logger = logging.getLogger('samir.tools.clipboard')


async def tool_get_clipboard() -> Dict[str, Any]:
    '''اقرا محتوى الحافظة (Clipboard) الحالية.'''
    try:
        result = subprocess.run(
            ['powershell', '-NoProfile', '-Command', 'Get-Clipboard'],
            capture_output=True, text=True, timeout=5
        )
        text = result.stdout.strip()
        if not text:
            return {'status': 'empty', 'message': 'الحافظة فارغة', 'content': ''}
        return {'status': 'success', 'message': f'محتوى الحافظة: {text[:200]}...', 'content': text}
    except Exception as e:
        return {'status': 'error', 'message': str(e), 'content': ''}


async def tool_set_clipboard(text: str) -> Dict[str, Any]:
    '''انسخ نصا الى الحافظة (Clipboard). مفيد لنسخ نتائج او ردود سمير مباشرة.'''
    try:
        subprocess.run(
            ['powershell', '-NoProfile', '-Command', f'Set-Clipboard -Value @\"{text}\"@'],
            capture_output=True, text=True, timeout=5, check=True
        )
        preview = text[:100] + ('...' if len(text) > 100 else '')
        return {'status': 'success', 'message': f'تم نسخ النص الى الحافظة: {preview}'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


tool_registry.register(
    name='get_clipboard',
    func=tool_get_clipboard,
    schema={
        'name': 'get_clipboard',
        'description': 'اقرا ما في حافظة النسخ (Clipboard) الحالية. استخدمه عندما يقول المستخدم "اقرا اللي نسخته" او "شو في الكلبورد".',
        'parameters': {'type': 'object', 'properties': {}, 'required': []},
    }
)

tool_registry.register(
    name='set_clipboard',
    func=tool_set_clipboard,
    schema={
        'name': 'set_clipboard',
        'description': 'انسخ نصا الى الحافظة مباشرة. مفيد لتجهيز ردود او بيانات للمستخدم.',
        'parameters': {
            'type': 'object',
            'properties': {
                'text': {'type': 'string', 'description': 'النص الذي سيتم نسخه الى الحافظة'}
            },
            'required': ['text'],
        },
    }
)
