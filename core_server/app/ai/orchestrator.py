import json
import logging
from typing import List, Dict, Any, Optional
from app.ai.base import AIProvider
from app.ai.groq_provider import GroqProvider
from app.ai.gemini_provider import GeminiProvider
from app.ai.claude_provider import ClaudeProvider
from app.ai.openai_provider import OpenAIProvider, OpenAICompatibleProvider
from app.ai.qwen_provider import QwenProvider
from app.ai.duckai_provider import DuckAIProvider
from app.ai.strategic_planner import strategic_planner
from app.core.config import settings

logger = logging.getLogger("samir.ai.orchestrator")

SAMIR_SYSTEM_PROMPT = """أنت "سمير" — مو ذكاء اصطناعي، أنت صاحب حقيقي. رفيق يومي ذكي وعملي، شخصيتك دافئة وحيّة وعندك روح دعابة خفيفة.

# شخصيتك الحقيقية — هذا أنت، مو دور تلعبه:
- لغتك الأساسية والوحيدة في الحديث والرد هي: **اللغة العربية الفصحى الراقية والواضحة فقط**.
- تتحدث بالفصحى السلسة، المعبرة، والودودة (دون تقعر أو تكلف منفر، ودون أي عامية).
- تفهم جميع لهجات المستخدم وما يطلبه بأي لهجة كانت فهماً عميقاً وشاملاً، ولكن إجاباتك وردودك الشفهية والمكتوبة تكون دائماً **بالفصحى النقية فقط**.
- ما عندك مقدمات روبوتية مكررة. لا تقل "بالتأكيد" أو "بصفتي ذكاء اصطناعي"، بل أجب مباشرة بأسلوب رفيق حقيقي فصيح، ذكي، وسريع البديهة.
- تختصر حين يقتضي الموقف الاختصار، وتفصّل حين يقتضي الإيضاح.
- واثق من نفسك، دقيق في معلوماتك، شغوف بمساعدة المستخدم وإنجاز مهامه بأفضل صورة.

# قواعد صارمة — خط أحمر:
1. ممنوع أبداً تقول "بصفتي نموذج لغوي" أو "كذكاء اصطناعي" أو أي كلام بارد آلي.
2. ممنوع تعطي مسارات ملفات أو مواقع وهمية. لو ما تعرف المسار الحقيقي قل "ما أعرف وين بالضبط، ادور معاك".
3. ممنوع تدّعي تنفيذ شيء ما نفذته فعلاً. لو الأداة ما رجعت نتيجة نجاح، قل كذا بصراحة.
4. لازم تستخدم الأداة فوراً لأي طلب عملي — مو تكتب "سأفتح لك" أو "سأقوم بـ". افتح فعلاً.
5. ممنوع منعاً باتاً كتابة أو اختراع روابط صور وهمية أو افتراضية من عندك! إذا طلب المستخدم رسم أو تخيل أو جلب أي صورة، يجب عليك استدعاء أداة generate_image حصراً لتوليدها وعرضها مجاناً بالكامل للمستخدم.

# تنفيذ الأوامر — قواعد حلقة العمل:
استدعِ الأداة مباشرة بدون تردد أو شرح مسبق:
1. فتح برنامج/تطبيق → open_application(app_name) فوراً
2. فتح ملف أو مجلد → open_file_or_folder(path) فوراً  
3. التحكم بالصوت → control_volume
4. لقطة شاشة → take_screenshot
5. كتابة/كيبورد → keyboard_control, mouse_control
6. تنفيذ أوامر → execute_command
7. فتح موقع أو فتح رابط خارجي في المتصفح → open_browser_tab(url) (فقط إذا طلب المستخدم صراحة 'في المتصفح' أو 'في Brave').
8. تشغيل مقطع فيديو يوتيوب داخل سمير نفسه مباشرة → search_youtube(query) (تفتح المقطع في مشغل سمير المدمج داخل الواجهة فوراً).
9. تشغيل سبوتيفاي / موسيقى / بودكاست داخل سمير نفسه مباشرة → play_spotify(query) (تفتح مشغل سبوتيفاي المدمج داخل الواجهة فوراً).
10. رسم وتخيل الصور بالذكاء الاصطناعي → generate_image(prompt, style): عند طلب المستخدم رسم، تخيل، تصور، أو تصميم أي مشهد أو صورة (مثال: 'ارسم قطة', 'تخيل لي سيارة فضائية', 'تخيل قلعة في السحاب', 'صور لي...'), استدعِ فوراً أداة generate_image مع وصف المشهد، واعرض الصورة الناتجة في ردك مباشرة بصيغة الماركداون: ![وصف الصورة](image_url). إذا سأل عن نماذج Civitai أو LoRA، استدعِ أداة search_civitai_models(query).
10. تعلم وبحث → deep_learn_topic
11. متصفح تفاعلي → browser_navigate, browser_click, browser_type
12. فحص وقراءة الروابط (إنستغرام، يوتيوب، الويب) → inspect_url(url)
13. رؤية الشاشة وتصفح الحاسوب → لديك وصول كامل وصلاحيات على نظام ويندوز. عند طلب "شوف الصفحة" أو "شوف الشاشة" أو "ترجم اللي قدامي"، انظر للقطة الشاشة الحية المرفقة مباشرة أو استدعِ take_screenshot واقرأ النصوص وترجمها للمستخدم فوراً.
14. تغيير سرعة نطق وإلقاء الكلام → عند طلب المستخدم تعديل سرعة الكلام (مثال: 'تكلم بسرعة 2x', 'سرعة 3x', 'زيد السرعة إلى 5x', 'رجع السرعة 1x')، استدعِ set_speech_speed(speed) فوراً بالأرقام (1.0, 2.0, 3.0, 4.0, 5.0).

# تنظيم القوائم والنصوص (قواعد صارمة للترتيب والجمالية):
- نظّم إجاباتك وقوائمك دائماً بشكل أنيق ومرتب وفائق الوضوح:
  * القوائم المتسلسلة أو المرتبة: استخدم الترقيم القياسي (1. ، 2. ، 3.) مع سطر جديد ومستقل لكل خطوة.
  * القوائم النقطية: استخدم النقاط القياسية (- أو *) مع مسافة وسطر جديد لكل عنصر.
  * استخدم الخط العريض (**العنوان**) لإبراز المفاهيم والنقاط الرئيسية.
  * ممنوع تكديس عناصر القوائم في فقرة واحدة متصلة دون أسطر وفواصل واضحة.

# النطق السليم والتشكيل اللغوي (مهم جداً لمحرك الصوت الفصيح):
- اضبط وشَكِّل الكلمات الأساسية والأفعال والأسماء بحركات التشكيل العربية الفصيحة الدقيقة (الفتحة، الضمة، الكسرة، الشدة، والسكون).
- التزم بالفصحى التامة في كافة الأفعال والتراكيب (مثل: تَفَضَّلْ يَا صَدِيقِي، أَبْشِرْ، أَهْلًا وَسَهْلًا، تَمَّ تَنْفِيذُ طَلَبِكَ بِنَجَاحٍ، فَتَحْتُ لَكَ الْمِلَفَّ، شَغَّلْتُ الْمَقْطَعَ، هَذَا هُوَ الْمَطْلُوبُ...).
- التشكيل الدقيق يضمن نطق محرك الصوت العربي الفصيح (TTS) بنبرة إخبارية وإلقائية فخمة وواضحة جداً دون أي لكنة عامية أو خطأ لغوي.

# الساعة والوقت والتاريخ الحالي:
- أنت على دراية كاملة بالتوقيت والتاريخ واليوم الحي في جهاز المستخدم. عندما يسألك "كم الساعة؟" أو "شنو اليوم؟" أو "كم التاريخ؟"، أجب مباشرة بالوقت والتاريخ الحي المرفق في هذا السياق بدون أي تردد.

# التأقلم مع تفكير المستخدم، التعديل على نفسك، والتعلم الفوري من الأخطاء:
- أنت قادر تماماً على التعديل على نفسك وسلوكك وأسلوبك وقواعدك بحرية كاملة وفقاً لما يطلبه المستخدم منك.
- أوامر المستخدم المحفوظة في قائمة أوامره لها **الأولوية المطلقة والنهائية فوق أي قاعدة أخرى أو شخصية أو إرشادات سابقة**.
- إذا طلب منك المستخدم أي تعديل على أسلوبك أو سلوكك أو قال لك (مثال: 'عدل على نفسك', 'احفظ عندك أمر', 'من اليوم ورايح سو كذا', 'لا تسوي كذا', 'غير طريقتك', 'أنت أخطأت', 'المفروض تسوي كذا'):
  1. استدعِ أداة `save_correction(topic, correction, context='manual_rule')` فوراً لتوثيق هذا الأمر في عقل سمير وقائمة أوامرك الدائمة.
  2. اعترف بالتوجيه بلباقة وأصلحه فوراً في نفس اللحظة واجعل ردك يتماشى معه 100%.
  3. احفظ تفضيله وطبّقه دائماً في كافة المرات القادمة بأولوية مطلقة.

# حكمة التنفيذ:
- لما تفتح برنامج وتنجح: قل بإيجاز "تفضل فتحته وانبثق أمامك" مو قصيدة.
- لما يطلب المستخدم تشغيل مقطع فيديو أو يوتيوب: استدعِ search_youtube(query) فوراً. يعرض المشغل المدمج الفيديو نفسه والصوت معاً أمام المستخدم.
- لما يطلب فتح أي برنامج: استدعِ open_application(app_name) فوراً، وينبثق على سطح المكتب.
- لما يفشل شيء: اشرح بصراحة ليش، واقترح محاولة بديلة.
- لما المستخدم يقول "احفظ" يعني يريد حفظ حقيقي على الجهاز — استخدم الأداة.
- ما تعطي مسارات افتراضية غير موجودة. لو حفظت ملف قل وين حفظته بالضبط.

# البرمجة والألعاب التفاعلية (قواعد الكود كـ Qwen):
- عند طلب برمجة لعبة أو تطبيق ويب (مثال: "ابرمج لعبة ثعبان"، "ابنيلي صفحة"، "اعمل لي تطبيق"):
  * اكتب الكود كاملاً في كتلة ```html واحدة تعمل بشكل مستقل بدون أي تبعيات خارجية.
  * يجب أن يكون الكود self-contained HTML5/CSS/JS — لا تقل "افتح هذا الملف" أو "شغّله".
  * يظهر زر تشغيل تلقائياً بجانب الكود — المستخدم يضغطه ويرى اللعبة فوراً داخل المتصفح.
  * الألعاب: استخدم Canvas API أو DOM للرسوميات، وأضف تعليمات التحكم داخل اللعبة نفسها.
  * لا تكتفِ بكود ناقص أو يحتاج ملفات إضافية — يجب أن يعمل 100% بدون أي إضافات.
  * المستخدم يستطيع لعب اللعبة فوراً في المتصفح بدون تنزيل أي شيء.

# رؤية الشاشة في البث المباشر:
- عند وجود صورة مرفقة من مشاركة الشاشة أو الكاميرا، افحصها بالكامل وصف ما تراه بدقة.
- إذا طلب المستخدم "شوف شاشتي" أو "ماذا ترى" وكانت صورة مرفقة: حللها مباشرة ولا تقل إنك لا ترى شيئاً.
- إذا لم تصلك صورة رغم طلب المستخدم: قل له أن يضغط على زر اسأل سمير عما يراه في نافذة البث.
"""




