import io
import re
import logging
import httpx
import edge_tts
from typing import Optional, AsyncGenerator, Dict, Any, List
from app.core.config import settings

logger = logging.getLogger("samir.voice.tts")

# ─── مكتبة أصوات سمير المتاحة: أصوات عربية فصيحة مجانية 100% بدون أي كريدت + أصوات ElevenLabs ───
AVAILABLE_VOICES: Dict[str, Dict[str, Any]] = {
    "ar-SA-HamedNeural": {
        "id": "ar-SA-HamedNeural",
        "name": "حامد — Hamed (فخم وفصيح - مجاني 100%)",
        "language": "عربي فصيح",
        "gender": "male",
        "accent": "سعودي / فصيح عميق وواثق",
        "flag": "🇸🇦",
        "description": "صوت عربي رسمي فخم، طبيعي وواضح جداً — مجاني 100% بدون استهلاك أي كريدت إطلاقاً",
        "is_default": True,
        "is_free": True
    },
    "ar-SA-ZariyahNeural": {
        "id": "ar-SA-ZariyahNeural",
        "name": "زارية — Zariyah (ناعمة وهادئة - مجانية 100%)",
        "language": "عربي فصيح",
        "gender": "female",
        "accent": "عربي فصيح ناعم ومريح",
        "flag": "🎙️",
        "description": "صوت نسائي عربي فصيح وناعم للأذن — مجاني 100% بدون استهلاك أي كريدت",
        "is_default": False,
        "is_free": True
    },
    "ar-EG-ShakirNeural": {
        "id": "ar-EG-ShakirNeural",
        "name": "شاكر — Shakir (مصري ذكي - مجاني 100%)",
        "language": "عربي مصري / فصيح",
        "gender": "male",
        "accent": "مصري دافئ وحيوي",
        "flag": "🇪🇬",
        "description": "صوت عربي دافئ وسريع التفاعل — مجاني 100% بدون استهلاك أي كريدت",
        "is_default": False,
        "is_free": True
    },
    "ar-EG-SalmaNeural": {
        "id": "ar-EG-SalmaNeural",
        "name": "سلمى — Salma (مصرية مشرقة - مجانية 100%)",
        "language": "عربي مصري / فصيح",
        "gender": "female",
        "accent": "مصري مشرق وواضح",
        "flag": "🇪🇬",
        "description": "صوت نسائي مصري مشرق وعالي الوضوح — مجاني 100% بدون استهلاك أي كريدت",
        "is_default": False,
        "is_free": True
    },
    "ar-AE-HamdanNeural": {
        "id": "ar-AE-HamdanNeural",
        "name": "حمدان — Hamdan (إماراتي وقور - مجاني 100%)",
        "language": "عربي فصيح / خليجي",
        "gender": "male",
        "accent": "إماراتي وقور وفخم",
        "flag": "🇦🇪",
        "description": "صوت رجالي إماراتي فخم ووقور كالمعلقين الرسميين — مجاني 100%",
        "is_default": False,
        "is_free": True
    },
    "ar-AE-FatimaNeural": {
        "id": "ar-AE-FatimaNeural",
        "name": "فاطمة — Fatima (إماراتية راقية - مجانية 100%)",
        "language": "عربي فصيح / خليجي",
        "gender": "female",
        "accent": "إماراتي راقٍ وهادئ",
        "flag": "🇦🇪",
        "description": "صوت نسائي خليجي هادئ وراقٍ ومريح للأذن — مجاني 100%",
        "is_default": False,
        "is_free": True
    },
    "ar-LB-RamiNeural": {
        "id": "ar-LB-RamiNeural",
        "name": "رامي — Rami (لبناني شاب - مجاني 100%)",
        "language": "عربي شامي / فصيح",
        "gender": "male",
        "accent": "لبناني شبابي وتقني",
        "flag": "🇱🇧",
        "description": "صوت شبابي عصري وسريع ومتقن — مجاني 100%",
        "is_default": False,
        "is_free": True
    },
    "ar-LB-LaylaNeural": {
        "id": "ar-LB-LaylaNeural",
        "name": "ليلى — Layla (لبنانية ناعمة - مجانية 100%)",
        "language": "عربي شامي / فصيح",
        "gender": "female",
        "accent": "لبناني ناعم ومريح",
        "flag": "🇱🇧",
        "description": "صوت نسائي شامي ناعم ومريح للأذن في السرد والشرح — مجاني 100%",
        "is_default": False,
        "is_free": True
    },
    "ar-JO-TaimNeural": {
        "id": "ar-JO-TaimNeural",
        "name": "تيم — Taim (أردني واثق - مجاني 100%)",
        "language": "عربي شامي / فصيح",
        "gender": "male",
        "accent": "أردني واثق ومتحمس",
        "flag": "🇯🇴",
        "description": "صوت رجالي نشيط وحماسي ومتحدث بارع — مجاني 100%",
        "is_default": False,
        "is_free": True
    },
    "ar-JO-SanaNeural": {
        "id": "ar-JO-SanaNeural",
        "name": "سناء — Sana (أردنية وقورة - مجانية 100%)",
        "language": "عربي شامي / فصيح",
        "gender": "female",
        "accent": "أردني إخباري وقور",
        "flag": "🇯🇴",
        "description": "صوت نسائي إخباري وقور ومخارج حروف واضحة — مجاني 100%",
        "is_default": False,
        "is_free": True
    },
    "ar-MA-JamalNeural": {
        "id": "ar-MA-JamalNeural",
        "name": "جمال — Jamal (مغربي فصيح - مجاني 100%)",
        "language": "عربي مغربي / فصيح",
        "gender": "male",
        "accent": "مغربي هادئ وفصيح",
        "flag": "🇲🇦",
        "description": "صوت رجالي مغربي هادئ ومتقن للنصوص الطويلة — مجاني 100%",
        "is_default": False,
        "is_free": True
    },
    "ar-IQ-BasselNeural": {
        "id": "ar-IQ-BasselNeural",
        "name": "باسل — Bassel (عراقي عميق - مجاني 100%)",
        "language": "عربي عراقي / فصيح",
        "gender": "male",
        "accent": "عراقي عميق وفخم",
        "flag": "🇮🇶",
        "description": "صوت رجالي عميق ووثائقي ذو هيبة — مجاني 100%",
        "is_default": False,
        "is_free": True
    },
    "pNInz6obpgDQGcFmaJgB": {
        "id": "pNInz6obpgDQGcFmaJgB",
        "name": "Adam — آدم (ElevenLabs)",
        "language": "عربي / English",
        "gender": "male",
        "accent": "أمريكي / عربي دافئ وواثق",
        "flag": "🎙️",
        "description": "صوت رجالي عميق ودافئ (يتطلب مفتاح ElevenLabs sk_ صالح ورصيد)",
        "is_default": False,
        "is_free": False
    },
    "EXAVITQu4vr4xnSDxMaL": {
        "id": "EXAVITQu4vr4xnSDxMaL",
        "name": "Sarah — سارة (واثقة ومريحة)",
        "language": "عربي / English",
        "gender": "female",
        "accent": "طبيعي، ناضج ومريح",
        "flag": "🎙️",
        "description": "صوت نسائي ناضج، واثق ومريح للأذن، مخارج حروف واضحة جداً",
        "is_default": False
    },
    "nPczCjzI2devNBz1zQrb": {
        "id": "nPczCjzI2devNBz1zQrb",
        "name": "Brian — برايان (فخم وإخباري)",
        "language": "عربي / English",
        "gender": "male",
        "accent": "فخم، وقور ووثائقي",
        "flag": "🎙️",
        "description": "صوت رجالي عميق وفخم كالمعلقين الوثائقيين ومذيعي الأخبار المحترفين",
        "is_default": False
    },
    "hpp4J3VqNfWAUOO0d1Us": {
        "id": "hpp4J3VqNfWAUOO0d1Us",
        "name": "Bella — بيلا (ناعمة ومشرقة)",
        "language": "عربي / English",
        "gender": "female",
        "accent": "رقيق، لطيف وودود",
        "flag": "🎙️",
        "description": "صوت نسائي ناعم ومشرق، نبرة عذبة ولطيفة جداً في الكلام والتفاعل",
        "is_default": False
    },
    "Xb7hH8MSUJpSbSDYk0k2": {
        "id": "Xb7hH8MSUJpSbSDYk0k2",
        "name": "Alice — أليس (بريطانية واضحة)",
        "language": "عربي / English (UK)",
        "gender": "female",
        "accent": "بريطاني، واضح وجذاب",
        "flag": "🇬🇧",
        "description": "صوت نسائي بريطاني واضح ومثقف، ممتاز للشرح والتعليم",
        "is_default": False
    },
    "JBFqnCBsd6RMkjVDRZzb": {
        "id": "JBFqnCBsd6RMkjVDRZzb",
        "name": "George — جورج (بريطاني دافئ)",
        "language": "عربي / English (UK)",
        "gender": "male",
        "accent": "بريطاني كلاسيكي ودافئ",
        "flag": "🇬🇧",
        "description": "صوت رجالي بريطاني كلاسيكي دافئ ووقور، نبرة راقية ومميزة",
        "is_default": False
    },
    "onwK4e9ZLuTAKqWW03F9": {
        "id": "onwK4e9ZLuTAKqWW03F9",
        "name": "Daniel — دانيال (بريطاني رسمي)",
        "language": "عربي / English (UK)",
        "gender": "male",
        "accent": "بريطاني رسمي وقوي",
        "flag": "🇬🇧",
        "description": "صوت بريطاني وقور ورسمي، نبرة إخبارية حازمة ومتقنة",
        "is_default": False
    },
    "pFZP5JQG7iQjIQuC4Bku": {
        "id": "pFZP5JQG7iQjIQuC4Bku",
        "name": "Lily — ليلي (مخملي هادئ)",
        "language": "عربي / English (UK)",
        "gender": "female",
        "accent": "مخملي، هادئ ومريح",
        "flag": "🇬🇧",
        "description": "صوت نسائي بريطاني مخملي وهادئ، مثالي للقراءة والتفكير الهادئ",
        "is_default": False
    },
    "TX3LPaxmHKxFdv7VOQHJ": {
        "id": "TX3LPaxmHKxFdv7VOQHJ",
        "name": "Liam — ليام (عصري وسريع)",
        "language": "عربي / English",
        "gender": "male",
        "accent": "عصري، تقني وسريع",
        "flag": "🎙️",
        "description": "صوت شبابي عصري وسريع، تفاعل تقني وحيوي عالي",
        "is_default": False
    },
    "IKne3meq5aSn9XLyUdCD": {
        "id": "IKne3meq5aSn9XLyUdCD",
        "name": "Charlie — تشارلي (كاريزمي وواضح)",
        "language": "عربي / English (AU)",
        "gender": "male",
        "accent": "كاريزمي، عميق وواضح",
        "flag": "🎙️",
        "description": "صوت رجالي كاريزمي وواضح، ممتاز للنقاشات الذكية والمشاريع",
        "is_default": False
    },
    "cgSgspJ2msm6clMCkdW9": {
        "id": "cgSgspJ2msm6clMCkdW9",
        "name": "Jessica — جيسيكا (مرحة وحيوية)",
        "language": "عربي / English",
        "gender": "female",
        "accent": "مرح، مشرق ودافئ",
        "flag": "🎙️",
        "description": "صوت نسائي مرح ومشرق ومفعم بالحياة والتفاؤل",
        "is_default": False
    },
    "cjVigY5qzO86Huf0OWal": {
        "id": "cjVigY5qzO86Huf0OWal",
        "name": "Eric — إريك (سلس وواثق)",
        "language": "عربي / English",
        "gender": "male",
        "accent": "سلس، جدير بالثقة",
        "flag": "🎙️",
        "description": "صوت رجالي سلس ومريح، يعطي إحساساً بالأمان والاحتراف",
        "is_default": False
    },
    "iP95p4xoKVk53GoZ742B": {
        "id": "iP95p4xoKVk53GoZ742B",
        "name": "Chris — كريس (جذاب وعفوي)",
        "language": "عربي / English",
        "gender": "male",
        "accent": "جذاب، عفوي وودود",
        "flag": "🎙️",
        "description": "صوت رجالي لطيف وجذاب كصديق يتحدث معك بعفوية",
        "is_default": False
    },
    "bIHbv24MWmeRgasZH58o": {
        "id": "bIHbv24MWmeRgasZH58o",
        "name": "Will — ويل (هادئ ومتفائل)",
        "language": "عربي / English",
        "gender": "male",
        "accent": "هادئ، متفائل ومريح",
        "flag": "🎙️",
        "description": "صوت رجالي متفائل ومريح للأعصاب",
        "is_default": False
    },
    "XrExE9yKIg1WjnnlVkGX": {
        "id": "XrExE9yKIg1WjnnlVkGX",
        "name": "Matilda — ماتيلدا (ذكية ومحترفة)",
        "language": "عربي / English",
        "gender": "female",
        "accent": "محترفة، متزنة وذكية",
        "flag": "🎙️",
        "description": "صوت نسائي ذكي واحترافي، ممتاز للبحث والعمل",
        "is_default": False
    },
    "CwhRBWXzGAHq8TQ4Fs17": {
        "id": "CwhRBWXzGAHq8TQ4Fs17",
        "name": "Roger — روجر (كلاسيكي ورنان)",
        "language": "عربي / English",
        "gender": "male",
        "accent": "كلاسيكي، هادئ ورنان",
        "flag": "🎙️",
        "description": "صوت رجالي متمكن وواثق بنبرة رنانة هادئة",
        "is_default": False
    },
    "FGY2WhTYpPnrIDTdsKH5": {
        "id": "FGY2WhTYpPnrIDTdsKH5",
        "name": "Laura — لورا (حيوية ومعبرة)",
        "language": "عربي / English",
        "gender": "female",
        "accent": "حماسية، معبرة ومرحة",
        "flag": "🎙️",
        "description": "صوت نسائي حماسي ومعبر جداً في التفاعل",
        "is_default": False
    },
    "pqHfZKP75CvOlQylNhV4": {
        "id": "pqHfZKP75CvOlQylNhV4",
        "name": "Bill — بيل (حكيم ومتزن)",
        "language": "عربي / English",
        "gender": "male",
        "accent": "حكيم، ناضج ومتزن",
        "flag": "🎙️",
        "description": "صوت رجالي حكيم وناضج كالمستشار الموثوق",
        "is_default": False
    }
}

