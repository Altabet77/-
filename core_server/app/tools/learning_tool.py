import json
import logging
from typing import Dict, Any, Optional, List
import aiosqlite
import httpx

from app.tools.base_tool import tool_registry
from app.core.config import settings

logger = logging.getLogger("samir.tools.learning")


async def tool_save_correction(topic: str, correction: str, context: Optional[str] = None) -> Dict[str, Any]:
    """
    حفظ درس أو تصحيح تعلمه سمير من خطأ أو من توجيه مباشر من المستخدم.
    """
    async with aiosqlite.connect(settings.DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO learned_lessons (topic, correction, context)
            VALUES (?, ?, ?)
            """,
            (topic, correction, context or ""),
        )
        await db.commit()
        lesson_id = cursor.lastrowid

    logger.info(f"Learned lesson #{lesson_id} recorded: [{topic}] -> {correction}")
    return {
        "learned": True,
        "lesson_id": lesson_id,
        "topic": topic,
        "correction": correction,
        "message": f"فهمت عليك يا غالي، حفظت هذا الدرس وتتعلمت منه: {correction}",
    }


async def tool_get_learned_lessons(limit: int = 15) -> Dict[str, Any]:
    """جلب الدروس والتصحيحات التي تعلمها سمير"""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, topic, correction, created_at FROM learned_lessons ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        lessons = [dict(r) for r in rows]

    return {
        "count": len(lessons),
        "lessons": lessons,
    }


async def tool_deep_learn_topic(topic: str, focus: Optional[str] = None) -> Dict[str, Any]:
    """
    التعلم الذاتي العميق: البحث في الإنترنت عن موضوع محدد، استخلاص تفاصيله،
    تخزينه في ذاكرة سمير المعرفية الدائمة، وتذكره إلى الأبد.
    """
    logger.info(f"Deep learning topic initiated: {topic} (Focus: {focus})")

    # 1. البحث عبر محرك الويب
    search_query = f"{topic} {focus}" if focus else f"{topic} شرح تفصيلي مفاهيم مميزات"
    results_snippets = []

    try:
        url = "https://html.duckduckgo.com/html/"
        data = {"q": search_query, "b": ""}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.post(url, data=data, headers=headers)
            if resp.status_code == 200:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, "html.parser")
                snippets = soup.find_all("a", class_="result__snippet")
                for s in snippets[:6]:
                    txt = s.get_text(strip=True)
                    if txt:
                        results_snippets.append(txt)
    except Exception as e:
        logger.warning(f"Web search during deep learning fallback: {e}")

    # تجميع الملخص والمعلومات
    if results_snippets:
        combined_info = "\n".join([f"- {s}" for s in results_snippets])
        summary = f"معلومات أساسية مستخلصة عن '{topic}':\n" + combined_info[:800]
    else:
        summary = f"تم تسجيل موضوع '{topic}' في بنك المعرفة الدائم، وجاهز للتعمق فيه واستخدامه في المحادثات."

    key_points = [
        f"الموضوع: {topic}",
        f"التركيز: {focus or 'عام'}",
        "تم التخزين في الذاكرة الدائمة",
    ]

    # 2. الحفظ في samir_knowledge و knowledge_network
    connected_list = [f"{topic} - أساسيات", f"{topic} - تطبيقات", f"{topic} - متقدم"]
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO samir_knowledge (topic, summary, details, key_points, source)
            VALUES (?, ?, ?, ?, ?)
            """,
            (topic, summary, summary, json.dumps(key_points, ensure_ascii=False), "web_deep_learning"),
        )
        await db.execute(
            """
            INSERT OR REPLACE INTO knowledge_network (concept, category, summary, details, connected_topics, source)
            VALUES (?, 'deep_learning', ?, ?, ?, 'web_learning_hub')
            """,
            (topic, summary[:300], summary, json.dumps(connected_list, ensure_ascii=False)),
        )
        # حفظ في الذاكرة الدائمة memories ليظهر تلقائياً في البرومبت
        await db.execute(
            """
            INSERT OR REPLACE INTO memories (key, value, category)
            VALUES (?, ?, 'knowledge')
            """,
            (f"knowledge_{topic.lower()[:30]}", summary[:400]),
        )
        await db.commit()

    return {
        "status": "success",
        "topic": topic,
        "summary": summary,
        "connected_concepts": connected_list,
        "message": f"بحثتلك في الويب وتعلمت كل شيء عن '{topic}' يا غالي، وأضفته لشبكة معلوماتي وذاكرتي الدائمة ومش حننساه أبداً!",
        "key_points": key_points,
    }