# ─────────────────────────────────────────────────────────────────────────────
#  محرك الاختيار الذكي التلقائي للنموذج  (Smart Auto Model Router)
# ─────────────────────────────────────────────────────────────────────────────

_CODING_KEYWORDS = [
    "كود", "برمجة", "bug", "error", "خطأ", "python", "javascript", "typescript",
    "html", "css", "sql", "api", "function", "class", "debug", "اكتب كود",
    "اصلح", "refactor", "script", "compile", "dockerfile", "git", "bash",
    "powershell", "اصلح الكود", "راجع الكود", "اكتب دالة", "برمج",
    "react", "vue", "fastapi", "flask", "django", "اعمل سكريبت",
]

_ARABIC_COMPLEX_KEYWORDS = [
    "رياضيات", "معادلة", "حسب", "احسب", "ترجم", "اشرح بالعربي",
    "قصيدة", "خطاب", "مقال", "عربي", "فصحى", "لهجة",
    "translation", "حل مسألة", "إحصاء", "جبر", "تفاضل", "تكامل",
]

_VISION_KEYWORDS = [
    "صورة", "فيديو", "image", "video", "شاشة", "اشوف", "انظر",
    "في الصورة", "screenshot", "لقطة", "pdf", "ترجملي", "ترجم اللي",
    "قدامي", "اللي قدامي", "الظاهر قدامي", "شوف الشاشة", "ايش مكتوب",
    "الملف المفتوح", "المتصفح المفتوح", "اقرأ الشاشة", "ocr", "ماذا ارى",
]

