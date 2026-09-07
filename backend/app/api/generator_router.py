import json
import logging
import random
import re
from random import shuffle
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import google.generativeai as genai

from app.database import get_db
from app.models import User, SavedBrand
from app.schemas import (
    BrandRequest,
    BrandResponse,
    SavedBrandCreate,
    SavedBrandResponse
)
from app.auth import get_current_user
from app.config import GEMINI_API_KEY, HAS_GEMINI_KEY

router = APIRouter(prefix="/api/generator", tags=["generator"])

logger = logging.getLogger(__name__)


# ============================================================
# LOCAL MULTILINGUAL FALLBACK GENERATOR
# ============================================================

LANGUAGE_DATA = {

    "english": {
        "prefix": [
            "Nova", "Bright", "Bold", "Fresh", "Prime",
            "Vivid", "Apex", "Luxe", "Swift", "Pure",
            "Urban", "True", "Smart", "Blue", "Next"
        ],
        "suffix": [
            "ora", "ify", "hub", "nest", "wave",
            "forge", "flow", "labs", "works", "space",
            "studio", "core", "craft", "verse", "spark"
        ],
        "meanings": [
            "A modern brand created to bring fresh ideas and strong experiences.",
            "A bold identity designed for ambitious businesses and modern customers.",
            "A creative brand representing innovation, quality, and forward thinking.",
            "A distinctive identity designed to connect with today's audience.",
            "A powerful brand concept focused on growth, creativity, and trust."
        ],
        "taglines": [
            "Innovation that inspires.",
            "Built for a brighter future.",
            "Ideas that move forward.",
            "Create. Connect. Grow.",
            "Your vision, our inspiration."
        ]
    },

    "telugu": {
        "prefix": [
            "తేజ", "నవ", "స్ఫూర్తి", "విజయ", "ధైర్య",
            "ప్రభ", "ఆశ", "శ్రేయ", "జయ", "కళ",
            "ప్రగతి", "సృజన", "వెలుగు", "ఆనంద", "మేధ"
        ],
        "suffix": [
            "కళ", "కిరణ్", "దీపం", "తరంగం", "శక్తి",
            "ప్రవాహం", "స్ఫూర్తి", "విజయం", "మయి", "వాణి",
            "లోకం", "ధారా", "రేఖ", "జ్యోతి", "మార్గం"
        ],
        "meanings": [
            "ఈ పేరు సృజనాత్మకత, నూతన ఆలోచనలు మరియు విజయాన్ని సూచిస్తుంది.",
            "ఈ బ్రాండ్ పేరు ఆధునికత, నమ్మకం మరియు అభివృద్ధిని ప్రతిబింబిస్తుంది.",
            "ఈ పేరు లక్ష్య ప్రేక్షకులతో బలమైన అనుబంధాన్ని సృష్టించేలా రూపొందించబడింది.",
            "ఈ పేరు కొత్త ఆలోచనలకు మరియు వ్యాపార అభివృద్ధికి ప్రతీకగా ఉంటుంది.",
            "ఈ బ్రాండ్ పేరు నాణ్యత, శక్తి మరియు ప్రత్యేకతను సూచిస్తుంది."
        ],
        "taglines": [
            "మీ ఆలోచనకు కొత్త రూపం.",
            "విజయానికి మీ కొత్త అడుగు.",
            "ఆలోచనల నుంచి ఆవిష్కరణ వరకు.",
            "మీ కలలకు మా స్ఫూర్తి.",
            "కొత్త ఆలోచనలకు కొత్త శక్తి."
        ]
    },

    "hindi": {
        "prefix": [
            "नव", "तेज", "शुभ", "सृजन", "उदय",
            "विजय", "प्रेरणा", "आशा", "शक्ति", "स्वर्ण",
            "नई", "उन्नति", "प्रकाश", "सफल", "दृष्टि"
        ],
        "suffix": [
            "दीप", "धारा", "कला", "शक्ति", "तरंग",
            "मंच", "लोक", "दृष्टि", "पथ", "ज्योति",
            "विश्व", "लहर", "केंद्र", "आभा", "सृजन"
        ],
        "meanings": [
            "यह नाम नई सोच, रचनात्मकता और सफलता को दर्शाता है।",
            "यह ब्रांड नाम आधुनिकता, विश्वास और विकास का प्रतीक है।",
            "यह नाम लक्षित ग्राहकों के साथ मजबूत भावनात्मक जुड़ाव बनाने के लिए तैयार किया गया है।",
            "यह नाम नए विचारों और व्यावसायिक विकास को दर्शाता है।",
            "यह ब्रांड पहचान गुणवत्ता, ऊर्जा और विशिष्टता को व्यक्त करती है।"
        ],
        "taglines": [
            "आपके विचारों की नई पहचान।",
            "सपनों को नई उड़ान।",
            "हर विचार में नई शक्ति।",
            "आपकी पहचान, आपकी कहानी।",
            "नए विचारों की नई शुरुआत।"
        ]
    },

    "marathi": {
        "prefix": [
            "नव", "तेज", "उदय", "सृजन", "यश",
            "स्वप्न", "आशा", "धैर्य", "शुभ", "प्रेरणा",
            "उत्कर्ष", "प्रगती", "प्रकाश", "समृद्धी", "विश्वास"
        ],
        "suffix": [
            "दीप", "धारा", "कला", "शक्ती", "लहरी",
            "विश्व", "मंच", "दृष्टी", "पथ", "ज्योत",
            "तरंग", "सृष्टी", "किरण", "गती", "आभा"
        ],
        "meanings": [
            "हे नाव नवीन कल्पना, सर्जनशीलता आणि यशाचे प्रतीक आहे.",
            "हे ब्रँड नाव आधुनिकता, विश्वास आणि प्रगती दर्शवते.",
            "हे नाव ग्राहकांशी मजबूत भावनिक नाते निर्माण करण्यासाठी तयार केले आहे.",
            "हे नाव नवीन विचार आणि व्यवसायाच्या वाढीचे प्रतिनिधित्व करते.",
            "ही ब्रँड ओळख गुणवत्ता, ऊर्जा आणि वेगळेपणा व्यक्त करते."
        ],
        "taglines": [
            "तुमच्या स्वप्नांना नवी ओळख.",
            "कल्पनांना यशाची नवी दिशा.",
            "तुमच्या ब्रँडची नवी सुरुवात.",
            "कल्पनेपासून ओळखीपर्यंत.",
            "यशासाठी नवी ऊर्जा."
        ]
    },

    "tamil": {
        "prefix": [
            "நவ", "வெற்றி", "அருள்", "ஒளி", "திறன்",
            "புது", "சக்தி", "அழகு", "வளம்", "மகிழ்",
            "புதிய", "உயர்", "நம்பிக்கை", "படைப்பு", "வளர்"
        ],
        "suffix": [
            "கலை", "வேகம்", "உலகம்", "அலை", "ஒளி",
            "சக்தி", "வளம்", "மையம்", "நதி", "விழி",
            "வானம்", "பாதை", "தீபம்", "மலர்", "அருவி"
        ],
        "meanings": [
            "இந்த பெயர் புதிய சிந்தனை, படைப்பாற்றல் மற்றும் வெற்றியை குறிக்கிறது.",
            "இந்த பிராண்ட் பெயர் நவீனத்தன்மை, நம்பிக்கை மற்றும் வளர்ச்சியை பிரதிபலிக்கிறது.",
            "இந்த பெயர் வாடிக்கையாளர்களுடன் வலுவான தொடர்பை உருவாக்கும் வகையில் அமைக்கப்பட்டுள்ளது.",
            "இந்த பெயர் புதிய யோசனைகள் மற்றும் வணிக வளர்ச்சியை குறிக்கிறது.",
            "இந்த பிராண்ட் அடையாளம் தரம், ஆற்றல் மற்றும் தனித்துவத்தை வெளிப்படுத்துகிறது."
        ],
        "taglines": [
            "உங்கள் கனவுக்கு புதிய அடையாளம்.",
            "புதிய எண்ணங்களுக்கு புதிய பாதை.",
            "உங்கள் பிராண்டின் புதிய பயணம்.",
            "எண்ணங்களில் இருந்து வெற்றிக்கு.",
            "உங்கள் கனவு, எங்கள் ஊக்கம்."
        ]
    },

    "kannada": {
        "prefix": [
            "ನವ", "ವಿಜಯ", "ತೇಜ", "ಸೃಜನ", "ಉದಯ",
            "ಶಕ್ತಿ", "ಆಶಾ", "ಸ್ಪೂರ್ತಿ", "ಧೈರ್ಯ", "ಶುಭ",
            "ಪ್ರಗತಿ", "ಬೆಳಕು", "ಯಶ", "ನಂಬಿಕೆ", "ಸಮೃದ್ಧಿ"
        ],
        "suffix": [
            "ಕಲೆ", "ಜ್ಯೋತಿ", "ಧಾರೆ", "ತರಂಗ", "ಶಕ್ತಿ",
            "ಲೋಕ", "ದೃಷ್ಟಿ", "ಮಾರ್ಗ", "ವಿಶ್ವ", "ಬೆಳಕು",
            "ಕಿರಣ", "ಪಥ", "ಸೃಷ್ಟಿ", "ನದಿ", "ಗತಿ"
        ],
        "meanings": [
            "ಈ ಹೆಸರು ಹೊಸ ಆಲೋಚನೆ, ಸೃಜನಶೀಲತೆ ಮತ್ತು ಯಶಸ್ಸನ್ನು ಪ್ರತಿನಿಧಿಸುತ್ತದೆ.",
            "ಈ ಬ್ರ್ಯಾಂಡ್ ಹೆಸರು ಆಧುನಿಕತೆ, ನಂಬಿಕೆ ಮತ್ತು ಬೆಳವಣಿಗೆಯನ್ನು ಸೂಚಿಸುತ್ತದೆ.",
            "ಈ ಹೆಸರು ಗ್ರಾಹಕರೊಂದಿಗೆ ಬಲವಾದ ಸಂಬಂಧವನ್ನು ನಿರ್ಮಿಸಲು ವಿನ್ಯಾಸಗೊಳಿಸಲಾಗಿದೆ.",
            "ಈ ಹೆಸರು ಹೊಸ ಆಲೋಚನೆಗಳು ಮತ್ತು ವ್ಯಾಪಾರದ ಬೆಳವಣಿಗೆಯನ್ನು ಪ್ರತಿಬಿಂಬಿಸುತ್ತದೆ.",
            "ಈ ಬ್ರ್ಯಾಂಡ್ ಗುರುತು ಗುಣಮಟ್ಟ, ಶಕ್ತಿ ಮತ್ತು ವಿಶಿಷ್ಟತೆಯನ್ನು ವ್ಯಕ್ತಪಡಿಸುತ್ತದೆ."
        ],
        "taglines": [
            "ನಿಮ್ಮ ಕನಸಿಗೆ ಹೊಸ ಗುರುತು.",
            "ಹೊಸ ಆಲೋಚನೆಗಳಿಗೆ ಹೊಸ ದಾರಿ.",
            "ನಿಮ್ಮ ಬ್ರ್ಯಾಂಡ್‌ನ ಹೊಸ ಆರಂಭ.",
            "ಆಲೋಚನೆಯಿಂದ ಯಶಸ್ಸಿನವರೆಗೆ.",
            "ನಿಮ್ಮ ಕನಸು, ನಮ್ಮ ಪ್ರೇರಣೆ."
        ]
    },

    "malayalam": {
        "prefix": [
            "നവ", "വിജയ", "തേജ", "സൃഷ്ടി", "ഉദയ",
            "ശക്തി", "ആശ", "സ്പന്ദന", "ധൈര്യ", "ശുഭ",
            "പ്രഗതി", "പ്രകാശ", "വിശ്വാസ", "സമൃദ്ധി", "സ്വപ്ന"
        ],
        "suffix": [
            "കല", "ജ്യോതി", "ധാര", "തിര", "ശക്തി",
            "ലോകം", "ദൃഷ്ടി", "പാത", "വിശ്വ", "പ്രഭ",
            "കിരണം", "സൃഷ്ടി", "നദി", "വഴി", "താളം"
        ],
        "meanings": [
            "ഈ പേര് പുതിയ ആശയങ്ങളെയും സർഗ്ഗാത്മകതയെയും വിജയത്തെയും പ്രതിനിധീകരിക്കുന്നു.",
            "ഈ ബ്രാൻഡ് പേര് ആധുനികത, വിശ്വാസം, വളർച്ച എന്നിവയെ പ്രതിഫലിപ്പിക്കുന്നു.",
            "ഉപഭോക്താക്കളുമായി ശക്തമായ ബന്ധം സൃഷ്ടിക്കുന്നതിനാണ് ഈ പേര് രൂപകൽപ്പന ചെയ്തിരിക്കുന്നത്.",
            "പുതിയ ചിന്തകളെയും ബിസിനസ് വളർച്ചയെയും ഈ പേര് സൂചിപ്പിക്കുന്നു.",
            "ഈ ബ്രാൻഡ് തിരിച്ചറിയൽ ഗുണനിലവാരവും ശക്തിയും സവിശേഷതയും പ്രകടിപ്പിക്കുന്നു."
        ],
        "taglines": [
            "നിങ്ങളുടെ സ്വപ്നങ്ങൾക്ക് പുതിയ തിരിച്ചറിയൽ.",
            "പുതിയ ആശയങ്ങൾക്ക് പുതിയ വഴി.",
            "നിങ്ങളുടെ ബ്രാൻഡിന്റെ പുതിയ തുടക്കം.",
            "ആശയങ്ങളിൽ നിന്ന് വിജയത്തിലേക്ക്.",
            "നിങ്ങളുടെ സ്വപ്നം, ഞങ്ങളുടെ പ്രചോദനം."
        ]
    },

    "bengali": {
        "prefix": [
            "নব", "জয়", "আলো", "সৃষ্টি", "উদয়",
            "শক্তি", "আশা", "প্রেরণা", "তেজ", "শুভ",
            "প্রগতি", "বিশ্বাস", "সমৃদ্ধি", "স্বপ্ন", "নতুন"
        ],
        "suffix": [
            "ধারা", "কলা", "জ্যোতি", "তরঙ্গ", "শক্তি",
            "বিশ্ব", "পথ", "দৃষ্টি", "লোক", "প্রভা",
            "কিরণ", "সৃষ্টি", "গতি", "আভা", "নীড়"
        ],
        "meanings": [
            "এই নামটি নতুন চিন্তা, সৃজনশীলতা এবং সাফল্যের প্রতীক।",
            "এই ব্র্যান্ড নামটি আধুনিকতা, বিশ্বাস এবং উন্নতির প্রতিনিধিত্ব করে।",
            "গ্রাহকদের সঙ্গে শক্তিশালী সম্পর্ক তৈরি করার জন্য এই নামটি তৈরি করা হয়েছে।",
            "এই নামটি নতুন ধারণা এবং ব্যবসায়িক বৃদ্ধিকে প্রকাশ করে।",
            "এই ব্র্যান্ড পরিচয় গুণমান, শক্তি এবং স্বাতন্ত্র্য প্রকাশ করে।"
        ],
        "taglines": [
            "আপনার স্বপ্নের নতুন পরিচয়।",
            "নতুন ভাবনার নতুন পথ।",
            "আপনার ব্র্যান্ডের নতুন শুরু।",
            "ভাবনা থেকে সাফল্যের পথে।",
            "আপনার স্বপ্ন, আমাদের অনুপ্রেরণা।"
        ]
    },

    "gujarati": {
        "prefix": [
            "નવ", "જય", "તેજ", "સર્જન", "ઉદય",
            "શક્તિ", "આશા", "પ્રેરણા", "શુભ", "વિજય",
            "પ્રગતિ", "પ્રકાશ", "વિશ્વાસ", "સમૃદ્ધિ", "સ્વપ્ન"
        ],
        "suffix": [
            "કલા", "જ્યોતિ", "ધારા", "તરંગ", "શક્તિ",
            "વિશ્વ", "દૃષ્ટિ", "માર્ગ", "લોક", "પ્રભા",
            "કિરણ", "સર્જન", "ગતિ", "આભા", "વલય"
        ],
        "meanings": [
            "આ નામ નવી વિચારસરણી, સર્જનાત્મકતા અને સફળતાનું પ્રતિનિધિત્વ કરે છે.",
            "આ બ્રાન્ડ નામ આધુનિકતા, વિશ્વાસ અને વિકાસ દર્શાવે છે.",
            "ગ્રાહકો સાથે મજબૂત જોડાણ બનાવવા માટે આ નામ તૈયાર કરવામાં આવ્યું છે.",
            "આ નામ નવા વિચારો અને વ્યવસાયિક વિકાસનું પ્રતિનિધિત્વ કરે છે.",
            "આ બ્રાન્ડ ઓળખ ગુણવત્તા, શક્તિ અને વિશિષ્ટતા દર્શાવે છે."
        ],
        "taglines": [
            "તમારા સપનાની નવી ઓળખ.",
            "નવા વિચારો માટે નવી દિશા.",
            "તમારી બ્રાન્ડની નવી શરૂઆત.",
            "વિચારથી સફળતા સુધી.",
            "તમારું સ્વપ્ન, અમારી પ્રેરણા."
        ]
    },

    "punjabi": {
        "prefix": [
            "ਨਵ", "ਜਿੱਤ", "ਤੇਜ", "ਸਿਰਜਣ", "ਉਦਯ",
            "ਸ਼ਕਤੀ", "ਆਸ", "ਪ੍ਰੇਰਣਾ", "ਸ਼ੁਭ", "ਵਿਜੈ",
            "ਤਰੱਕੀ", "ਰੋਸ਼ਨੀ", "ਵਿਸ਼ਵਾਸ", "ਸਮਰਿੱਧੀ", "ਸੁਪਨਾ"
        ],
        "suffix": [
            "ਕਲਾ", "ਜੋਤ", "ਧਾਰਾ", "ਲਹਿਰ", "ਸ਼ਕਤੀ",
            "ਲੋਕ", "ਦ੍ਰਿਸ਼ਟੀ", "ਰਾਹ", "ਵਿਸ਼ਵ", "ਪ੍ਰਭਾ",
            "ਕਿਰਨ", "ਸਿਰਜਣ", "ਗਤੀ", "ਆਭਾ", "ਮੰਚ"
        ],
        "meanings": [
            "ਇਹ ਨਾਮ ਨਵੀਂ ਸੋਚ, ਰਚਨਾਤਮਕਤਾ ਅਤੇ ਸਫਲਤਾ ਨੂੰ ਦਰਸਾਉਂਦਾ ਹੈ।",
            "ਇਹ ਬ੍ਰਾਂਡ ਨਾਮ ਆਧੁਨਿਕਤਾ, ਭਰੋਸੇ ਅਤੇ ਵਿਕਾਸ ਦਾ ਪ੍ਰਤੀਕ ਹੈ।",
            "ਗਾਹਕਾਂ ਨਾਲ ਮਜ਼ਬੂਤ ਸੰਬੰਧ ਬਣਾਉਣ ਲਈ ਇਹ ਨਾਮ ਤਿਆਰ ਕੀਤਾ ਗਿਆ ਹੈ।",
            "ਇਹ ਨਾਮ ਨਵੇਂ ਵਿਚਾਰਾਂ ਅਤੇ ਕਾਰੋਬਾਰੀ ਵਿਕਾਸ ਨੂੰ ਦਰਸਾਉਂਦਾ ਹੈ।",
            "ਇਹ ਬ੍ਰਾਂਡ ਪਛਾਣ ਗੁਣਵੱਤਾ, ਤਾਕਤ ਅਤੇ ਵਿਲੱਖਣਤਾ ਦਰਸਾਉਂਦੀ ਹੈ।"
        ],
        "taglines": [
            "ਤੁਹਾਡੇ ਸੁਪਨੇ ਦੀ ਨਵੀਂ ਪਛਾਣ।",
            "ਨਵੇਂ ਵਿਚਾਰਾਂ ਲਈ ਨਵੀਂ ਦਿਸ਼ਾ।",
            "ਤੁਹਾਡੇ ਬ੍ਰਾਂਡ ਦੀ ਨਵੀਂ ਸ਼ੁਰੂਆਤ।",
            "ਵਿਚਾਰ ਤੋਂ ਸਫਲਤਾ ਤੱਕ।",
            "ਤੁਹਾਡਾ ਸੁਪਨਾ, ਸਾਡੀ ਪ੍ਰੇਰਣਾ।"
        ]
    },

    "urdu": {
        "prefix": [
            "نیا", "نور", "کامیاب", "روشن", "تخلیق",
            "امید", "طاقت", "خوش", "عروج", "شاندار",
            "ترقی", "اعتماد", "خواب", "برکت", "نقش"
        ],
        "suffix": [
            "فن", "روشنی", "جہان", "لہریں", "طاقت",
            "نظر", "راستہ", "دنیا", "ترقی", "کمال",
            "دائرہ", "آواز", "سفر", "مقام", "نگاہ"
        ],
        "meanings": [
            "یہ نام نئی سوچ، تخلیقی صلاحیت اور کامیابی کی علامت ہے۔",
            "یہ برانڈ نام جدیدیت، اعتماد اور ترقی کی نمائندگی کرتا ہے۔",
            "یہ نام صارفین کے ساتھ مضبوط تعلق پیدا کرنے کے لیے بنایا گیا ہے۔",
            "یہ نام نئے خیالات اور کاروباری ترقی کو ظاہر کرتا ہے۔",
            "یہ برانڈ شناخت معیار، طاقت اور انفرادیت کو ظاہر کرتی ہے۔"
        ],
        "taglines": [
            "آپ کے خواب کی نئی پہچان۔",
            "نئے خیالات کے لیے نئی راہ۔",
            "آپ کے برانڈ کی نئی شروعات۔",
            "خیال سے کامیابی تک۔",
            "آپ کا خواب، ہماری تحریک۔"
        ]
    },

    "french": {
        "prefix": [
            "Belle", "Nova", "Élan", "Lumi", "Viva",
            "Clair", "Étoile", "Brio", "Pure", "Aube",
            "Éclat", "Fleur", "Rêve", "Force", "Serein"
        ],
        "suffix": [
            "ora", "vie", "elle", "ique", "ia",
            "éa", "is", "on", "elle", "ova",
            "ance", "ine", "ora", "éto", "art"
        ],
        "meanings": [
            "Un nom élégant qui représente la créativité et l'innovation.",
            "Une identité moderne conçue pour créer une connexion forte avec le public.",
            "Un nom distinctif qui évoque la qualité, la confiance et la croissance.",
            "Une identité créative adaptée aux entreprises modernes.",
            "Un concept de marque qui combine élégance et innovation."
        ],
        "taglines": [
            "Donnez vie à vos idées.",
            "Votre marque, votre histoire.",
            "L'innovation avec élégance.",
            "Des idées qui inspirent.",
            "Construisez votre identité."
        ]
    },

    "german": {
        "prefix": [
            "Neu", "Kraft", "Licht", "Wert", "Stark",
            "Glanz", "Zukunft", "Wunder", "Klar", "Mut",
            "Erfolg", "Idee", "Frei", "Hoch", "Stern"
        ],
        "suffix": [
            "werk", "kraft", "haus", "blick", "welt",
            "fluss", "raum", "punkt", "weg", "stern",
            "kraft", "idee", "raum", "licht", "brand"
        ],
        "meanings": [
            "Ein moderner Markenname, der Innovation und Stärke vermittelt.",
            "Eine klare Markenidentität für moderne und ambitionierte Unternehmen.",
            "Ein einzigartiger Name, der Vertrauen, Qualität und Wachstum ausdrückt.",
            "Ein kreatives Markenkonzept für ein modernes Publikum.",
            "Eine starke Identität, die Innovation und Zukunft verbindet."
        ],
        "taglines": [
            "Ideen mit Zukunft.",
            "Ihre Marke. Ihre Geschichte.",
            "Starke Ideen, starke Marken.",
            "Innovation mit Charakter.",
            "Die Zukunft Ihrer Marke."
        ]
    },

    "italian": {
        "prefix": [
            "Nova", "Bella", "Viva", "Luce", "Forte",
            "Sole", "Arte", "Vero", "Brio", "Nuova",
            "Stella", "Dolce", "Crea", "Sogno", "Puro"
        ],
        "suffix": [
            "vita", "ora", "bella", "luna", "forma",
            "vento", "mondo", "stile", "vero", "fiore",
            "arte", "luce", "linea", "onda", "casa"
        ],
        "meanings": [
            "Un nome che rappresenta creatività, eleganza e innovazione.",
            "Un'identità moderna pensata per creare una connessione con il pubblico.",
            "Un nome distintivo che comunica qualità, fiducia e crescita.",
            "Un'identità creativa per aziende moderne e ambiziose.",
            "Un concetto di brand che combina stile e innovazione."
        ],
        "taglines": [
            "Dai vita alle tue idee.",
            "La tua marca, la tua storia.",
            "Innovazione con stile.",
            "Idee che fanno la differenza.",
            "Costruisci il tuo futuro."
        ]
    },

    "spanish": {
        "prefix": [
            "Nueva", "Brillo", "Viva", "Luz", "Fuerte",
            "Bella", "Crea", "Sol", "Esperanza", "Valor",
            "Estrella", "Sueño", "Claro", "Éxito", "Fresco"
        ],
        "suffix": [
            "vida", "arte", "mundo", "onda", "flujo",
            "luz", "forma", "casa", "punto", "alma",
            "nova", "cielo", "vista", "camino", "fuerza"
        ],
        "meanings": [
            "Un nombre que representa creatividad, innovación y crecimiento.",
            "Una identidad moderna creada para conectar con el público.",
            "Un nombre distintivo que comunica calidad y confianza.",
            "Una marca creativa diseñada para negocios modernos.",
            "Un concepto de marca que combina innovación y personalidad."
        ],
        "taglines": [
            "Da vida a tus ideas.",
            "Tu marca, tu historia.",
            "Innovación que inspira.",
            "Ideas que transforman.",
            "Construye tu identidad."
        ]
    },

    "portuguese": {
        "prefix": [
            "Nova", "Brilho", "Viva", "Luz", "Forte",
            "Bela", "Criativa", "Sol", "Esperança", "Valor",
            "Estrela", "Sonho", "Claro", "Sucesso", "Livre"
        ],
        "suffix": [
            "vida", "arte", "mundo", "onda", "fluxo",
            "luz", "forma", "casa", "ponto", "alma",
            "nova", "céu", "vista", "caminho", "força"
        ],
        "meanings": [
            "Um nome que representa criatividade, inovação e crescimento.",
            "Uma identidade moderna criada para conectar com o público.",
            "Um nome distinto que transmite qualidade e confiança.",
            "Uma marca criativa desenvolvida para negócios modernos.",
            "Um conceito de marca que combina inovação e personalidade."
        ],
        "taglines": [
            "Dê vida às suas ideias.",
            "Sua marca, sua história.",
            "Inovação que inspira.",
            "Ideias que transformam.",
            "Construa sua identidade."
        ]
    },

    "russian": {
        "prefix": [
            "Нова", "Свет", "Сила", "Мир", "Вектор",
            "Успех", "Твор", "Звезда", "Эко", "Радуга",
            "Новый", "Вдох", "Мечта", "Рост", "Яркий"
        ],
        "suffix": [
            "сфера", "мир", "сила", "свет", "путь",
            "дом", "поток", "волна", "центр", "арт",
            "линия", "пространство", "вектор", "идея", "пик"
        ],
        "meanings": [
            "Название отражает творчество, инновации и рост.",
            "Современная идентичность для амбициозного бизнеса.",
            "Уникальное имя, создающее ощущение качества и доверия.",
            "Креативная концепция бренда для современной аудитории.",
            "Сильная идентичность, объединяющая инновации и развитие."
        ],
        "taglines": [
            "Новая идея. Новый бренд.",
            "Создаём будущее вместе.",
            "Ваш бренд — ваша история.",
            "Идеи, которые вдохновляют.",
            "От идеи к успеху."
        ]
    },

    "japanese": {
        "prefix": [
            "未来", "新", "光", "夢", "空",
            "星", "和", "創", "輝", "希望",
            "未来", "明", "心", "結", "花"
        ],
        "suffix": [
            "光", "風", "波", "空", "道",
            "心", "結", "彩", "創", "未来",
            "星", "花", "夢", "輪", "空間"
        ],
        "meanings": [
            "新しい価値と創造性を表現するブランド名です。",
            "未来への成長と革新を感じさせる名前です。",
            "品質と信頼、そして独自性を表現するブランドです。",
            "現代的なビジネスと若い世代に合う名前です。",
            "新しいアイデアと未来への可能性を象徴しています。"
        ],
        "taglines": [
            "未来をブランドに。",
            "あなたの想いを形に。",
            "新しい価値を創造する。",
            "夢から未来へ。",
            "アイデアを力に変える。"
        ]
    },

    "korean": {
        "prefix": [
            "새", "빛", "꿈", "미래", "희망",
            "창조", "성공", "푸른", "별", "강한",
            "새로운", "성장", "맑은", "행복", "열정"
        ],
        "suffix": [
            "빛", "길", "세상", "마음", "물결",
            "미래", "공간", "힘", "별", "창",
            "꿈", "봄", "온", "결", "나래"
        ],
        "meanings": [
            "새로운 아이디어와 창의성을 표현하는 브랜드 이름입니다.",
            "성장과 혁신을 상징하는 현대적인 브랜드 이름입니다.",
            "품질과 신뢰, 독창성을 표현하는 이름입니다.",
            "현대적인 비즈니스와 젊은 고객에게 적합한 이름입니다.",
            "새로운 가능성과 미래를 상징하는 브랜드입니다."
        ],
        "taglines": [
            "당신의 꿈을 브랜드로.",
            "새로운 생각, 새로운 시작.",
            "당신의 브랜드, 당신의 이야기.",
            "아이디어를 현실로.",
            "미래를 만드는 브랜드."
        ]
    },

    "arabic": {
        "prefix": [
            "نور", "نوفا", "أمل", "قوة", "إبداع",
            "نجاح", "رؤية", "مجد", "صفا", "بريق",
            "نجم", "حياة", "فكر", "نمو", "روعة"
        ],
        "suffix": [
            "نور", "فن", "عالم", "موجة", "أفق",
            "قمة", "روح", "نجاح", "رؤية", "إبداع",
            "حياة", "طريق", "نبض", "بداية", "أمل"
        ],
        "meanings": [
            "اسم يعكس الإبداع والابتكار والنمو.",
            "هوية حديثة مصممة للتواصل مع الجمهور.",
            "اسم مميز يعبر عن الجودة والثقة.",
            "علامة إبداعية مناسبة للأعمال الحديثة.",
            "فكرة علامة تجارية تجمع بين الابتكار والشخصية."
        ],
        "taglines": [
            "حوّل فكرتك إلى هوية.",
            "علامتك، قصتك.",
            "ابتكار يصنع الفرق.",
            "من الفكرة إلى النجاح.",
            "اصنع مستقبلك بعلامتك."
        ]
    },

    "chinese": {
        "prefix": [
            "新", "光", "星", "梦", "创",
            "智", "未来", "华", "优", "瑞",
            "明", "悦", "云", "远", "盛"
        ],
        "suffix": [
            "光", "创", "空间", "力量", "未来",
            "视界", "动力", "天地", "无限", "星",
            "梦", "源", "云", "峰", "意"
        ],
        "meanings": [
            "这个名字代表创新、创造力和成长。",
            "这个品牌名称体现现代感、信任和品质。",
            "这个名字旨在与目标客户建立强烈的情感联系。",
            "这个名字代表新的想法和商业发展。",
            "这个品牌形象体现独特性、活力和创新。"
        ],
        "taglines": [
            "让品牌成就梦想。",
            "创新成就未来。",
            "你的品牌，你的故事。",
            "从创意走向成功。",
            "让每个想法发光。"
        ]
    }
}