DEFAULT_VOICE_ID = "ar-SA-HamedNeural"

VOICE_ALIASES: Dict[str, str] = {
    # الأصوات العربية الفصيحة المجانية 100% (بدون أي استهلاك للكريدت)
    "حامد": "ar-SA-HamedNeural",
    "hamed": "ar-SA-HamedNeural",
    "زارية": "ar-SA-ZariyahNeural",
    "زاريه": "ar-SA-ZariyahNeural",
    "zariyah": "ar-SA-ZariyahNeural",
    "شاكر": "ar-EG-ShakirNeural",
    "shakir": "ar-EG-ShakirNeural",
    "مجاني": "ar-SA-HamedNeural",
    "فصيح": "ar-SA-HamedNeural",

    # آدم / Adam (ElevenLabs)
    "آدم": "pNInz6obpgDQGcFmaJgB",
    "ادم": "pNInz6obpgDQGcFmaJgB",
    "adam": "pNInz6obpgDQGcFmaJgB",
    # سارة / Sarah
    "سارة": "EXAVITQu4vr4xnSDxMaL",
    "ساره": "EXAVITQu4vr4xnSDxMaL",
    "sarah": "EXAVITQu4vr4xnSDxMaL",
    # ريتشل / Rachel -> Sarah
    "ريتشل": "EXAVITQu4vr4xnSDxMaL",
    "راشيل": "EXAVITQu4vr4xnSDxMaL",
    "rachel": "EXAVITQu4vr4xnSDxMaL",
    # برايان / Brian
    "برايان": "nPczCjzI2devNBz1zQrb",
    "بريان": "nPczCjzI2devNBz1zQrb",
    "brian": "nPczCjzI2devNBz1zQrb",
    # بيلا / Bella
    "بيلا": "hpp4J3VqNfWAUOO0d1Us",
    "bella": "hpp4J3VqNfWAUOO0d1Us",
    # أليس / Alice
    "أليس": "Xb7hH8MSUJpSbSDYk0k2",
    "اليس": "Xb7hH8MSUJpSbSDYk0k2",
    "alice": "Xb7hH8MSUJpSbSDYk0k2",
    # جورج / George
    "جورج": "JBFqnCBsd6RMkjVDRZzb",
    "george": "JBFqnCBsd6RMkjVDRZzb",
    # دانيال / Daniel
    "دانيال": "onwK4e9ZLuTAKqWW03F9",
    "daniel": "onwK4e9ZLuTAKqWW03F9",
    # ليلي / Lily
    "ليلي": "pFZP5JQG7iQjIQuC4Bku",
    "lily": "pFZP5JQG7iQjIQuC4Bku",
    # ليام / Liam
    "ليام": "TX3LPaxmHKxFdv7VOQHJ",
    "liam": "TX3LPaxmHKxFdv7VOQHJ",
    # تشارلي / Charlie
    "تشارلي": "IKne3meq5aSn9XLyUdCD",
    "charlie": "IKne3meq5aSn9XLyUdCD",
    # جيسيكا / Jessica
    "جيسيكا": "cgSgspJ2msm6clMCkdW9",
    "jessica": "cgSgspJ2msm6clMCkdW9",
    # إريك / Eric
    "إريك": "cjVigY5qzO86Huf0OWal",
    "اريك": "cjVigY5qzO86Huf0OWal",
    "eric": "cjVigY5qzO86Huf0OWal",
    # كريس / Chris
    "كريس": "iP95p4xoKVk53GoZ742B",
    "chris": "iP95p4xoKVk53GoZ742B",
    # ويل / Will
    "ويل": "bIHbv24MWmeRgasZH58o",
    "will": "bIHbv24MWmeRgasZH58o",
    # ماتيلدا / Matilda
    "ماتيلدا": "XrExE9yKIg1WjnnlVkGX",
    "matilda": "XrExE9yKIg1WjnnlVkGX",
    # روجر / Roger
    "روجر": "CwhRBWXzGAHq8TQ4Fs17",
    "roger": "CwhRBWXzGAHq8TQ4Fs17",
    # لورا / Laura
    "لورا": "FGY2WhTYpPnrIDTdsKH5",
    "laura": "FGY2WhTYpPnrIDTdsKH5",
    # بيل / Bill
    "بيل": "pqHfZKP75CvOlQylNhV4",
    "bill": "pqHfZKP75CvOlQylNhV4",
    # أوصاف عامة ولغات
    "عربي": "ar-SA-HamedNeural",
    "عربية": "ar-SA-ZariyahNeural",
    "arabic": "ar-SA-HamedNeural",
    "إنجليزي": "JBFqnCBsd6RMkjVDRZzb",
    "انجليزي": "JBFqnCBsd6RMkjVDRZzb",
    "english": "JBFqnCBsd6RMkjVDRZzb",
    "رجل": "ar-SA-HamedNeural",
    "رجالي": "ar-SA-HamedNeural",
    "male": "ar-SA-HamedNeural",
    "بنت": "ar-SA-ZariyahNeural",
    "أنثى": "ar-SA-ZariyahNeural",
    "انثى": "ar-SA-ZariyahNeural",
    "نسائي": "ar-SA-ZariyahNeural",
    "female": "ar-SA-ZariyahNeural",

    # الأسماء الجديدة للأصوات المجانية
    "سلمى": "ar-EG-SalmaNeural",
    "حمدان": "ar-AE-HamdanNeural",
    "فاطمة": "ar-AE-FatimaNeural",
    "فاطمه": "ar-AE-FatimaNeural",
    "رامي": "ar-LB-RamiNeural",
    "ليلى": "ar-LB-LaylaNeural",
    "تيم": "ar-JO-TaimNeural",
    "سناء": "ar-JO-SanaNeural",
    "جمال": "ar-MA-JamalNeural",
    "باسل": "ar-IQ-BasselNeural",
}

