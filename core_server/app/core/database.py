import aiosqlite
import logging
from typing import AsyncGenerator
from app.core.config import settings

logger = logging.getLogger("samir.db")

INIT_DB_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    google_id TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    picture TEXT,
    session_token TEXT,
    password_hash TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, key)
);

CREATE TABLE IF NOT EXISTS devices (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    device_type TEXT NOT NULL, -- 'windows', 'android', 'web'
    token TEXT NOT NULL,
    status TEXT DEFAULT 'offline', -- 'online', 'offline', 'busy'
    ip_address TEXT,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    category TEXT DEFAULT 'general', -- 'user_preference', 'project', 'system', 'fact'
    is_user_approved BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT,
    summary TEXT,
    provider_used TEXT,
    message_count INTEGER DEFAULT 0,
    device_id TEXT,
    user_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    session_id TEXT,
    sender TEXT NOT NULL, -- 'user', 'samir', 'system'
    content TEXT NOT NULL,
    provider TEXT,
    model TEXT,
    routing_reason TEXT,
    audio_path TEXT,
    tool_calls_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS command_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT,
    tool_name TEXT NOT NULL,
    arguments TEXT,
    status TEXT NOT NULL, -- 'success', 'failed', 'pending_approval', 'rejected'
    risk_level TEXT DEFAULT 'LOW', -- 'LOW', 'MEDIUM', 'HIGH', 'BLOCKED'
    result TEXT,
    error_message TEXT,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'pending', -- 'pending', 'in_progress', 'done', 'cancelled'
    priority TEXT DEFAULT 'normal', -- 'low', 'normal', 'high', 'urgent'
    category TEXT DEFAULT 'general',
    due_date TEXT,
    reminder_at TEXT,
    is_recurring BOOLEAN DEFAULT 0,
    recurrence_rule TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL, -- 'tool_executed', 'message_sent', 'mode_activated', 'memory_saved'
    summary TEXT NOT NULL,
    details TEXT,
    tool_name TEXT,
    status TEXT DEFAULT 'success', -- 'success', 'failed', 'confirmed', 'rejected'
    session_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS modes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE, -- 'creator', 'gaming', 'work', 'night'
    display_name TEXT NOT NULL,
    description TEXT,
    steps TEXT NOT NULL, -- JSON array of tool calls
    is_active BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS custom_commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_phrase TEXT NOT NULL UNIQUE,
    action_type TEXT NOT NULL, -- 'mode', 'tool', 'message', 'sequence'
    action_data TEXT NOT NULL, -- JSON
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS learned_lessons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    correction TEXT NOT NULL,
    context TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS samir_knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    summary TEXT NOT NULL,
    details TEXT,
    key_points TEXT, -- JSON array
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge_network (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept TEXT NOT NULL UNIQUE,
    category TEXT DEFAULT 'general',
    summary TEXT NOT NULL,
    details TEXT,
    connected_topics TEXT, -- JSON array of related concepts
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# Seed default modes if not present
SEED_MODES_SQL = """
INSERT OR IGNORE INTO modes (name, display_name, description, steps) VALUES
(
    'creator',
    'وضع صانع المحتوى',
    'يجهز بيئة العمل لإنتاج المحتوى: OBS، برنامج المونتاج، مجلد المشاريع، YouTube Studio',
    '[
        {"tool": "open_application", "args": {"app_name": "obs"}},
        {"tool": "open_application", "args": {"app_name": "davinci resolve"}},
        {"tool": "open_url", "args": {"url": "https://studio.youtube.com"}},
        {"tool": "open_application", "args": {"app_name": "discord"}}
    ]'
),
(
    'gaming',
    'وضع الألعاب',
    'يجهز بيئة الألعاب: Discord، OBS للتسجيل، وإغلاق البرامج الثقيلة',
    '[
        {"tool": "open_application", "args": {"app_name": "discord"}},
        {"tool": "open_application", "args": {"app_name": "obs"}}
    ]'
),
(
    'work',
    'وضع العمل',
    'يجهز بيئة العمل: المتصفح، البريد الإلكتروني، وأدوات الإنتاجية',
    '[
        {"tool": "open_application", "args": {"app_name": "brave"}},
        {"tool": "open_url", "args": {"url": "https://gmail.com"}},
        {"tool": "open_application", "args": {"app_name": "vscode"}}
    ]'
),
(
    'night',
    'وضع الليل',
    'يقلل الإشعارات ويجعل المساعد في وضع هادئ',
    '[
        {"tool": "set_volume", "args": {"action": "set", "level": 20}}
    ]'
);
"""

async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db

async def init_database():
    """تهيئة قاعدة البيانات وإنشاء الجداول المطلوبة"""
    logger.info(f"Initializing database at: {settings.DB_PATH}")
    Path(settings.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(settings.DB_PATH) as db:

        await db.executescript(INIT_DB_SQL)
        await db.executescript(SEED_MODES_SQL)
        # التأكد من وجود عمود password_hash في قواعد البيانات القديمة
        try:
            await db.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
        except Exception:
            pass  # العمود موجود مسبقاً
        try:
            await db.execute("ALTER TABLE conversations ADD COLUMN device_id TEXT")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE conversations ADD COLUMN user_id TEXT")
        except Exception:
            pass
        await db.commit()
    logger.info("Database schema initialized successfully.")