LANGUAGE_ALIASES = {
    "en": "english",
    "english": "english",

    "te": "telugu",
    "telugu": "telugu",

    "hi": "hindi",
    "hindi": "hindi",

    "mr": "marathi",
    "marathi": "marathi",

    "ta": "tamil",
    "tamil": "tamil",

    "kn": "kannada",
    "kannada": "kannada",

    "ml": "malayalam",
    "malayalam": "malayalam",

    "bn": "bengali",
    "bengali": "bengali",

    "gu": "gujarati",
    "gujarati": "gujarati",

    "pa": "punjabi",
    "punjabi": "punjabi",

    "ur": "urdu",
    "urdu": "urdu",

    "fr": "french",
    "french": "french",

    "de": "german",
    "german": "german",

    "es": "spanish",
    "spanish": "spanish",

    "it": "italian",
    "italian": "italian",

    "pt": "portuguese",
    "portuguese": "portuguese",

    "ru": "russian",
    "russian": "russian",

    "ja": "japanese",
    "japanese": "japanese",

    "ko": "korean",
    "korean": "korean",

    "ar": "arabic",
    "arabic": "arabic",

    "zh": "chinese",
    "chinese": "chinese"
}


def normalize_language(language: str) -> str:
    value = language.lower().strip()
    return LANGUAGE_ALIASES.get(value, "english")