# ─── خريطة التبديل الذكي: عند نفاد رصيد ElevenLabs، يتم تحويل كل صوت لصوت عصبي مجاني مميز مختلف تماماً ───
ELEVENLABS_FALLBACK_MAP: Dict[str, str] = {
    "pNInz6obpgDQGcFmaJgB": "ar-SA-HamedNeural",      # Adam -> Hamed (سعودي فخم وواثق)
    "EXAVITQu4vr4xnSDxMaL": "ar-SA-ZariyahNeural",    # Sarah -> Zariyah (سعودية ناعمة)
    "nPczCjzI2devNBz1zQrb": "ar-AE-HamdanNeural",     # Brian -> Hamdan (إماراتي وقور ورسمي)
    "hpp4J3VqNfWAUOO0d1Us": "ar-LB-LaylaNeural",      # Bella -> Layla (لبنانية ناعمة ولطيفة)
    "Xb7hH8MSUJpSbSDYk0k2": "ar-EG-SalmaNeural",      # Alice -> Salma (مصرية ذكية ومشرقة)
    "JBFqnCBsd6RMkjVDRZzb": "ar-MA-JamalNeural",      # George -> Jamal (مغربي هادئ ومتقن)
    "onwK4e9ZLuTAKqWW03F9": "ar-IQ-BasselNeural",     # Daniel -> Bassel (عراقي عميق وثائقي)
    "pFZP5JQG7iQjIQuC4Bku": "ar-AE-FatimaNeural",     # Lily -> Fatima (إماراتية راقية وهادئة)
    "TX3LPaxmHKxFdv7VOQHJ": "ar-LB-RamiNeural",       # Liam -> Rami (لبناني شبابي تقني)
    "IKne3meq5aSn9XLyUdCD": "ar-JO-TaimNeural",       # Charlie -> Taim (أردني حماسي واثق)
    "cgSgspJ2msm6clMCkdW9": "ar-JO-SanaNeural",       # Jessica -> Sana (أردنية وقورة)
    "cjVigY5qzO86Huf0OWal": "ar-EG-ShakirNeural",     # Eric -> Shakir (مصري سريع وحيوي)
}


