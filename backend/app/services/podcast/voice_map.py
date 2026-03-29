from __future__ import annotations

from typing import Dict, List

VOICE_MAP: Dict[str, List[dict]] = {
    "en": [
        {"id": "en-US-GuyNeural", "name": "Guy", "gender": "male", "description": "Warm, conversational American male"},
        {"id": "en-US-JennyNeural", "name": "Jenny", "gender": "female", "description": "Clear, friendly American female"},
        {"id": "en-US-ChristopherNeural", "name": "Christopher", "gender": "male", "description": "Professional, steady American male"},
        {"id": "en-US-AriaNeural", "name": "Aria", "gender": "female", "description": "Expressive, engaging American female"},
    ],
    "hi": [
        {"id": "hi-IN-MadhurNeural", "name": "Madhur", "gender": "male", "description": "Natural Hindi male voice"},
        {"id": "hi-IN-SwaraNeural", "name": "Swara", "gender": "female", "description": "Warm Hindi female voice"},
    ],
    "gu": [
        {"id": "gu-IN-NiranjanNeural", "name": "Niranjan", "gender": "male", "description": "Natural Gujarati male voice"},
        {"id": "gu-IN-DhwaniNeural", "name": "Dhwani", "gender": "female", "description": "Warm Gujarati female voice"},
    ],
    "es": [
        {"id": "es-ES-AlvaroNeural", "name": "Alvaro", "gender": "male", "description": "Professional Spanish male"},
        {"id": "es-ES-ElviraNeural", "name": "Elvira", "gender": "female", "description": "Natural Spanish female"},
    ],
    "ar": [
        {"id": "ar-SA-HamedNeural", "name": "Hamed", "gender": "male", "description": "Clear Arabic male voice"},
        {"id": "ar-SA-ZariyahNeural", "name": "Zariyah", "gender": "female", "description": "Warm Arabic female voice"},
    ],
    "fr": [
        {"id": "fr-FR-HenriNeural", "name": "Henri", "gender": "male", "description": "Professional French male"},
        {"id": "fr-FR-DeniseNeural", "name": "Denise", "gender": "female", "description": "Natural French female"},
    ],
    "de": [
        {"id": "de-DE-ConradNeural", "name": "Conrad", "gender": "male", "description": "Clear German male voice"},
        {"id": "de-DE-KatjaNeural", "name": "Katja", "gender": "female", "description": "Professional German female"},
    ],
    "ja": [
        {"id": "ja-JP-KeitaNeural", "name": "Keita", "gender": "male", "description": "Natural Japanese male"},
        {"id": "ja-JP-NanamiNeural", "name": "Nanami", "gender": "female", "description": "Clear Japanese female"},
    ],
    "zh": [
        {"id": "zh-CN-YunxiNeural", "name": "Yunxi", "gender": "male", "description": "Natural Chinese male"},
        {"id": "zh-CN-XiaoxiaoNeural", "name": "Xiaoxiao", "gender": "female", "description": "Warm Chinese female"},
    ],
    "pt": [
        {"id": "pt-BR-AntonioNeural", "name": "Antonio", "gender": "male", "description": "Natural Portuguese male"},
        {"id": "pt-BR-FranciscaNeural", "name": "Francisca", "gender": "female", "description": "Warm Portuguese female"},
    ],
}

DEFAULT_VOICES: Dict[str, dict] = {
    "en": {"host": "en-US-GuyNeural", "guest": "en-US-JennyNeural"},
    "hi": {"host": "hi-IN-MadhurNeural", "guest": "hi-IN-SwaraNeural"},
    "gu": {"host": "gu-IN-NiranjanNeural", "guest": "gu-IN-DhwaniNeural"},
    "es": {"host": "es-ES-AlvaroNeural", "guest": "es-ES-ElviraNeural"},
    "ar": {"host": "ar-SA-HamedNeural", "guest": "ar-SA-ZariyahNeural"},
    "fr": {"host": "fr-FR-HenriNeural", "guest": "fr-FR-DeniseNeural"},
    "de": {"host": "de-DE-ConradNeural", "guest": "de-DE-KatjaNeural"},
    "ja": {"host": "ja-JP-KeitaNeural", "guest": "ja-JP-NanamiNeural"},
    "zh": {"host": "zh-CN-YunxiNeural", "guest": "zh-CN-XiaoxiaoNeural"},
    "pt": {"host": "pt-BR-AntonioNeural", "guest": "pt-BR-FranciscaNeural"},
}

LANGUAGE_NAMES: Dict[str, str] = {
    "en": "English", "hi": "Hindi", "gu": "Gujarati", "bn": "Bengali",
    "ta": "Tamil", "te": "Telugu", "mr": "Marathi", "kn": "Kannada",
    "ml": "Malayalam", "pa": "Punjabi", "ur": "Urdu", "or": "Odia",
    "es": "Spanish", "ar": "Arabic", "fr": "French", "de": "German",
    "ja": "Japanese", "zh": "Chinese", "pt": "Portuguese",
}

