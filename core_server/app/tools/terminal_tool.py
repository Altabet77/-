"""
terminal_tool.py — سمير: الوصول الكامل للـ Terminal
تشغيل أوامر PowerShell / Python / Node بشكل آمن مع نظام موافقة
"""

import asyncio
import logging
import subprocess
import sys
import os
from typing import Dict, Any, Optional
from app.tools.base_tool import tool_registry

logger = logging.getLogger('samir.tools.terminal')

# الأوامر التي تحتاج تأكيد (destructive)
DANGEROUS_PATTERNS = [
    'rm -rf', 'del /f', 'format', 'rmdir', 'drop table',
    'delete from', 'shutdown', 'restart', 'taskkill',
]

def _is_dangerous(cmd: str) -> bool:
    cmd_lower = cmd.lower()
    return any(p in cmd_lower for p in DANGEROUS_PATTERNS)


async def tool_run_terminal_command(
    command: str,
    shell: str = 'powershell',
    timeout: int = 30,
    working_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    شغّل امرا في Terminal (PowerShell او CMD). مفيد لتثبيت برامج، تشغيل سكريبتات، وادارة الملفات.
    command: الامر المراد تنفيذه
    shell: نوع الـ shell — 'powershell' | 'cmd' | 'python'
    timeout: المهلة بالثواني (افتراضي 30)
    working_dir: مجلد العمل (اختياري)
    """
    if _is_dangerous(command):
        return {
            'status': 'blocked',
            'message': f'الامر محظور لانه قد يسبب فقدان بيانات: {command[:100]}. قل "تاكيد التنفيذ" اذا كنت متاكدا.',
            'command': command,
            'requires_confirmation': True,
        }

    loop = asyncio.get_event_loop()

    def _execute():
        try:
            if shell == 'powershell':
                cmd_list = ['powershell', '-NoProfile', '-Command', command]
            elif shell == 'python':
                cmd_list = [sys.executable, '-c', command]
            elif shell == 'cmd':
                cmd_list = ['cmd', '/c', command]
            else:
                cmd_list = ['powershell', '-NoProfile', '-Command', command]

            result = subprocess.run(
                cmd_list,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=working_dir,
                encoding='utf-8',
                errors='replace',
            )

            output = result.stdout.strip()
            error = result.stderr.strip()
            success = result.returncode == 0

            return {
                'status': 'success' if success else 'error',
                'command': command,
                'output': output[:2000] if output else '(لا يوجد خرج)',
                'error': error[:500] if error else '',
                'exit_code': result.returncode,
                'message': output[:500] if output else ('خطا: ' + error[:300] if error else 'تم التنفيذ'),
            }
        except subprocess.TimeoutExpired:
            return {'status': 'timeout', 'message': f'انتهت مهلة التنفيذ ({timeout}ث)', 'command': command}
        except Exception as e:
            return {'status': 'error', 'message': str(e), 'command': command}

    result = await loop.run_in_executor(None, _execute)
    logger.info(f'Terminal [{shell}] exit={result.get("exit_code", "?")} cmd={command[:80]}')
    return result


async def tool_install_package(
    package_name: str,
    manager: str = 'pip',
) -> Dict[str, Any]:
    """
    ثبّت حزمة برمجية (pip / npm / winget).
    package_name: اسم الحزمة
    manager: 'pip' | 'npm' | 'winget' | 'choco'
    """
    cmd_map = {
        'pip': f'{sys.executable} -m pip install {package_name} --quiet',
        'npm': f'npm install -g {package_name}',
        'winget': f'winget install {package_name} --accept-package-agreements --accept-source-agreements',
        'choco': f'choco install {package_name} -y',
    }

    if manager not in cmd_map:
        return {'status': 'error', 'message': f'مدير حزم غير مدعوم: {manager}'}

    command = cmd_map[manager]
    result = await tool_run_terminal_command(command=command, shell='powershell', timeout=120)
    if result.get('status') in ('success', 'error'):
        result['message'] = f'تثبيت {package_name} عبر {manager}: {result.get("message", "")}'
    return result


# ─── Register ─────────────────────────────────────────────────────────────────

tool_registry.register(
    name='run_terminal_command',
    func=tool_run_terminal_command,
    schema={
        'name': 'run_terminal_command',
        'description': 'شغّل امرا في Terminal (PowerShell). مفيد لتثبيت برامج، تشغيل سكريبتات، فحص النظام، ادارة الملفات.',
        'parameters': {
            'type': 'object',
            'properties': {
                'command': {'type': 'string', 'description': 'الامر المراد تنفيذه'},
                'shell': {'type': 'string', 'enum': ['powershell', 'cmd', 'python'], 'default': 'powershell'},
                'timeout': {'type': 'integer', 'default': 30, 'description': 'المهلة بالثواني'},
                'working_dir': {'type': 'string', 'description': 'مجلد العمل (اختياري)'},
            },
            'required': ['command'],
        },
    }
)

tool_registry.register(
    name='install_package',
    func=tool_install_package,
    schema={
        'name': 'install_package',
        'description': 'ثبت حزمة برمجية باستخدام pip او npm او winget. استخدمه عند طلب تثبيت مكتبة او برنامج.',
        'parameters': {
            'type': 'object',
            'properties': {
                'package_name': {'type': 'string', 'description': 'اسم الحزمة او البرنامج'},
                'manager': {'type': 'string', 'enum': ['pip', 'npm', 'winget', 'choco'], 'default': 'pip'},
            },
            'required': ['package_name'],
        },
    }
)