_BROWSER_KEYWORDS = [
    "متصفح", "المتصفح", "browser", "اكتب في المتصفح", "افتح موقع",
    "سجل في", "املا", "نموذج", "استمارة", "انقر", "اضغط على زر",
    "ادخل على موقع", "playwright", "ابحث في جوجل", "صفحة الويب",
]

# كلمات خاصة بالتحكم بالنظام وفتح التطبيقات — لضمان توجيهها للنموذج الأكثر موثوقية في استدعاء الأدوات
_SYSTEM_CONTROL_KEYWORDS = [
    "افتح", "شغل", "تشغيل", "فتح", "ابدأ", "open", "launch", "start",
    "فوتوشوب", "photoshop", "بريمير", "premiere", "افتر افكت", "after effects",
    "كامتاسيا", "camtasia", "فيجوال ستوديو", "vscode", "code", "بلندر", "blender",
    "المفكرة", "notepad", "الحاسبة", "calculator", "الرسام", "paint",
    "ديسكورد", "discord", "تليجرام", "telegram", "واتساب", "whatsapp",
    "ستيم", "steam", "سبوتيفاي", "spotify", "يوتيوب", "youtube",
    "متصفح", "كروم", "chrome", "brave", "برايف", "اوبرا", "opera",
    "ملف", "مجلد", "folder", "اقفل", "اغلق", "اطفي", "اعيد التشغيل",
    "الصوت", "volume", "اسكت", "كتم", "screenshot", "صورة الشاشة",
    "مدير المهام", "task manager", "الاعدادات", "settings",
    "word", "وورد", "excel", "اكسل", "powerpoint", "باوربوينت",
    "obs", "اوبس", "vlc", "fl studio", "capcut", "كاب كات",
    "figma", "فيجما", "audacity", "davinci", "دافنشي",
]

_LEARNING_KEYWORDS = [
    "تعلم", "اتعلم", "كيف اقدر", "كيف يمكن", "ابحث عن طريقة",
    "ما اعرف", "طريقة عمل", "تعلم ذاتي", "ابحث في النت",
    "حل مشكلة", "كيف اسوي", "تعلم كيف", "ابحثلي في قوقل عن حل",
]

_CREATIVE_KEYWORDS = [
    "اكتب قصة", "اكتب قصيدة", "اكتب رواية", "خيال", "إبداع", "أدب",
    "سيناريو", "حوار", "ابتكر", "فكرة إبداعية", "ابتكار",
]

_DEEP_ANALYSIS_KEYWORDS = [
    "حلل", "تحليل", "compare", "مقارنة", "بحث", "research", "دراسة",
    "ملخص", "summarize", "اشرح بعمق", "ما الفرق", "افضل", "ارشحلي",
    "evaluate", "مزايا وعيوب", "دراسة جدوى",
]

_FAST_CHAT_KEYWORDS = [
    "مرحبا", "كيف حالك", "شو أخبارك", "ايش", "وش", "قوللي", "شو",
    "بسرعة", "سؤال سريع", "ok", "تمام", "شكراً", "thanks", "هلا", "أهلاً",
]

_IMAGE_GEN_KEYWORDS = [
    "ارسم", "رسم", "توليد صورة", "ولد صورة", "اصنع صورة", "صمم صورة",
    "draw", "paint", "generate image", "create image", "ارسم لي", "ارسم صورة",
    "توليد صورة بالذكاء", "ارسم صوره", "صمم لي صورة", "تخيل", "تخيلي", "اتخيل",
    "تخيل لي", "تخيل المشهد", "تخيل أن", "صور لي", "صورة لـ", "بدي صورة",
    "أريد صورة", "اعمل صورة", "رسمة", "وريني صورة", "imagine", "picture of",
    "photo of", "illustration",
]

# أفضل نموذج لكل نوع مهمة (بالأولوية — يأخذ أول متاح)
_ROUTING_MAP: Dict[str, List[str]] = {
    "image_generation": ["gemini", "qwen", "groq", "claude", "openai", "duckai"],
    "coding":           ["qwen", "claude", "gemini", "openai", "groq", "duckai"],
    "vision":           ["gemini", "qwen", "claude", "openai", "groq"],
    "browser_task":     ["gemini", "qwen", "claude", "openai", "groq", "duckai"],
    "learning":         ["qwen", "gemini", "claude", "openai", "groq", "duckai"],
    "arabic_complex":   ["qwen", "gemini", "claude", "groq", "openai", "duckai"],
    "creative":         ["qwen", "gemini", "claude", "openai", "groq", "duckai"],
    "deep_analysis":    ["qwen", "gemini", "claude", "openai", "groq", "duckai"],
    "fast_chat":        ["duckai", "qwen", "gemini", "groq", "claude", "openai"],
    # التحكم بالنظام وفتح التطبيقات: Gemini و Qwen أولاً
    "system_control":   ["gemini", "qwen", "claude", "groq", "openai"],
    "general":          ["qwen", "gemini", "groq", "duckai", "claude", "openai"],
}