def make_domain_name(name: str) -> str:
    value = name.lower()

    value = re.sub(r"[^a-zA-Z0-9]", "", value)

    if not value:
        value = "brand"

    return value


def generate_dummy_brands(req: BrandRequest):
    """
    Local multilingual fallback.

    Used when Gemini is unavailable, rate limited, or returns
    an invalid response.
    """

    lang = normalize_language(req.preferred_language)

    info = LANGUAGE_DATA[lang]

    combinations = [
        (prefix, suffix)
        for prefix in info["prefix"]
        for suffix in info["suffix"]
    ]

    random.shuffle(combinations)

    brands = []
    used_names = set()

    for prefix, suffix in combinations:

        if len(brands) >= 10:
            break

        name = f"{prefix}{suffix}"

        normalized_name = name.lower()

        if normalized_name in used_names:
            continue

        used_names.add(normalized_name)

        meaning = random.choice(info["meanings"])
        tagline = random.choice(info["taglines"])

        domain_name = make_domain_name(name)

        domains = [
            f"{domain_name}.com",
            f"{domain_name}.co",
            f"{domain_name}.io"
        ]

        brands.append({
            "name": name,
            "meaning": meaning,
            "tagline": tagline,
            "domains": domains
        })

    return {"brands": brands}


# ============================================================
# GEMINI CONFIGURATION
# ============================================================