PREVIEW_TEXTS: Dict[str, str] = {
    "en": "Welcome to this podcast where we explore fascinating topics together.",
    "hi": "इस पॉडकास्ट में आपका स्वागत है जहाँ हम साथ मिलकर दिलचस्प विषयों की खोज करते हैं।",
    "gu": "આ પોડકાસ્ટમાં આપનું સ્વાગત છે જ્યાં આપણે સાથે મળીને રસપ્રદ વિષયોની શોધ કરીએ છીએ.",
    "bn": "এই পডকাস্টে আপনাকে স্বাগতম, যেখানে আমরা একসাথে আকর্ষণীয় বিষয়গুলি অন্বেষণ করি।",
    "ta": "இந்த பாட்காஸ்டிற்கு வரவேற்கிறோம். நாம் சேர்ந்து சுவாரஸ்யமான தலைப்புகளை ஆராய்வோம்.",
    "te": "ఈ పోడ్‌కాస్ట్‌కు స్వాగతం. మనం కలిసి ఆసక్తికరమైన విషయాలను అన్వేషిద్దాం.",
    "mr": "या पॉडकास्टमध्ये आपले स्वागत आहे, जिथे आपण एकत्रितपणे रंजक विषयांचा अभ्यास करतो.",
    "kn": "ಈ ಪಾಡ್‌ಕಾಸ್ಟ್‌ಗೆ ಸ್ವಾಗತ, ಇಲ್ಲಿ ನಾವು ಒಟ್ಟಿಗೆ ಆಸಕ್ತಿದಾಯಕ ವಿಷಯಗಳನ್ನು ಅನ್ವೇಷಿಸುತ್ತೇವೆ.",
    "ml": "ഈ പോഡ്കാസ്റ്റിലേക്ക് സ്വാഗതം, ഇവിടെ നാം ഒരുമിച്ച് ആകർഷകമായ വിഷയങ്ങൾ അന്വേഷിക്കുന്നു.",
    "pa": "ਇਸ ਪੋਡਕਾਸਟ ਵਿੱਚ ਤੁਹਾਡਾ ਸੁਆਗਤ ਹੈ, ਜਿੱਥੇ ਅਸੀਂ ਇਕੱਠੇ ਦਿਲਚਸਪ ਵਿਸ਼ਿਆਂ ਦੀ ਖੋਜ ਕਰਦੇ ਹਾਂ।",
    "ur": "اس پوڈکاسٹ میں خوش آمدید، جہاں ہم مل کر دلچسپ موضوعات کو دریافت کرتے ہیں۔",
    "or": "ଏହି ପଡକାଷ୍ଟକୁ ସ୍ୱାଗତ, ଯେଉଁଠାରେ ଆମେ ସଙ୍ଗେ ସଙ୍ଗେ ଆକର୍ଷଣୀୟ ବିଷୟ ଅନୁସନ୍ଧାନ କରୁଛୁ।",
    "es": "Bienvenidos a este podcast donde exploramos temas fascinantes juntos.",
    "ar": "مرحبًا بكم في هذا البودكاست حيث نستكشف معًا مواضيع رائعة.",
    "fr": "Bienvenue dans ce podcast où nous explorons ensemble des sujets fascinants.",
    "de": "Willkommen zu diesem Podcast, in dem wir gemeinsam faszinierende Themen erkunden.",
    "ja": "このポッドキャストへようこそ。一緒に魅力的なトピックを探求しましょう。",
    "zh": "欢迎来到本播客，让我们一起探索有趣的话题。",
    "pt": "Bem-vindos a este podcast onde exploramos temas fascinantes juntos.",
}

def normalize_language_code(language: str) -> str:
    raw = str(language or "").strip().lower().replace("_", "-")
    if not raw:
        return "en"
    if raw in VOICE_MAP:
        return raw
    root = raw.split("-", 1)[0]
    if root in VOICE_MAP:
        return root
    return raw


def get_voices_for_language(language: str) -> List[dict]:
    normalized = normalize_language_code(language)
    return VOICE_MAP.get(normalized, [])

def get_default_voices(language: str) -> dict:
    normalized = normalize_language_code(language)
    return DEFAULT_VOICES.get(normalized, {})

def get_preview_text(language: str) -> str:
    normalized = normalize_language_code(language)
    return PREVIEW_TEXTS.get(normalized, PREVIEW_TEXTS["en"])

def validate_voice(voice_id: str, language: str) -> bool:
    voices = get_voices_for_language(language)
    return any(v["id"] == voice_id for v in voices)