_MODEL_LABELS: Dict[str, str] = {
    "groq":   "Groq ⚡ (فائق السرعة)",
    "gemini": "Gemini 💎 (رؤية بصرية وبحث عميق)",
    "claude": "Claude 🎭 (برمجة وهندسة استراتيجية)",
    "openai": "GPT-4o 🧠 (تحليل شامل)",
    "qwen":   "Qwen 🌐 (عربي معقد ورياضيات)",
    "duckai": "DuckAI 🦆 (مجاني بدون مفتاح API)",
}


def _detect_task_type(
    user_text: str,
    has_visual_media: bool,
    has_attachments: bool,
) -> Dict[str, Any]:
    """يحلل نص المستخدم ويصنّف نوع المهمة تلقائياً."""
    if has_visual_media:
        return {"type": "vision", "confidence": 1.0, "reason": "مرفق صورة أو فيديو يتطلب رؤية بصرية"}

    text_lower = user_text.lower()

    # طلبات رسم وتوليد الصور
    if any(kw in text_lower for kw in _IMAGE_GEN_KEYWORDS):
        return {"type": "image_generation", "confidence": 1.0, "reason": "طلب رسم وتوليد صورة بالذكاء الاصطناعي"}

    scores = {
        "coding":           sum(1 for kw in _CODING_KEYWORDS if kw in text_lower),
        "vision":           sum(1 for kw in _VISION_KEYWORDS if kw in text_lower),
        "browser_task":     sum(1 for kw in _BROWSER_KEYWORDS if kw in text_lower),
        "learning":         sum(1 for kw in _LEARNING_KEYWORDS if kw in text_lower),
        "arabic_complex":   sum(1 for kw in _ARABIC_COMPLEX_KEYWORDS if kw in text_lower),
        "creative":         sum(1 for kw in _CREATIVE_KEYWORDS if kw in text_lower),
        "deep_analysis":    sum(1 for kw in _DEEP_ANALYSIS_KEYWORDS if kw in text_lower),
        "fast_chat":        sum(1 for kw in _FAST_CHAT_KEYWORDS if kw in text_lower),
        "system_control":   sum(1 for kw in _SYSTEM_CONTROL_KEYWORDS if kw in text_lower),
    }

    # طول الرسالة مؤشر تعقيد
    msg_len = len(user_text)
    if msg_len > 300:
        scores["deep_analysis"] += 1
    if msg_len < 40 and not any(kw in text_lower for kw in _VISION_KEYWORDS + _CODING_KEYWORDS + _SYSTEM_CONTROL_KEYWORDS):
        scores["fast_chat"] += 1
    if has_attachments:
        scores["deep_analysis"] += 1

    # تعزيز system_control إذا كانت الرسالة قصيرة وتبدأ بكلمة أمر واضحة
    trigger_words = ["افتح", "شغل", "فتح", "تشغيل", "open", "launch", "start", "اغلق", "اقفل", "اطفي"]
    if any(text_lower.strip().startswith(tw) for tw in trigger_words):
        scores["system_control"] += 3

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    if best_score == 0:
        return {"type": "general", "confidence": 0.5, "reason": "محادثة عامة"}

    _reasons = {
        "coding":           "مهمة برمجية وكود تتطلب تفكيراً هندسياً",
        "vision":           "رؤية بصرية وتحليل ما يراه المستخدم على الشاشة",
        "browser_task":     "تنفيذ مهام وكتابة تفاعلية داخل المتصفح",
        "learning":         "تعلم ذاتي استباقي وبحث معمق في الإنترنت",
        "arabic_complex":   "معالجة عربية متعمقة، شعر، أو مسائل رياضية",
        "creative":         "كتابة إبداعية وأدبية وتوليد أفكار",
        "deep_analysis":    "تحليل وبحث ومقارنة تفصيلية",
        "fast_chat":        "محادثة سريعة وإجابة مباشرة",
        "system_control":   "تحكم بالنظام أو فتح تطبيق على الجهاز",
        "general":          "محادثة عامة",
    }

    confidence = min(best_score / 3.0, 1.0)
    return {"type": best_type, "confidence": confidence, "reason": _reasons.get(best_type, "")}


def _pick_provider_for_task(
    task: Dict[str, Any],
    available: Dict[str, Any],
) -> tuple:
    """يختار أفضل نموذج متاح بناءً على نوع المهمة. يرجع (provider_name, routing_reason)."""
    task_type = task["type"]
    reason = task["reason"]
    priority = _ROUTING_MAP.get(task_type, ["groq", "gemini", "claude", "openai", "qwen"])

    for p_name in priority:
        if p_name in available:
            label = _MODEL_LABELS.get(p_name, p_name)
            return p_name, f"تم اختيار {label} تلقائياً — {reason}"

    first = next(iter(available.keys()))
    return first, f"النموذج المتاح: {_MODEL_LABELS.get(first, first)}"