if HAS_GEMINI_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


# ============================================================
# BRAND NAME GENERATION
# ============================================================

@router.post("/names", response_model=BrandResponse)
def generate_names(
    req: BrandRequest,
    current_user: User = Depends(get_current_user)
):

    missing = []

    if not req.business_type:
        missing.append("business_type")

    if not req.industry:
        missing.append("industry")

    if not req.target_audience:
        missing.append("target_audience")

    if not req.brand_personality:
        missing.append("brand_personality")

    if not req.preferred_language:
        missing.append("preferred_language")

    if not req.country:
        missing.append("country")

    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields: {', '.join(missing)}"
        )

    # --------------------------------------------------------
    # If Gemini key is unavailable, use multilingual fallback
    # --------------------------------------------------------

    if not HAS_GEMINI_KEY:

        logger.warning(
            "Gemini API key unavailable. Using multilingual local generator."
        )

        return generate_dummy_brands(req)

    # --------------------------------------------------------
    # Gemini prompt
    # --------------------------------------------------------

    prompt = f"""
You are BrandCraft AI, an expert multilingual branding consultant.

The user selected:

Preferred Language: {req.preferred_language}
Business Type: {req.business_type}
Industry: {req.industry}
Target Audience: {req.target_audience}
Brand Personality: {req.brand_personality}
Target Country: {req.country}

LANGUAGE REQUIREMENT:
You MUST respect the selected language.

Generate the brand names specifically for "{req.preferred_language}".

If the selected language is Telugu, generate Telugu-inspired names.
If Hindi, generate Hindi-inspired names.
If Marathi, generate Marathi-inspired names.
If Tamil, generate Tamil-inspired names.
If Kannada, generate Kannada-inspired names.
If Malayalam, generate Malayalam-inspired names.
If Bengali, generate Bengali-inspired names.
If Gujarati, generate Gujarati-inspired names.
If Punjabi, generate Punjabi-inspired names.
If Urdu, generate Urdu-inspired names.
If French, generate French-inspired names.
If German, generate German-inspired names.
If Spanish, generate Spanish-inspired names.
If Italian, generate Italian-inspired names.
If Portuguese, generate Portuguese-inspired names.
If Russian, generate Russian-inspired names.
If Japanese, generate Japanese-inspired names.
If Korean, generate Korean-inspired names.
If Arabic, generate Arabic-inspired names.
If Chinese, generate Chinese-inspired names.

DO NOT simply generate English names and translate their meanings.

DO NOT repeatedly use names such as:
Nova, Bright, Prime, Bold, Fresh, Vivid, Apex, etc.
unless English is the selected language.

Every name must be different and creatively related to the selected language.

The names should feel like REAL BRAND NAMES rather than ordinary dictionary words.

Use combinations, word blends, cultural inspiration, phonetic creativity,
meaningful roots, and modern naming techniques.

Generate EXACTLY 10 UNIQUE names.

For every name provide:

1. name
2. meaning
3. tagline
4. domains

The meaning MUST be written in {req.preferred_language}.

The tagline MUST be written in {req.preferred_language}.

The name should primarily use {req.preferred_language}.

For languages using non-Latin scripts, native script is preferred.
A tasteful romanized name is allowed when appropriate, but it must still
be inspired by the selected language.

Domain suggestions should use lowercase ASCII transliteration where possible.

Return ONLY valid JSON.

Required JSON structure:

{{
    "brands": [
        {{
            "name": "brand name",
            "meaning": "meaning in selected language",
            "tagline": "tagline in selected language",
            "domains": [
                "brandname.com",
                "brandname.co",
                "brandname.io"
            ]
        }}
    ]
}}
"""

    # --------------------------------------------------------
    # Gemini request
    # --------------------------------------------------------

    try:

        model_names = [
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
            "gemini-2.0-flash"
        ]

        response = None
        last_error = None

        for model_name in model_names:

            try:

                logger.info(
                    f"Trying Gemini model: {model_name}"
                )

                model = genai.GenerativeModel(
                    model_name=model_name
                )

                response = model.generate_content(
                    prompt,
                    generation_config={
                        "response_mime_type": "application/json",
                        "temperature": 0.9
                    }
                )

                if response and response.text:
                    break

            except Exception as model_error:

                last_error = model_error

                logger.warning(
                    f"Gemini model {model_name} failed: {model_error}"
                )

        # ----------------------------------------------------
        # If all Gemini models failed
        # ----------------------------------------------------

        if response is None or not response.text:

            logger.warning(
                f"All Gemini models failed: {last_error}"
            )

            return generate_dummy_brands(req)

        # ----------------------------------------------------
        # Parse JSON safely
        # ----------------------------------------------------

        response_text = response.text.strip()

        # Remove markdown JSON fences if Gemini returns them
        response_text = re.sub(
            r"^```json\s*",
            "",
            response_text,
            flags=re.IGNORECASE
        )

        response_text = re.sub(
            r"^```\s*",
            "",
            response_text
        )

        response_text = re.sub(
            r"\s*```$",
            "",
            response_text
        )

        try:

            result = json.loads(response_text)

        except json.JSONDecodeError:

            # Try extracting JSON object
            match = re.search(
                r"\{.*\}",
                response_text,
                re.DOTALL
            )

            if match:
                result = json.loads(match.group(0))
            else:
                raise ValueError(
                    "Gemini returned invalid JSON."
                )

        # ----------------------------------------------------
        # Validate result
        # ----------------------------------------------------

        if (
            not isinstance(result, dict)
            or "brands" not in result
            or not isinstance(result["brands"], list)
        ):
            raise ValueError(
                "Invalid Gemini response format."
            )

        # ----------------------------------------------------
        # Clean and remove duplicate names
        # ----------------------------------------------------

        unique_brands = []
        seen_names = set()

        for brand in result["brands"]:

            if not isinstance(brand, dict):
                continue

            name = str(
                brand.get("name", "")
            ).strip()

            meaning = str(
                brand.get("meaning", "")
            ).strip()

            tagline = str(
                brand.get("tagline", "")
            ).strip()

            domains = brand.get(
                "domains",
                []
            )

            if not name:
                continue

            normalized = name.lower()

            if normalized in seen_names:
                continue

            seen_names.add(normalized)

            if not isinstance(domains, list):
                domains = []

            domains = [
                str(domain).strip()
                for domain in domains
                if str(domain).strip()
            ]

            # Guarantee 3 domains
            if len(domains) < 3:

                domain_name = make_domain_name(name)

                default_domains = [
                    f"{domain_name}.com",
                    f"{domain_name}.co",
                    f"{domain_name}.io"
                ]

                for domain in default_domains:

                    if domain not in domains:
                        domains.append(domain)

                    if len(domains) >= 3:
                        break

            unique_brands.append({
                "name": name,
                "meaning": meaning,
                "tagline": tagline,
                "domains": domains[:3]
            })

            if len(unique_brands) >= 10:
                break

        # ----------------------------------------------------
        # If Gemini produced too few names, use fallback
        # ----------------------------------------------------

        if len(unique_brands) < 10:

            logger.warning(
                "Gemini returned fewer than 10 usable names. "
                "Using multilingual fallback."
            )

            return generate_dummy_brands(req)

        return {
            "brands": unique_brands
        }

    except Exception as e:

        logger.error(
            f"Gemini brand generation failed: {e}"
        )

        # Always return useful multilingual results
        # instead of breaking the frontend.

        return generate_dummy_brands(req)


