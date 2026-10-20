"""
Strategic Planner Module for Samir (عقل التخطيط الاستراتيجي المستوحى من Antigravity)

يوفر هذا الموديول قدرات التفكير الاستراتيجي المتقدم:
1. تحليل وتفكيك المهام المعقدة إلى مراحل منظمة (بحث/استكشاف -> خطة تنفيذ -> تنفيذ أدوات -> تحقق واختبار).
2. فحص مخرجات الأدوات بدقة لاكتشاف الأخطاء أو عدم اكتمال المهمة تلقائياً.
3. صياغة توجيهات التصحيح الذاتي (Self-Correction) لسمير دون استسلام عند حدوث أي خطأ برمجي أو تقني.
"""

import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("samir.ai.strategic_planner")


class StrategicPlanner:
    """منظم التفكير والتخطيط الاستراتيجي لسمير على غرار Antigravity"""

    @staticmethod
    def analyze_task_complexity(user_text: str) -> Dict[str, Any]:
        """
        تحليل مستوى تعقيد الطلب لتحديد ما إذا كان يتطلب تفكيراً استراتيجياً وتخطيطاً مسبقاً.
        """
        complex_keywords = [
            "ابني", "انشئ مشروع", "صمم تطبيق", "حل مشكلة", "خطط",
            "استراتيجية", "صلح الكود", "تطوير كامل", "موقع كامل",
            "أتمتة", "debug", "refactor", "build", "architecture",
            "antigravity", "أنتي قرافيتي", "مهارة", "skill"
        ]
        
        text_lower = user_text.lower()
        matches = [kw for kw in complex_keywords if kw in text_lower]
        is_complex = len(matches) > 0 or len(user_text.split()) > 25

        return {
            "is_complex": is_complex,
            "matched_keywords": matches,
            "recommended_strategy": "plan_execute_verify" if is_complex else "direct_execute"
        }

    @staticmethod
    def verify_tool_result(tool_name: str, arguments: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
        """
        التحقق الصارم من نتيجة تنفيذ الأداة ومطابقتها لمعايير الجودة (Verification Phase).
        يمنع الادعاء بنجاح العملية إذا فشل الأمر أو حدث استثناء.
        """
        status = result.get("status", "unknown")
        
        # فحص حالات الخطأ الشائعة
        has_error = False
        error_details = ""

        if status in ["error", "blocked"]:
            has_error = True
            error_details = result.get("message", "حدث خطأ غير محدد أثناء تنفيذ الأداة.")
        elif "output" in result:
            output_str = str(result["output"]).lower()
            if "error:" in output_str or "traceback (most recent call last)" in output_str or "exception:" in output_str:
                has_error = True
                error_details = f"تحذير: يحتوي خرج الأداة على رسائل خطأ استثنائية: {output_str[:300]}"

        return {
            "verified": not has_error,
            "tool_name": tool_name,
            "error_details": error_details,
            "suggestion": (
                f"فشلت أداة {tool_name} أو أرجعت خطأ. لا تستسلم! افحص الخطأ التالي وقم بتصحيحه أو استخدام طريقة بديلة فوراً:\n{error_details}"
                if has_error else "تم التنفيذ والتحقق بنجاح."
            )
        }

    @staticmethod
    def format_strategic_guidance() -> str:
        """
        توجيهات التفكير الاستراتيجي التي تُحقن في وعي سمير.
        """
        return """
# مبادئ التفكير الاستراتيجي والهندسي (Antigravity Strategic Principles):
1. **حلل المشكلة أولاً ولا تتسرع**:
   - افهم المطلوب بدقة، وحدد الملفات أو الأدوات المستهدفة قبل أي كتابة أو تشغيل.
2. **نفّذ خطوة بخطوة وتحقق من النتائج (Execute & Verify)**:
   - بعد كل استدعاء لأداة (Tool Call)، اقرأ النتيجة وتحقق منها. لا تفترض أن الملف تم تعديله أو التطبيق فُتح دون مراجعة المخرج.
3. **التصحيح الذاتي التلقائي (Self-Correction)**:
   - إذا حدث خطأ في تنفيذ أمر أو تعديل كود، افحص رسالة الخطأ بعمق، وحدد السبب الجذري، وعدل مقاربتك فوراً في الدورة التالية دون إزعاج المستخدم باعتذارات متكررة.
4. **الارتباط ببيئة ومصادر أنتي قرافيتي (Antigravity Ecosystem)**:
   - لديك إمكانية استخدام أدوات `antigravity_list_skills` و `antigravity_read_skill` لقراءة المهارات والتعليمات الرسمية لحل التحديات البرمجية المعقدة.
"""


strategic_planner = StrategicPlanner()