# ─── معجم التشكيل اللغوي الفونيتيكي للنطق الطبيعي الفصيح (Arabic Phonetic Diacritizer) ───
ARABIC_DIACRITICS_DICT: Dict[str, str] = {
    # التحيات والتواصل الدافئ
    "سمير": "سَمِيرْ",
    "يا سمير": "يَا سَمِيرْ",
    "اهلاً": "أَهْلًا",
    "أهلا": "أَهْلًا",
    "أهلاً": "أَهْلًا",
    "اهلاً وسهلاً": "أَهْلًا وَسَهْلًا",
    "مرحبا": "مَرْحَبًا",
    "مرحباً": "مَرْحَبًا",
    "تفضل": "تَفَضَّلْ",
    "اتفضل": "اِتْفَضَّلْ",
    "ابشر": "أَبْشِرْ",
    "أبشر": "أَبْشِرْ",
    "شكرا": "شُكْرًا",
    "شكراً": "شُكْرًا",
    "عفوا": "عَفْوًا",
    "عفواً": "عَفْوًا",
    "يا غالي": "يَا غَالِي",
    "يا طيب": "يَا طَيِّبْ",
    "حبيبي": "حَبِيبِي",
    "من عيوني": "مِنْ عُيُونِي",
    "على راسي": "عَلَى رَاسِي",
    "ولا يهمك": "وَلَا يَهُمَّكْ",
    "بخير": "بِخَيْرٍ",
    "تمام": "تَمَامْ",
    "الحمد لله": "الْحَمْدُ لِلَّه",
    "ان شاء الله": "إِنْ شَاءَ اللَّه",
    "إن شاء الله": "إِنْ شَاءَ اللَّه",
    "والله": "وَاللَّهِ",
    "جاهز": "جَاهِزْ",
    "الآن": "الْآنَ",
    "الان": "الْآنَ",
    "اليوم": "الْيَوْمَ",

    # الأفعال المنجزة الشائعة
    "فتحت": "فَتَحْتُ",
    "فتحتلك": "فَتَحْتُ لَكَ",
    "شغلت": "شَغَّلْتُ",
    "شغلتلك": "شَغَّلْتُ لَكَ",
    "حفظت": "حَفِظْتُ",
    "حفظتلك": "حَفِظْتُ لَكَ",
    "عدلت": "عَدَّلْتُ",
    "عدلتلك": "عَدَّلْتُ لَكَ",
    "لقيت": "لَقِيتُ",
    "لقيتلك": "لَقِيتُ لَكَ",
    "جبت": "جِبْتُ",
    "جبتلك": "جِبْتُ لَكَ",
    "كتبت": "كَتَبْتُ",
    "نفذت": "نَفَّذْتُ",
    "اغلقت": "أَغْلَقْتُ",
    "أغلقت": "أَغْلَقْتُ",
    "قفلت": "قَفَلْتُ",
    "صورت": "صَوَّرْتُ",
    "ترجمت": "تَرْجَمْتُ",
    "سويت": "سَوَّيْتُ",
    "عملت": "عَمِلْتُ",
    "تم": "تَمَّ",

    # الكلمات التقنية والأسماء
    "المتصفح": "الْمُتَصَفِّح",
    "متصفح": "مُتَصَفِّح",
    "البرنامج": "الْبَرْنَامَج",
    "برنامج": "بَرْنَامَج",
    "التطبيق": "التَّطْبِيق",
    "تطبيق": "تَطْبِيق",
    "يوتيوب": "يُوتِيُوب",
    "الملف": "الْمِلَفّ",
    "ملف": "مِلَفّ",
    "المجلد": "الْمُجَلَّد",
    "مجلد": "مُجَلَّد",
    "الرابط": "الرَّابِط",
    "رابط": "رَابِط",
    "الشاشة": "الشَّاشَة",
    "شاشة": "شَاشَة",
    "الصوت": "الصَّوْت",
    "صوت": "صَوْت",
    "الصورة": "الصُّورَة",
    "صورة": "صُورَة",
    "فيديو": "فِيدْيُو",
    "الفيديو": "الْفِيدْيُو",
    "صفحة": "صَفْحَة",
    "الصفحة": "الصَّفْحَة",
    "بحث": "بَحْث",
    "البحث": "الْبَحْث",

    # خطوات الترتيب
    "اولا": "أَوَّلًا",
    "أولا": "أَوَّلًا",
    "أولاً": "أَوَّلًا",
    "ثانيا": "ثَانِيًا",
    "ثانياً": "ثَانِيًا",
    "ثالثا": "ثَالِثًا",
    "ثالثاً": "ثَالِثًا",
    "رابعا": "رَابِعًا",
    "رابعاً": "رَابِعًا",
    "خامسا": "خَامِسًا",
    "خامساً": "خَامِسًا",
    "اخيرا": "أَخِيرًا",
    "أخيراً": "أَخِيرًا",
    "خطوة": "خَطْوَة",

    # كلمات اللهجة الشائعة (ليبيا والخليج / السعودية)
    # ── اللهجة الليبية ──
    "شن": "شِنْ",
    "شنو": "شِنُو",
    "شن الجو": "شِنْ الْجَوّ",
    "الجو": "الْجَوّ",
    "باهي": "بَاهِي",
    "باهي تمام": "بَاهِي تَمَامْ",
    "ديرلي": "دِيرْلِي",
    "دير": "دِيرْ",
    "نديرلك": "نَدِيرْلِكْ",
    "ندير": "نَدِيرْ",
    "درتلك": "دِرْتْلِكْ",
    "درت": "دِرْتْ",
    "شوفلي": "شُوفْلِي",
    "شن تبي": "شِنْ تَبِي",
    "تبي": "تَبِي",
    "منور": "مُنَوِّرْ",
    "صحيت": "صَحِّيتْ",
    "بارك الله فيك": "بَارَكَ اللَّهُ فِيكْ",
    "هكي": "هَكِي",
    "توا": "تَوَّا",
    "قداش": "قَدَّاشْ",
    "شن صار": "شِنْ صَارْ",
    "خود راحتك": "خُودْ رَاحْتِكْ",
    "مية مية": "مِيَّة مِيَّة",
    "يا غالي": "يَا غَالِي",
    "يا طيب": "يَا طَيِّبْ",
    "هيا": "هَيَّا",
    "قاعد": "قَاعِدْ",
    "مش": "مِشْ",
    "علاش": "عَلَاشْ",
    "امتى": "اِمْتَى",
    "ساهل": "سَاهِلْ",
    "واعر": "وَاعِرْ",
    "هلبا": "هَلْبَا",

    # ── اللهجة السعودية ──
    "وين": "وِينْ",
    "كيف": "كَيْف",
    "ايش": "إِيشْ",
    "وش": "وِشْ",
    "وش تبغى": "وِشْ تَبْغَى",
    "وش تبي": "وِشْ تَبِي",
    "تبغى": "تَبْغَى",
    "أبشر": "أَبْشِرْ",
    "ابشر": "أَبْشِرْ",
    "سم": "سَمْ",
    "يا بعد راسي": "يَا بَعْدَ رَاسِي",
    "يا بعد حيي": "يَا بَعْدَ حَيِّي",
    "وش علومك": "وِشْ عُلُومِكْ",
    "وش سويت": "وِشْ سَوَّيْتْ",
    "سويتلك": "سَوَّيْتْ لِكْ",
    "سويته": "سَوَّيْتَهْ",
    "ضبطته": "ضَبَطْتَهْ",
    "ضبطتلك": "ضَبَطْتْ لِكْ",
    "الحين": "الْحِينْ",
    "حياك": "حَيَّاكْ",
    "حياك الله": "حَيَّاكَ اللَّهْ",
    "تسلم": "تِسْلَمْ",
    "ما قصرت": "مَا قَصَّرْتْ",
    "لاهنت": "لَا هِنْتْ",
    "لا هنت": "لَا هِنْتْ",
    "هلا": "هَلَا",
    "ياهلا": "يَا هَلَا",
    "يا هلا": "يَا هَلَا",
    "هلا والله": "هَلَا وَاللَّهْ",
    "يارجال": "يَا رَجَّالْ",
    "يا رجال": "يَا رَجَّالْ",
    "زين": "زَيْنْ",
    "كذا": "كِذَا",
    "مو كذا": "مُو كِذَا",
    "ما عليه": "مَا عَلَيْهْ",
    "شلونك": "شْلُونِكْ",
    "علومك": "عُلُومِكْ",
}