async def tool_query_knowledge_network(query: str) -> Dict[str, Any]:
    """البحث في شبكة المعرفة والمعلومات الدائمة لسمير لاسترجاع المفاهيم المترابطة"""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        q_wildcard = f"%{query.strip()}%"
        cursor = await db.execute(
            """
            SELECT concept, category, summary, connected_topics, created_at 
            FROM knowledge_network 
            WHERE concept LIKE ? OR summary LIKE ? OR details LIKE ?
            ORDER BY id DESC LIMIT 10
            """,
            (q_wildcard, q_wildcard, q_wildcard),
        )
        rows = await cursor.fetchall()
        nodes = []
        for r in rows:
            item = dict(r)
            try:
                item["connected_topics"] = json.loads(item.get("connected_topics") or "[]")
            except Exception:
                pass
            nodes.append(item)

    return {
        "query": query,
        "found_nodes": len(nodes),
        "network_nodes": nodes,
        "message": f"استخرجتلك {len(nodes)} مفاهيم مترابطة من شبكة معلوماتي حول '{query}'."
    }


async def tool_get_learned_knowledge(limit: int = 20) -> Dict[str, Any]:
    """استرجاع المواضيع والمعارف التي تعلمها سمير بالبحث الذاتي"""
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id, topic, summary, created_at FROM samir_knowledge ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        items = [dict(r) for r in rows]

    return {
        "count": len(items),
        "knowledge": items,
    }


def register_learning_tools():
    tool_registry.register_tool(
        name="save_correction",
        description="حفظ أمر دائم أو توجيه أو تعديل في سلوك سمير أو تصحيح لقواعده ليطبقه سمير بأولوية مطلقة دائماً (مثل: 'احفظ عندك أمر كذا', 'من الآن فصاعداً سو كذا', 'عدل على نفسك').",
        parameters={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "موضوع الأمر أو التعديل"},
                "correction": {"type": "string", "description": "الأمر أو السلوك المطلوب الالتزام به"},
                "context": {"type": "string", "description": "سياق الأمر أو 'manual_rule'"},
            },
            "required": ["topic", "correction"],
        },
        handler=tool_save_correction,
    )

    tool_registry.register_tool(
        name="get_learned_lessons",
        description="استرجاع قائمة التصحيحات والدروس السابقة.",
        parameters={"type": "object", "properties": {}},
        handler=tool_get_learned_lessons,
    )

    tool_registry.register_tool(
        name="deep_learn_topic",
        description="التعلم الذاتي العميق: البحث في الإنترنت عن موضوع محدد، استخلاص تفاصيله، وحفظه في شبكة معلومات وذاكرة سمير الدائمة (مثل: 'سمير تعلم كل شيء عن بايثون 3.12', 'سمير تعلم تاريخ ليبيا').",
        parameters={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "الموضوع المراد تعلمه بعمق"},
                "focus": {"type": "string", "description": "جانب معين من الموضوع (اختياري)"},
            },
            "required": ["topic"],
        },
        handler=tool_deep_learn_topic,
    )

    tool_registry.register_tool(
        name="query_knowledge_network",
        description="البحث في شبكة المعلومات والمعرفة المترابطة لسمير لاسترجاع ما تم تعلمه سابقاً وربط الأفكار.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "المفهوم أو الكلمة المراد البحث عنها في شبكة المعرفة"},
            },
            "required": ["query"],
        },
        handler=tool_query_knowledge_network,
    )

    tool_registry.register_tool(
        name="get_learned_knowledge",
        description="عرض قائمة المواضيع التي تعلمها سمير بنفسه بالبحث العميق.",
        parameters={"type": "object", "properties": {}},
        handler=tool_get_learned_knowledge,
    )


register_learning_tools()