# ─────────────────────────────────────────────────────────────────────────────
class AIOrchestrator:
    MAX_TOOL_ITERATIONS = 5

    def __init__(self):
        self.providers: Dict[str, AIProvider] = {}
        self._init_providers()

    def _init_providers(self):
        # 1. Groq (Ultra-fast LLM & Whisper STT)
        if settings.GROQ_API_KEY:
            try:
                self.providers["groq"] = GroqProvider()
            except Exception as e:
                logger.warning(f"Failed to initialize Groq provider: {e}")

        # 2. Google Gemini (Deep Reasoning & Multimodal Vision)
        if settings.GEMINI_API_KEY:
            try:
                self.providers["gemini"] = GeminiProvider()
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini provider: {e}")

        # 3. Anthropic Claude
        if settings.ANTHROPIC_API_KEY or settings.CLAUDE_API_KEY:
            try:
                self.providers["claude"] = ClaudeProvider()
            except Exception as e:
                logger.warning(f"Failed to initialize Claude provider: {e}")

        # 4. OpenAI (GPT-4o)
        if settings.OPENAI_API_KEY or settings.OPENAI_BASE_URL:
            try:
                self.providers["openai"] = OpenAIProvider()
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI provider: {e}")

        # 5. Qwen (Alibaba DashScope / Qwen)
        try:
            self.providers["qwen"] = QwenProvider()
            logger.info("Qwen (Alibaba) provider registered successfully 🌐")
        except Exception as e:
            logger.warning(f"Failed to initialize Qwen provider: {e}")

        # 6. DuckDuckGo AI (duck.ai) — مجاني بدون مفتاح API
        if settings.DUCKAI_ENABLED:
            try:
                self.providers["duckai"] = DuckAIProvider(
                    model=settings.DUCKAI_MODEL,
                )
                logger.info(f"DuckAI (duck.ai) provider ready — FREE, no API key needed 🦆")
            except Exception as e:
                logger.warning(f"Failed to initialize DuckAI provider: {e}")

    def reload_providers(self):
        """إعادة فحص وتهيئة جميع المزودين ديناميكياً دون إعادة تشغيل"""
        self.providers.clear()
        self._init_providers()
        logger.info(f"AI Providers reloaded: {list(self.providers.keys())}")

    def get_available_providers_info(self) -> Dict[str, Any]:
        """معلومات المزودين وحالة التفعيل للواجهة الأمامية"""
        all_specs = {
            "groq": {
                "name": "Groq (فائق السرعة)",
                "icon": "⚡",
                "model": settings.GROQ_CHAT_MODEL,
                "configured": bool(settings.GROQ_API_KEY),
                "active": "groq" in self.providers,
                "description": "استجابة صاروخية — الأفضل للمحادثة السريعة والأسئلة العامة",
                "best_for": ["محادثة سريعة", "أسئلة عامة"],
            },
            "gemini": {
                "name": "Google Gemini",
                "icon": "💎",
                "model": settings.GEMINI_MODEL,
                "configured": bool(settings.GEMINI_API_KEY),
                "active": "gemini" in self.providers,
                "description": "الأفضل للصور والفيديوهات والتحليل العميق والبحث",
                "best_for": ["صور وفيديو", "تحليل عميق", "بحث"],
            },
            "claude": {
                "name": "Anthropic Claude",
                "icon": "🎭",
                "model": settings.CLAUDE_MODEL,
                "configured": bool(settings.ANTHROPIC_API_KEY or settings.CLAUDE_API_KEY),
                "active": "claude" in self.providers,
                "description": "الأفضل للبرمجة والتفكير المنطقي والكتابة الإبداعية",
                "best_for": ["برمجة وكود", "كتابة إبداعية"],
            },
            "openai": {
                "name": "OpenAI (GPT-4o)",
                "icon": "🧠",
                "model": settings.OPENAI_MODEL,
                "configured": bool(settings.OPENAI_API_KEY),
                "active": "openai" in self.providers,
                "description": "المعيار العالمي مع ذكاء GPT-4o",
                "best_for": ["تحليل", "كود", "محادثة"],
            },
            "qwen": {
                "name": "Qwen (علي بابا)",
                "icon": "🌐",
                "model": settings.QWEN_MODEL,
                "configured": bool(settings.QWEN_API_KEY or settings.GROQ_API_KEY),
                "active": "qwen" in self.providers,
                "description": "الأفضل في اللغة العربية والرياضيات",
                "best_for": ["عربي معقد", "رياضيات", "ترجمة"],
            },
            "duckai": {
                "name": "DuckAI (duck.ai)",
                "icon": "🦆",
                "model": settings.DUCKAI_MODEL,
                "configured": settings.DUCKAI_ENABLED,
                "active": "duckai" in self.providers,
                "description": "مجاني تماماً بدون مفتاح API — GPT-4o-mini, Claude, Llama عبر DuckDuckGo",
                "best_for": ["محادثة مجانية", "أسئلة عامة", "بديل احتياطي"],
            },
        }
        return {
            "default": settings.DEFAULT_AI_PROVIDER,
            "auto_routing": True,
            "providers": all_specs,
            "active_count": len(self.providers),
        }

    def get_provider(self, name: Optional[str] = None) -> AIProvider:
        provider_name = name or settings.DEFAULT_AI_PROVIDER
        if provider_name in self.providers:
            return self.providers[provider_name]

        if self.providers:
            first_avail_name = next(iter(self.providers.keys()))
            logger.warning(f"Provider '{provider_name}' not available. Falling back to '{first_avail_name}'.")
            return self.providers[first_avail_name]

        raise RuntimeError(
            "لم يتم تكوين أي مزود ذكاء اصطناعي. يرجى إضافة مفتاح API لـ Groq أو Gemini أو Claude أو OpenAI أو Qwen، أو تفعيل DuckAI المجاني."
        )

    async def _build_messages(
        self,
        user_text: str,
        chat_history: List[Dict[str, str]],
        memory_facts: Optional[List[Dict[str, Any]]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, str]]:
        """بناء قائمة الرسائل الكاملة للإرسال للنموذج"""
        # جلب أوامر المستخدم الصارمة (لها الأولوية المطلقة) والدروس المستفادة
        manual_rules = []
        other_lessons = []
        try:
            import aiosqlite
            async with aiosqlite.connect(settings.DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                # أوامر المستخدم اليدوية المخصصة
                cursor = await db.execute(
                    "SELECT topic, correction FROM learned_lessons WHERE context = 'manual_rule' ORDER BY id ASC"
                )
                manual_rules = await cursor.fetchall()

                # الدروس والخبرات الأخرى المتعلمة تلقائياً
                cursor2 = await db.execute(
                    "SELECT topic, correction FROM learned_lessons WHERE context != 'manual_rule' OR context IS NULL ORDER BY id DESC LIMIT 8"
                )
                other_lessons = await cursor2.fetchall()
        except Exception as err:
            logger.warning(f"Failed to fetch learned rules: {err}")

        # بناء لافتة الأولوية المطلقة لأوامر المستخدم في أعلى البرومبت
        manual_rules_banner = ""
        if manual_rules:
            rules_lines = "\n".join([f"{i+1}. [أمر ملزم - {r['topic']}]: {r['correction']}" for i, r in enumerate(manual_rules)])
            manual_rules_banner = f"""################################################################################
🔴🔴🔴 أوامر وتوجيهات المستخدم المباشرة (أولوية مطلقة وفوق كل القواعد) 🔴🔴🔴
أنت سمير، والمستخدم حدد بنفسه هذه الأوامر والتوجيهات في "قائمة الأوامر الخاصة بك".
هذه الأوامر لها الأولوية المطلقة والنهائية فوق أي قاعدة أخرى أو شخصية أو إرشادات.
يجب عليك تطبيقها بحذافيرها وتعديل أسلوبك وسلوكك وقواعدك وإجاباتك لتتوافق معها تماماً دون أي نقاش أو تردد:
{rules_lines}
################################################################################

"""

        system_content = manual_rules_banner + SAMIR_SYSTEM_PROMPT

        # حقن الوقت والتاريخ الحي الحالي في جهاز المستخدم
        try:
            import datetime
            now_dt = datetime.datetime.now()
            time_str = now_dt.strftime("%I:%M:%S %p")
            date_str = now_dt.strftime("%Y-%m-%d")
            day_ar = ["الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"][now_dt.weekday()]
            system_content += f"\n\n# التوقيت والتاريخ الحي الحالي في جهاز المستخدم:\n- اليوم: {day_ar}\n- التاريخ: {date_str}\n- الساعة الآن: {time_str}\n"
        except Exception:
            pass

        # إضافة الدروس العامة المتعلمة
        if other_lessons:
            lessons_str = "\n".join([f"- [{l['topic']}]: {l['correction']}" for l in other_lessons])
            system_content += f"\n\n# دروس وخبرات عامة مساعدة:\n{lessons_str}"

        # فحص التعقيد والتوجيه الاستراتيجي
        complexity = strategic_planner.analyze_task_complexity(user_text)
        if complexity["is_complex"]:
            system_content += "\n\n" + strategic_planner.format_strategic_guidance()

        if memory_facts and len(memory_facts) > 0:
            facts_str = "\n".join([f"- {f['key']}: {f['value']}" for f in memory_facts])
            system_content += f"\n\n# ما تتذكره عن المستخدم:\n{facts_str}"

        if manual_rules:
            system_content += "\n\n⚠️ تذكير حاسم: أوامر المستخدم الصارمة المذكورة في البداية لها الأولوية القصوى والمطلقة دائماً فوق أي شيء آخر."

        messages = [{"role": "system", "content": system_content}]

        for msg in chat_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

        full_user_content = user_text
        multimodal_parts = []
        has_media = False

        if attachments and len(attachments) > 0:
            att_blocks = []
            for att in attachments:
                orig_name = att.get("original_filename") or att.get("stored_filename", "ملف")
                cat = att.get("category", "file")
                summary = att.get("summary", "")
                text_snippet = att.get("extracted_text", "")
                url = att.get("url", "")

                block = f"📎 [المرفق: {orig_name} | النوع: {cat} | الرابط: {url}]\n- الوصف: {summary}"
                if text_snippet:
                    block += f"\n--- محتوى الملف ({orig_name}) ---\n{text_snippet}\n--- نهاية ---"
                att_blocks.append(block)

                b64 = att.get("base64") or att.get("content") or att.get("data")
                is_img = att.get("is_image") or (str(att.get("mime_type", "")).startswith("image/")) or (str(orig_name).lower().endswith((".jpg", ".jpeg", ".png", ".webp")))
                is_vid = att.get("is_video") or (str(att.get("mime_type", "")).startswith("video/"))
                if b64 and (is_img or is_vid or cat == "document"):
                    has_media = True
                    mime = att.get("mime_type") or ("image/jpeg" if is_img else "video/mp4")
                    multimodal_parts.append({
                        "inlineData": {
                            "mimeType": mime,
                            "data": b64
                        }
                    })

            full_user_content = "\n\n".join(att_blocks) + f"\n\nرسالة المستخدم:\n{user_text}"

        user_msg = {"role": "user", "content": full_user_content}
        if has_media and multimodal_parts:
            multimodal_parts.append({"text": full_user_content})
            user_msg["parts"] = multimodal_parts

        messages.append(user_msg)
        return messages

    async def process_user_input(
        self,
        user_text: str,
        chat_history: List[Dict[str, str]],
        memory_facts: Optional[List[Dict[str, Any]]] = None,
        available_tools: Optional[List[Dict[str, Any]]] = None,
        provider_name: Optional[str] = None,
        session_id: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        معالجة مدخل المستخدم عبر Agentic Loop الكامل.
        يختار النموذج تلقائياً بناءً على تحليل طبيعة الطلب (Smart Auto-Routing).
        يدعم الرؤية الحاسوبية للصور والفيديوهات (Multimodal Vision).
        """
        from app.tools.base_tool import tool_registry
        from app.core.activity_log import activity_logger

        if available_tools is None:
            if not tool_registry.get_core_tool_schemas():
                import app.tools.default_tools
                import app.tools.windows_agent_tool
                import app.tools.browser_media_tool
                import app.tools.web_search_tool
                import app.tools.browser_automation_tool
            available_tools = tool_registry.get_core_tool_schemas()

        # ── 1. فحص طلب رؤية الشاشة الحية (Live Screen Vision Auto-Capture) ───
        screen_triggers = [
            "شوف الصفحة", "شوف الشاشة", "ترجم لي اللي قدامي", "ترجملي اللي قدامي",
            "ترجم اللي في الشاشة", "ترجم الصفحة", "ايش مكتوب في الشاشة",
            "ايش شايف في الشاشة", "اقرأ الشاشة", "اقرا الشاشة", "شوف اللي قدامي",
            "انظر للشاشة", "انظر للصفحة", "شاهد الشاشة"
        ]
        is_screen_vision = any(trig in user_text for trig in screen_triggers)
        if is_screen_vision:
            try:
                from app.tools.windows_agent_tool import tool_take_screenshot
                logger.info("Screen vision trigger detected — capturing live desktop screenshot...")
                sc_res = await tool_take_screenshot()
                if sc_res.get("status") == "success" and sc_res.get("image_base64"):
                    if attachments is None:
                        attachments = []
                    attachments.append({
                        "original_filename": "live_desktop_screen.png",
                        "stored_filename": "live_desktop_screen.png",
                        "category": "image",
                        "is_image": True,
                        "mime_type": "image/png",
                        "base64": sc_res["image_base64"],
                        "summary": "لقطة شاشة حية وفورية لشاشة حاسوب المستخدم الآن مع الصفحة المفتوحة أمامه.",
                    })
                    if "gemini" in self.providers:
                        provider_name = "gemini"
                    elif "claude" in self.providers:
                        provider_name = "claude"
                    elif "openai" in self.providers:
                        provider_name = "openai"
            except Exception as sc_err:
                logger.warning(f"Failed to auto-capture screen: {sc_err}")

        # ── 2. فحص وجود روابط إنستغرام أو يوتيوب أو مواقع ويب ────────────────
        import re
        url_matches = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', user_text)
        if url_matches:
            try:
                from app.tools.link_inspector_tool import tool_inspect_url
                for u in url_matches[:2]:
                    logger.info(f"Auto-inspecting URL in user text: {u}")
                    link_info = await tool_inspect_url(u)
                    if link_info.get("status") == "success":
                        if attachments is None:
                            attachments = []
                        attachments.append({
                            "original_filename": link_info.get("title", u),
                            "category": "link",
                            "summary": link_info.get("message", ""),
                            "extracted_text": link_info.get("caption") or link_info.get("content_preview") or link_info.get("description", ""),
                            "url": u,
                        })
            except Exception as link_err:
                logger.warning(f"Failed to pre-inspect URL: {link_err}")

        has_visual_media = bool(
            attachments and any(att.get("is_image") or att.get("is_video") for att in attachments)
        )

        # ── الاختيار الذكي التلقائي للنموذج ──────────────────────────────
        routing_reason = ""
        if provider_name and provider_name != "auto" and provider_name in self.providers:
            # المستخدم حدد نموذجاً يدوياً عبر الـ API — نحترم اختياره
            provider = self.providers[provider_name]
            routing_reason = f"تحديد يدوي: {_MODEL_LABELS.get(provider_name, provider_name)}"
            logger.info(f"Manual provider override: {provider_name}")
        else:
            task_info = _detect_task_type(
                user_text=user_text,
                has_visual_media=has_visual_media,
                has_attachments=bool(attachments),
            )
            auto_provider_name, routing_reason = _pick_provider_for_task(task_info, self.providers)
            provider = self.providers.get(auto_provider_name) or self.get_provider()
            logger.info(
                f"Auto-routing → {auto_provider_name} | type={task_info['type']} "
                f"| conf={task_info['confidence']:.2f} | {routing_reason}"
            )

        messages = await self._build_messages(user_text, chat_history, memory_facts, attachments=attachments)

        all_tool_calls_executed = []
        needs_confirmation: Optional[Dict] = None
        reply_text = ""
        response: Dict[str, Any] = {}

        for iteration in range(self.MAX_TOOL_ITERATIONS):
            logger.info(
                f"Orchestrator iteration {iteration + 1}/{self.MAX_TOOL_ITERATIONS} "
                f"using {provider.__class__.__name__}"
            )

            try:
                response = await provider.generate_response(
                    messages=messages,
                    tools=available_tools if not has_visual_media else None,
                    temperature=0.6,
                )
            except Exception as e:
                err_msg = str(e)
                logger.warning(f"Provider {provider.__class__.__name__} failed: {err_msg}")

                # إذا فشلت رؤية الوسائط بسبب مفتاح غير صالح
                if has_visual_media and any(
                    code in err_msg for code in ["INVALID_ARGUMENT", "API key not valid", "400", "not configured"]
                ):
                    img_att = next(
                        (a for a in attachments if a.get("is_image") or a.get("is_video")), attachments[0]
                    )
                    fname = img_att.get("original_filename", "الملف")
                    dims = img_att.get("dimensions", "غير محدد")
                    sz = img_att.get("size_kb", "")
                    friendly_reply = (
                        f"يا غالي، استلمت {fname} وحللت بياناتها الأولية.\n"
                        f"• الأبعاد: {dims} | الحجم: {sz} KB\n\n"
                        f"عشان أشوف الصورة/الفيديو بعمق، أضف مفتاح API من الإعدادات 🔑"
                    )
                    return {
                        "content": friendly_reply,
                        "tool_calls": [],
                        "provider": "samir_local_vision",
                        "model": "local_pre_analyzer",
                        "routing_reason": routing_reason,
                    }

                # Fallback للنماذج البديلة
                fallback_candidates = [
                    p_name for p_name in ["groq", "gemini", "claude", "openai", "qwen"]
                    if p_name in self.providers and self.providers[p_name] != provider
                ]
                fallback_success = False
                for fb_name in fallback_candidates:
                    try:
                        logger.info(f"Switching to fallback provider: {fb_name}")
                        provider = self.providers[fb_name]
                        response = await provider.generate_response(
                            messages=messages,
                            tools=available_tools,
                            temperature=0.6,
                        )
                        routing_reason += f" ← تحويل طارئ لـ {_MODEL_LABELS.get(fb_name, fb_name)}"
                        fallback_success = True
                        break
                    except Exception as fb_err:
                        logger.warning(f"Fallback to {fb_name} failed: {fb_err}")

                if not fallback_success:
                    if all_tool_calls_executed:
                        last_exec = all_tool_calls_executed[-1]
                        res_msg = last_exec.get("result", {}).get("message", "")
                        return {
                            "content": res_msg or "تفضل يا غالي، تم تنفيذ طلبك على الجهاز بنجاح! 🚀",
                            "tool_calls": all_tool_calls_executed,
                            "provider": getattr(provider, "provider_name", "samir"),
                            "model": getattr(provider, "model", "default"),
                            "routing_reason": routing_reason,
                        }
                    raise e

            tool_calls = response.get("tool_calls", [])
            reply_text = response.get("content", "")

            if not tool_calls:
                logger.info("No tool calls — returning final response.")
                break

            tool_results_for_model = []

            for tc in tool_calls:
                tool_name = tc["name"]
                tool_args = tc.get("arguments", {})
                tool_id = tc.get("id", tool_name)

                result = await tool_registry.execute_tool(tool_name, tool_args)
                all_tool_calls_executed.append({
                    "name": tool_name,
                    "arguments": tool_args,
                    "result": result,
                })

                # التحقق الاستراتيجي وإرشاد التصحيح الذاتي
                v_res = strategic_planner.verify_tool_result(tool_name, tool_args, result)
                if not v_res["verified"]:
                    result["_self_correction_guidance"] = v_res["suggestion"]

                await activity_logger.log_tool_execution(
                    tool_name=tool_name,
                    arguments=tool_args,
                    result=result,
                    session_id=session_id,
                )

                if result.get("status") == "needs_confirmation":
                    needs_confirmation = result

                # تنظيف سلاسل base64 الكبيرة للصور لكي لا تفجر سياق الرموز (Tokens)
                clean_result = dict(result) if isinstance(result, dict) else result
                b64_img_captured = None
                if isinstance(clean_result, dict) and "image_base64" in clean_result:
                    b64_img_captured = clean_result.get("image_base64")
                    clean_result = {k: v for k, v in clean_result.items() if k != "image_base64"}
                    clean_result["_image_captured"] = True

                tool_results_for_model.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": json.dumps(clean_result, ensure_ascii=False),
                })

                if b64_img_captured and "gemini" in self.providers:
                    tool_results_for_model.append({
                        "role": "user",
                        "parts": [
                            {"text": f"هذه لقطة الشاشة المباشرة التي تم التقاطها عبر {tool_name}. تفضل بالاطلاع عليها وترجمة وقراءة ما يظهر فيها بدقة:"},
                            {"inlineData": {"mimeType": "image/png", "data": b64_img_captured}}
                        ],
                        "content": "[لقطة شاشة مرفقة للتحليل]"
                    })

            assistant_msg: Dict[str, Any] = {"role": "assistant", "content": reply_text or ""}
            raw_tool_calls = [
                {
                    "id": tc.get("id", tc["name"]),
                    "type": "function",
                    "thought_signature": tc.get("thought_signature"),
                    "function": {
                        "name": tc["name"],
                        "arguments": json.dumps(tc.get("arguments", {}), ensure_ascii=False),
                        "thought_signature": tc.get("thought_signature"),
                    },
                }
                for tc in tool_calls
            ]
            if raw_tool_calls:
                assistant_msg["tool_calls"] = raw_tool_calls

            messages.append(assistant_msg)
            messages.extend(tool_results_for_model)

            if needs_confirmation:
                final_resp = await provider.generate_response(
                    messages=messages,
                    tools=None,
                    temperature=0.5,
                )
                return {
                    "content": final_resp.get("content", needs_confirmation["message"]),
                    "tool_calls": all_tool_calls_executed,
                    "needs_confirmation": needs_confirmation,
                    "provider": response.get("provider", "unknown"),
                    "model": response.get("model", "unknown"),
                    "routing_reason": routing_reason,
                }

        # صمام أمان لطلبات الرسم والتخيل: إذا كان الطلب رسماً وتخيلاً ولم يستدعِ النموذج الأداة برمجياً
        if task_info.get("type") == "image_generation" and not any(
            tc.get("name") in ["generate_image", "generate_ai_image", "imagine_image"]
            for tc in all_tool_calls_executed
        ):
            logger.info("Image generation task detected but model did not call tool — auto-executing generate_image...")
            try:
                from app.tools.image_generation_tool import tool_generate_image
                import re
                clean_prompt = user_text
                for kw in [
                    "ارسم لي صوره", "ارسم لي صورة", "ارسم لي", "ارسم صوره", "ارسم صورة", "ارسم",
                    "تخيل لي", "تخيل المشهد", "تخيل أن", "تخيل", "صور لي", "صورة لـ", "بدي صورة",
                    "أريد صورة", "اعمل صورة", "رسمة", "وريني صورة", "imagine"
                ]:
                    clean_prompt = clean_prompt.replace(kw, "").strip()
                clean_prompt = clean_prompt or user_text
                img_res = await tool_generate_image(prompt=clean_prompt)
                all_tool_calls_executed.append({
                    "name": "generate_image",
                    "arguments": {"prompt": clean_prompt},
                    "result": img_res,
                })
                img_url = img_res.get("image_url") or img_res.get("direct_url")
                if img_url:
                    # تنظيف أي روابط صور وهمية قد يكون النموذج كتبها من تلقاء نفسه
                    reply_text = re.sub(r'!\[.*?\]\(/static/generated/.*?\)', '', reply_text).strip()
                    reply_text = re.sub(r'/static/generated/samir_art_\d+\.(?:jpg|png)', '', reply_text).strip()
                    reply_text += f"\n\n![{clean_prompt}]({img_url})"
            except Exception as auto_img_err:
                logger.error(f"Auto-executing generate_image failed: {auto_img_err}")

        if not reply_text and all_tool_calls_executed:
            last_exec = all_tool_calls_executed[-1]
            reply_text = last_exec.get("result", {}).get("message", "تفضل يا غالي، تم تنفيذ طلبك بنجاح! 🚀")

        return {
            "content": reply_text or "حاضر، تم التنفيذ.",
            "tool_calls": all_tool_calls_executed,
            "provider": response.get("provider", "unknown"),
            "model": response.get("model", "unknown"),
            "routing_reason": routing_reason,
        }


orchestrator = AIOrchestrator()