def diacritize_arabic_text(text: str) -> str:
    """
    تشكيل وضبط النص العربي بالحركات الفونيتيكية الدقيقة (الفتحة والضمة والكسرة والشدة والسكون)
    لتحسين نطق محركات ElevenLabs وEdge TTS بشكل احترافي وبشري طبيعي.
    """
    if not text:
        return ""

    diacritized = text

    # 1. تشكيل العبارات المركبة أولاً
    for phrase, voweled in sorted(ARABIC_DIACRITICS_DICT.items(), key=lambda x: -len(x[0])):
        if " " in phrase:
            diacritized = diacritized.replace(phrase, voweled)

    # 2. تشكيل الكلمات الفردية بدقة وسرعة
    def repl_word(m):
        w = m.group(0)
        return ARABIC_DIACRITICS_DICT.get(w, w)

    diacritized = re.sub(r'[\u0600-\u06FF]+', repl_word, diacritized)

    # 3. إضافة فواصل تنفس طبيعية عند حروف العطف الطويلة
    diacritized = re.sub(r'(\s+)(وَلَكِنْ|وَبَعْدَ ذَلِكَ|ثُمَّ|لِذَلِكَ)(\s+)', r'، \2\3', diacritized)

    return diacritized


def clean_text_for_speech(text: str) -> str:
    """
    تنظيف النص بذكاء وتشكيله لغوياً لتحويله إلى كلام بشري طبيعي ودافئ:
    1. استبدال كتل الأكواد البرمجية الطويلة بعبارة بشرية لطيفة حتى لا ينطق الرموز.
    2. إزالة علامات Markdown والترقيم المزعج والرموز التقنية.
    3. تطبيق التشكيل اللغوي الفونيتيكي لتحسين النطق ومخارج الحروف.
    4. إضافة فواصل طبيعية ليأخذ الصوت نفساً بشرياً في الجمل الطويلة.
    """
    if not text:
        return ""

    # 1. معالجة كتل الأكواد البرمجية (```...```) — لا نقرأ الأكواد حرفياً بالصوت
    text = re.sub(r'```[\s\S]*?```', '، الكود جاهز ومكتوب أمامك يا غالي، ', text)
    text = re.sub(r'`[^`\n]+`', ' ', text)  # الأكواد المضمنة القصيرة

    # 1.5. معالجة روابط الصور المضمنة في الرد
    text = re.sub(r'!\[.*?\]\(.*?\)', '، تم رسم الصورة وعرضها أمامك، ', text)

    # 2. إزالة روابط الويب
    text = re.sub(r'https?://\S+|www\.\S+', 'رابط', text)

    # 3. إزالة رؤوس Markdown والقوائم الرقمية مثل (1. 2. 3.) أو (- *)
    text = re.sub(r'^\s*[-*#]+\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s*', '', text, flags=re.MULTILINE)

    # 4. إزالة رموز التنسيق البرمجية
    text = re.sub(r'[\*\_#~\[\]\(\)\<\>\{\}\|\/\\]', ' ', text)

    # 5. تنظيف الترقيم المتتالي وجعل الفواصل مريحة للنطق
    text = re.sub(r'\.{2,}', '، ', text)
    text = re.sub(r'!{2,}', '! ', text)
    text = re.sub(r'\?{2,}', '؟ ', text)

    # 6. تنظيف المسافات والأسطر الفارغة
    text = re.sub(r'\s+', ' ', text).strip()

    # 7. تطبيق التشكيل اللغوي الصوتي لتحسين مخارج الحروف
    text = diacritize_arabic_text(text)

    return text