# ============================================================
# SAVE BRAND
# ============================================================

@router.post(
    "/save",
    response_model=SavedBrandResponse
)
def save_brand(
    brand_data: SavedBrandCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    db_brand = SavedBrand(
        user_id=current_user.id,
        brand_name=brand_data.brand_name,
        industry=brand_data.industry,
        target_audience=brand_data.target_audience,
        brand_meaning=brand_data.brand_meaning,
        tagline=brand_data.tagline,
        domain_suggestions=json.dumps(
            brand_data.domain_suggestions
        )
    )

    db.add(db_brand)
    db.commit()
    db.refresh(db_brand)

    return SavedBrandResponse(
        id=db_brand.id,
        brand_name=db_brand.brand_name,
        industry=db_brand.industry,
        target_audience=db_brand.target_audience,
        brand_meaning=db_brand.brand_meaning,
        tagline=db_brand.tagline,
        domain_suggestions=brand_data.domain_suggestions,
        created_at=db_brand.created_at
    )


# ============================================================
# GET SAVED BRANDS
# ============================================================

@router.get(
    "/saved",
    response_model=List[SavedBrandResponse]
)
def get_saved_brands(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    brands = (
        db.query(SavedBrand)
        .filter(
            SavedBrand.user_id == current_user.id
        )
        .all()
    )

    response_list = []

    for brand in brands:

        try:
            domains = json.loads(
                brand.domain_suggestions
            )
        except Exception:
            domains = []

        response_list.append(
            SavedBrandResponse(
                id=brand.id,
                brand_name=brand.brand_name,
                industry=brand.industry,
                target_audience=brand.target_audience,
                brand_meaning=brand.brand_meaning,
                tagline=brand.tagline,
                domain_suggestions=domains,
                created_at=brand.created_at
            )
        )

    return response_list


# ============================================================
# DELETE SAVED BRAND
# ============================================================

@router.delete(
    "/saved/{brand_id}"
)
def delete_saved_brand(
    brand_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    brand = (
        db.query(SavedBrand)
        .filter(
            SavedBrand.id == brand_id,
            SavedBrand.user_id == current_user.id
        )
        .first()
    )

    if not brand:
        raise HTTPException(
            status_code=404,
            detail="Saved brand not found"
        )

    db.delete(brand)
    db.commit()

    return {
        "message": "Brand deleted successfully"
    }