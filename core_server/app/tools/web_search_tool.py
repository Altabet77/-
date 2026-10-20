import logging
from typing import Dict, Any, List, Optional
from app.tools.base_tool import tool_registry

logger = logging.getLogger("samir.tools.web_search")


async def tool_web_search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """البحث في الإنترنت عبر DuckDuckGo"""
    try:
        from duckduckgo_search import DDGS

        results: List[Dict[str, str]] = []
        with DDGS() as ddgs:
            search_results = list(ddgs.text(query, max_results=max_results))

        for r in search_results:
            results.append({
                "title": r.get("title", ""),
                "snippet": r.get("body", ""),
                "url": r.get("href", ""),
            })

        if not results:
            return {
                "found": False,
                "query": query,
                "message": "ما لقيت نتائج للبحث عن: " + query,
            }

        # تلخيص النتائج بشكل مناسب للرد الصوتي
        summary_parts = []
        for i, r in enumerate(results[:3], 1):
            snippet = r["snippet"][:200].strip()
            if snippet:
                summary_parts.append(f"{i}. {r['title']}: {snippet}")

        return {
            "found": True,
            "query": query,
            "results_count": len(results),
            "summary": "\n".join(summary_parts),
            "results": results,
        }

    except ImportError:
        logger.error("duckduckgo-search not installed. Run: pip install duckduckgo-search")
        return {
            "found": False,
            "error": "مكتبة البحث غير مثبتة. شغل: pip install duckduckgo-search",
        }
    except Exception as e:
        logger.error(f"Web search error: {e}", exc_info=True)
        return {
            "found": False,
            "error": str(e),
            "message": "ما قدرتش أبحث في الإنترنت حالياً.",
        }


def register_web_search_tools():
    tool_registry.register_tool(
        name="web_search",
        description=(
            "البحث في الإنترنت عن معلومات حديثة، أخبار، أسعار، مواصفات، أو أي شيء "
            "لا تجده في معلوماتك الموجودة. استخدم هذه الأداة عندما يسأل المستخدم "
            "عن معلومات تحتاج تأكيد حديث أو عن أحداث جارية."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "نص البحث (مثال: 'سعر الذهب اليوم', 'آخر إصدار iPhone', 'طريقة عمل VPN')",
                },
                "max_results": {
                    "type": "integer",
                    "description": "عدد النتائج المطلوبة (افتراضي: 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
        handler=tool_web_search,
    )


register_web_search_tools()