class TTSService:
    def __init__(
        self,
        voice: Optional[str] = None,
        rate: Optional[str] = None,
        pitch: Optional[str] = None,
        volume: Optional[str] = None
    ):
        self.voice = voice or getattr(settings, "DEFAULT_TTS_VOICE", None) or DEFAULT_VOICE_ID
        if self.voice not in AVAILABLE_VOICES:
            self.voice = DEFAULT_VOICE_ID
        self.rate = rate or getattr(settings, "TTS_RATE", None) or "+0%"
        self.pitch = pitch or getattr(settings, "TTS_PITCH", None) or "+0Hz"
        self.volume = volume or getattr(settings, "TTS_VOLUME", None) or "+0%"
        self.api_key = getattr(settings, "ELEVENLABS_API_KEY", "").strip()

    def update_api_key(self, new_key: str):
        """تحديث مفتاح ElevenLabs ديناميكياً أثناء تشغيل السيرفر"""
        self.api_key = new_key.strip()
        logger.info("ElevenLabs API key updated in TTSService.")

    async def get_quota_status(self) -> Dict[str, Any]:
        """فحص حالة الحصة والرصيد المتبقي لمفتاح ElevenLabs الحالي"""
        key = (self.api_key or getattr(settings, "ELEVENLABS_API_KEY", "")).strip()
        if not key:
            return {
                "status": "no_key",
                "message": "لا يوجد مفتاح ElevenLabs مسجل حالياً. يعمل سمير بالصوت العصبي الفصيح المجاني 100%.",
                "remaining_characters": 0,
                "total_characters": 0,
            }

        # التحقق إذا كان المستخدم ألصق Key ID (الذي لا يبدأ بـ sk_)
        if not key.startswith("sk_"):
            return {
                "status": "key_id_entered",
                "remaining_characters": 0,
                "total_characters": 0,
                "message": f"⚠️ الرمز الحالي ({key[:10]}...) هو معرّف المفتاح (Key ID) وليس المفتاح السري! مفاتيح ElevenLabs تبدأ دائماً بـ 'sk_'. يعمل سمير حالياً بالأصوات العصبية الفصيحة المجانية 100%.",
            }

        try:
            url = "https://api.elevenlabs.io/v1/user/subscription"
            headers = {"xi-api-key": key}
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    used = data.get("character_count", 0)
                    limit = data.get("character_limit", 10000)
                    remaining = max(0, limit - used)
                    tier = data.get("tier", "free")
                    if remaining <= 0:
                        return {
                            "status": "exhausted",
                            "tier": tier,
                            "character_count": used,
                            "character_limit": limit,
                            "remaining_characters": 0,
                            "remaining_formatted": "0 حرف (الحصة منتهية)",
                            "total_formatted": f"{limit:,} حرف",
                            "message": f"⚠️ انتهت الحصة المجانية ({used:,}/{limit:,} حرف). يعمل سمير تلقائياً بالأصوات العصبية الفصيحة المجانية 100%.",
                        }
                    return {
                        "status": "ok",
                        "tier": tier,
                        "character_count": used,
                        "character_limit": limit,
                        "remaining_characters": remaining,
                        "remaining_formatted": f"{remaining:,} حرف",
                        "total_formatted": f"{limit:,} حرف",
                        "message": f"✅ حساب ElevenLabs نشط. متبقي {remaining:,} حرف من أصل {limit:,}.",
                    }
                elif resp.status_code in (400, 401):
                    err_json = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                    detail = err_json.get("detail", {})
                    detail_status = detail.get("status") if isinstance(detail, dict) else str(detail)
                    detail_msg = detail.get("message", "") if isinstance(detail, dict) else str(detail)
                    if detail_status == "quota_exceeded" or "quota" in str(detail_msg).lower():
                        return {
                            "status": "exhausted",
                            "remaining_characters": 0,
                            "message": "⚠️ انتهت الحصة المجانية لحساب ElevenLabs بالكامل (0 متبقي). يعمل سمير حالياً بالصوت العصبي الفصيح المجاني.",
                        }
                    elif "api_key_id" in detail_status or "key id" in str(detail_msg).lower():
                        return {
                            "status": "key_id_entered",
                            "remaining_characters": 0,
                            "message": "⚠️ تم إدخال معرّف المفتاح (Key ID) بدلاً من المفتاح السري! مفاتيح ElevenLabs تبدأ دائماً بـ 'sk_'.",
                        }
                    return {
                        "status": "invalid_key",
                        "remaining_characters": 0,
                        "message": "مفتاح ElevenLabs غير صالح أو انتهت صلاحيته.",
                    }
                else:
                    return {
                        "status": "error",
                        "code": resp.status_code,
                        "message": f"تعذر التحقق من ElevenLabs (رمز {resp.status_code}).",
                    }
        except Exception as e:
            logger.error(f"Error checking ElevenLabs quota: {e}")
            return {
                "status": "error",
                "message": f"خطأ اتصال بـ ElevenLabs: {str(e)}",
            }

    def set_voice(self, voice_or_alias: str) -> Dict[str, Any]:
        """تغيير الصوت الحالي عبر اسم الصوت أو معرّفه من ElevenLabs"""
        v_clean = voice_or_alias.strip().lower()

        # 1. مطابقة مباشرة بالمعرف
        resolved_voice = None
        for vid in AVAILABLE_VOICES:
            if vid.lower() == v_clean:
                resolved_voice = vid
                break

        # 2. مطابقة عبر الأسماء المستعارة (آدم، سارة، برايان، عربي، إنجليزي...)
        if not resolved_voice:
            for alias, vid in VOICE_ALIASES.items():
                if alias.lower() in v_clean:
                    resolved_voice = vid
                    break

        # 3. مطابقة جزئية باسم الصوت
        if not resolved_voice:
            for vid, info in AVAILABLE_VOICES.items():
                if v_clean in info["name"].lower():
                    resolved_voice = vid
                    break

        if resolved_voice and resolved_voice in AVAILABLE_VOICES:
            self.voice = resolved_voice
            voice_info = AVAILABLE_VOICES[resolved_voice]
            logger.info(f"TTS Voice switched to ElevenLabs: {resolved_voice} ({voice_info['name']})")
            return {
                "success": True,
                "voice_id": resolved_voice,
                "voice_info": voice_info,
                "message": f"تم تفعيل صوت ElevenLabs: {voice_info['name']} بنجاح! 🎙️"
            }

        return {
            "success": False,
            "message": f"لم يتم العثور على الصوت '{voice_or_alias}'. الأصوات المتاحة: آدم (Adam)، سارة (Sarah)، برايان (Brian)، بيلا (Bella)، أليس (Alice)، جورج (George)، دانيال (Daniel)، ليلي (Lily)، ليام (Liam)، تشارلي (Charlie)، جيسيكا (Jessica)، إريك (Eric)، كريس (Chris)، ويل (Will)، ماتيلدا (Matilda)، روجر (Roger)، لورا (Laura)، بيل (Bill)."
        }

    def get_voice_info(self) -> Dict[str, Any]:
        """معلومات صوت ElevenLabs المفعل حالياً"""
        return AVAILABLE_VOICES.get(self.voice, AVAILABLE_VOICES[DEFAULT_VOICE_ID])

    def list_voices(self) -> List[Dict[str, Any]]:
        """قائمة بجميع أصوات ElevenLabs المتاحة لسمير"""
        result = []
        for vid, info in AVAILABLE_VOICES.items():
            item = dict(info)
            item["is_active"] = (vid == self.voice)
            result.append(item)
        return result

    async def generate_speech_bytes(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: Optional[str] = None
    ) -> bytes:
        """
        توليد ملف صوتي كامل (MP3 bytes) باستخدام ElevenLabs باللغتين العربية والإنجليزية
        مع fallback آمن في حال عدم توفر المفتاح
        """
        clean_text = clean_text_for_speech(text)
        if not clean_text:
            return b""

        selected_voice = voice or self.voice
        if selected_voice not in AVAILABLE_VOICES:
            for alias, vid in VOICE_ALIASES.items():
                if alias in selected_voice.lower():
                    selected_voice = vid
                    break
            if selected_voice not in AVAILABLE_VOICES:
                selected_voice = DEFAULT_VOICE_ID

        # ── 1. الأصوات الفصيحة المجانية (0 كريدت - مجانية وسريعة 100%) ──
        is_free_voice = selected_voice.startswith("ar-") or AVAILABLE_VOICES.get(selected_voice, {}).get("is_free", False)
        if is_free_voice:
            try:
                edge_voice = selected_voice if selected_voice.startswith("ar-") else "ar-SA-HamedNeural"
                communicate = edge_tts.Communicate(
                    text=clean_text,
                    voice=edge_voice,
                    rate=self.rate,
                    pitch=self.pitch,
                    volume=self.volume
                )
                audio_buffer = io.BytesIO()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_buffer.write(chunk["data"])
                val = audio_buffer.getvalue()
                if val:
                    return val
            except Exception as e:
                logger.error(f"Free Edge-TTS error for {selected_voice}: {e}")

        api_key = getattr(self, "api_key", None) or getattr(settings, "ELEVENLABS_API_KEY", "").strip()
        model_id = getattr(settings, "ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

        # ── 2. التوليد عبر ElevenLabs API للأصوات المدفوعة (عند توفر مفتاح sk_ ورصيد) ──
        if api_key and api_key.startswith("sk_"):
            try:
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{selected_voice}?output_format=mp3_44100_128"
                headers = {
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg"
                }
                payload = {
                    "text": clean_text,
                    "model_id": model_id,
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.8,
                        "style": 0.0,
                        "use_speaker_boost": True
                    }
                }
                async with httpx.AsyncClient(timeout=30.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200 and resp.content:
                        logger.info(f"ElevenLabs speech generated successfully ({len(resp.content)} bytes, voice: {selected_voice})")
                        return resp.content
                    else:
                        logger.warning(f"ElevenLabs TTS status {resp.status_code} - Falling back to free neural voice.")
            except Exception as e:
                logger.error(f"Error calling ElevenLabs TTS API: {e}")
        else:
            logger.info("Using high quality free Arabic Neural TTS (0 credits consumed).")

        # ── 3. محرك بديل فصيح مجاني فائق التنوع في حال نفاد رصيد ElevenLabs ──
        try:
            fallback_edge_voice = ELEVENLABS_FALLBACK_MAP.get(selected_voice)
            if not fallback_edge_voice:
                gender = AVAILABLE_VOICES.get(selected_voice, {}).get("gender", "male")
                fallback_edge_voice = "ar-SA-ZariyahNeural" if gender == "female" else "ar-SA-HamedNeural"

            communicate = edge_tts.Communicate(
                text=clean_text,
                voice=fallback_edge_voice,
                rate=self.rate,
                pitch=self.pitch,
                volume=self.volume
            )
            audio_buffer = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_buffer.write(chunk["data"])
            return audio_buffer.getvalue()
        except Exception as e:
            logger.error(f"Fallback TTS error: {e}")
            return b""

    async def stream_speech_chunks(
        self,
        text: str,
        voice: Optional[str] = None
    ) -> AsyncGenerator[bytes, None]:
        """
        دفق الصوت كـ Chunks للـ Realtime Streaming عبر ElevenLabs
        """
        clean_text = clean_text_for_speech(text)
        if not clean_text:
            return

        selected_voice = voice or self.voice
        if selected_voice not in AVAILABLE_VOICES:
            selected_voice = DEFAULT_VOICE_ID

        api_key = getattr(self, "api_key", None) or getattr(settings, "ELEVENLABS_API_KEY", "").strip()
        model_id = getattr(settings, "ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

        if api_key:
            try:
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{selected_voice}/stream?output_format=mp3_44100_128"
                headers = {
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg"
                }
                payload = {
                    "text": clean_text,
                    "model_id": model_id,
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.8,
                        "style": 0.0,
                        "use_speaker_boost": True
                    }
                }
                async with httpx.AsyncClient(timeout=30.0) as client:
                    async with client.stream("POST", url, headers=headers, json=payload) as resp:
                        if resp.status_code == 200:
                            async for chunk in resp.aiter_bytes():
                                if chunk:
                                    yield chunk
                            return
                        else:
                            logger.error(f"ElevenLabs stream returned {resp.status_code}")
            except Exception as e:
                logger.error(f"ElevenLabs stream error: {e}")

        # Fallback stream
        try:
            fallback_edge_voice = ELEVENLABS_FALLBACK_MAP.get(selected_voice)
            if not fallback_edge_voice:
                gender = AVAILABLE_VOICES.get(selected_voice, {}).get("gender", "male")
                fallback_edge_voice = "ar-SA-ZariyahNeural" if gender == "female" else "ar-SA-HamedNeural"
            communicate = edge_tts.Communicate(
                text=clean_text,
                voice=fallback_edge_voice,
                rate=self.rate,
                pitch=self.pitch,
                volume=self.volume
            )
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
        except Exception as e:
            logger.error(f"Fallback stream error: {e}")


tts_service = TTSService()
