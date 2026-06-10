import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.schemas import ChatRequest, ChatResponse, ChatMessage
from backend.app.auth import get_current_user
from backend.app.models import User, ChatMessageDB
from backend.app.config import GEMINI_API_KEY, HAS_GEMINI_KEY
import google.generativeai as genai

router = APIRouter(prefix="/api/assistant", tags=["assistant"])
logger = logging.getLogger(__name__)

# Configure Gemini if key is present
if HAS_GEMINI_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# List of branding keywords to validate prompt in fallback and system guidance
BRANDING_KEYWORDS = [
    "brand", "logo", "marketing", "content", "slogan", "tagline", "story", "identity",
    "business", "startup", "target", "audience", "positioning", "ad", "email",
    "social", "media", "caption", "name", "colors", "font", "strategy", "campaign",
    "product", "sales", "niche", "customer", "sentiment", "review"
]

def fallback_chat_response(prompt: str) -> str:
    """Procedural chatbot response logic for local testing without API keys."""
    prompt_lower = prompt.lower().strip().rstrip(".!?")
    
    # 1. Greetings
    greetings = ["hello", "hi", "hey", "hola", "howdy", "greetings", "good morning", "good afternoon", "good evening", "yo"]
    is_greeting = any(g == prompt_lower or prompt_lower.startswith(g + " ") or prompt_lower.startswith(g + ",") for g in greetings)
    if is_greeting:
        return (
            "Hello! I am your BrandCraft AI Assistant. I specialize in branding, marketing, content automation, logo design rules, and business strategy.\n\n"
            "How can I assist you with your brand guidelines today? Ask me about color psychology, fonts, naming tips, or social media writing!"
        )
        
    # 2. Identity / Who are you
    if any(x in prompt_lower for x in ["who are you", "what is your name", "your name", "who created you", "what are you"]):
        return (
            "I am the BrandCraft AI Assistant, your dedicated brand identity and marketing consultant. "
            "I was created to help startups, entrepreneurs, and creators build their complete brand presence. "
            "I can guide you through choosing brand names, logo aesthetics, slogans, and marketing campaigns. How can I help you today?"
        )
        
    # 3. Capabilities / What can you do
    if any(x in prompt_lower for x in ["what can you do", "features", "capabilities", "how can you help", "help me"]):
        return (
            "I can assist you with all aspects of brand building and identity design, including:\n\n"
            "1. **Brand Names**: Brainstorming names with taglines and domains.\n"
            "2. **Logo Design**: Recommending colors, typography, styles, and blueprints.\n"
            "3. **Content Writing**: Drafting slogans, brand stories, product copy, emails, and ads.\n"
            "4. **Sentiment Tracking**: Analyzing customer feedback metrics.\n\n"
            "Just ask me a question about any of these topics!"
        )
        
    # 4. Smalltalk / How are you
    if any(x in prompt_lower for x in ["how are you", "how is it going", "how are you doing"]):
        return (
            "I'm doing great, thank you! I'm fully charged and ready to brainstorm branding ideas with you. "
            "What business or brand are we working on today?"
        )
        
    # 5. Gratitude / Thank you
    if any(x in prompt_lower for x in ["thank you", "thanks", "appreciate", "helpful"]):
        return (
            "You are very welcome! Helping you build a strong brand is what I do best. "
            "Let me know if you need to refine your logo ideas, write product descriptions, or analyze review sentiments!"
        )
        
    # Check if the prompt is related to branding
    is_related = any(keyword in prompt_lower for keyword in BRANDING_KEYWORDS)
    
    if not is_related:
        return "I specialize in branding and marketing assistance. Please ask a branding-related question."
        
    # Smart keyword mappings for rich customized replies
    if "color" in prompt_lower:
        return (
            "Color psychology is a powerful tool in branding! Here are some recommended color systems:\n\n"
            "1. **Luxury & Upscale**: Charcoal, deep burgundy, and metallic gold accents.\n"
            "2. **Tech & Innovations**: Deep navy blue, digital teal, and clean slate gray.\n"
            "3. **Wellness & Organic**: Sage green, warm peach, sand white, and earth brown.\n"
            "4. **Youthful & Bold**: Vibrant coral pink, sunny yellow, and deep purple highlights.\n\n"
            "Use our Logo Generator and select matching color themes to preview these styles!"
        )
    elif "font" in prompt_lower or "typography" in prompt_lower:
        return (
            "Typography sets the emotional tone of your corporate identity:\n\n"
            "- **Serif Fonts (e.g., Georgia, Playfair)**: Connote luxury, tradition, authority, and editorial prestige. Ideal for fashion, law, and high-end goods.\n"
            "- **Sans-Serif Fonts (e.g., Calibri, Arial, Inter)**: Feel modern, clean, efficient, and direct. Great for tech, startups, and mobile apps.\n"
            "- **Slab Serifs (e.g., Rockwell)**: Bold, strong, and mechanical. Excellent for hardware, outdoors, and engineering brands."
        )
    elif "logo" in prompt_lower:
        return (
            "A great logo should be simple, memorable, and versatile (scaling from a tiny favicon to a huge billboard):\n\n"
            "1. **Minimal**: Excellent for modern corporate messaging. Focuses on simple shapes and negative space.\n"
            "2. **Luxury Badge**: Uses geometric borders (circles/shields) and monograms (initials like BC).\n"
            "3. **Tech Circuits**: Blends abstract connection lines representing innovation and digital flow.\n\n"
            "Generate a batch in our **Logo Generator** and download them as PNG, JPG, or PDF spec sheets."
        )
    elif "positioning" in prompt_lower or "strategy" in prompt_lower:
        return (
            "Brand positioning defines how you stand out from competitors. Key elements to establish:\n\n"
            "1. **Target Persona**: Who is your dream user? Define their age, goals, and core frustrations.\n"
            "2. **Unique Value Proposition (UVP)**: What do you do better than anyone else?\n"
            "3. **Emotional Hook**: Why should they care? (e.g. peace of mind, status, saved time)."
        )
    elif "name" in prompt_lower:
        return (
            "Choosing a brand name is crucial! It should be pronounceable, distinctive, and have available domains.\n\n"
            "Use our **Brand Name Generator** on the dashboard. Specify your target country, industry, and Preferred Language (Hindi, Spanish, Telugu, French, etc.) to get 30+ tailored names with matching taglines and domain ideas."
        )
    elif "slogan" in prompt_lower or "tagline" in prompt_lower:
        return (
            "A tagline should tell the customer what benefit they receive, in under 5 words. Emotional taglines like 'Think Different' (Apple) "
            "or functional taglines like 'The World's Local Bank' (HSBC) are great patterns.\n\n"
            "You can generate 50+ slogans simultaneously in the **Content Automation** dashboard."
        )
    elif "story" in prompt_lower or "about" in prompt_lower:
        return (
            "Every brand needs a compelling story. Use the 'Hero's Journey' formula: "
            "1. **The Conflict**: The customer's pain point. "
            "2. **The Guide**: Your brand showing up with a plan. "
            "3. **The Success**: The positive outcome. "
            "You can generate 10 unique brand stories in the Content Automation tab."
        )
    elif "sentiment" in prompt_lower or "review" in prompt_lower:
        return (
            "Tracking reviews helps evaluate whether your branding is working. In our **Sentiment Analysis** tab, "
            "paste customer reviews to track positive/negative feedback, extract keywords, and diagnose specific emotions "
            "(Happy, Excited, Satisfied vs. Angry, Frustrated)."
        )
    else:
        return (
            "Hello! I am your BrandCraft AI Assistant. I specialize in branding, marketing, content automation, logo design rules, and business strategy.\n\n"
            "How can I assist you with your brand guidelines today? Ask me about color psychology, fonts, naming tips, or social media writing!"
        )

@router.post("/chat", response_model=ChatResponse)
def chat_assistant(req: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_message = req.message.strip()
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
        
    # Topic pre-filtering (satisfies IPL rules instantly before calling external API)
    user_message_lower = user_message.lower().strip().rstrip(".!?")
    greetings = ["hello", "hi", "hey", "hola", "howdy", "greetings", "good morning", "good afternoon", "good evening", "yo"]
    is_greeting = any(g == user_message_lower or user_message_lower.startswith(g + " ") or user_message_lower.startswith(g + ",") for g in greetings)
    
    # Pre-filtering update: Allow capability queries, identity, smalltalk, and gratitude keywords
    allowed_smalltalk = [
        "who are you", "what is your name", "your name", "who created you", "what are you", 
        "what can you do", "features", "capabilities", "how can you help", "help me", 
        "how are you", "how is it going", "how are you doing", "thank you", "thanks", 
        "appreciate", "helpful", "what model", "which model"
    ]
    is_smalltalk = any(x in user_message_lower for x in allowed_smalltalk)
    is_related = is_greeting or is_smalltalk or any(keyword in user_message_lower for keyword in BRANDING_KEYWORDS)
    
    # Check common unrelated questions directly to guarantee correct response
    if not is_related or any(x in user_message_lower for x in ["ipl", "cricket", "who won", "weather", "recipe", "coding", "code python"]):
        return ChatResponse(message="I specialize in branding and marketing assistance. Please ask a branding-related question.")

    # Save User message to persistent history in DB
    try:
        db_user_msg = ChatMessageDB(user_id=current_user.id, sender="user", message=user_message)
        db.add(db_user_msg)
        db.commit()
    except Exception as db_err:
        logger.error(f"Failed to save user message to DB: {db_err}")

    # Generate reply
    if not HAS_GEMINI_KEY:
        reply = fallback_chat_response(user_message)
    else:
        # Construct conversation context for Gemini
        system_instruction = (
            "You are BrandCraft AI Assistant, a professional branding, marketing, and business identity consultant. "
            "You must ONLY answer questions related to branding, logo design, taglines, marketing strategies, business identity, "
            "startup advice, social media copy, and audience research. "
            "If the user asks an unrelated question (such as sports, news, cooking, weather, math, general programming), you MUST "
            "respond exactly with: 'I specialize in branding and marketing assistance. Please ask a branding-related question.' "
            "Keep your branding answers extremely concise, direct, professional, encouraging, and clear. Avoid wordiness to maximize response speed."
        )
        
        try:
            model_name = "gemini-2.5-flash-lite"
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=system_instruction
                )
                contents = []
                for msg in req.history[-10:]:
                    role = "user" if msg.sender == "user" else "model"
                    contents.append({"role": role, "parts": [msg.message]})
                contents.append({"role": "user", "parts": [user_message]})
                response = model.generate_content(contents)
                reply = response.text
            except Exception as model_err:
                logger.warning(f"Gemini chat with {model_name} failed: {model_err}. Trying gemini-2.5-flash...")
                model_name = "gemini-2.5-flash"
                try:
                    model = genai.GenerativeModel(
                        model_name=model_name,
                        system_instruction=system_instruction
                    )
                    contents = []
                    for msg in req.history[-10:]:
                        role = "user" if msg.sender == "user" else "model"
                        contents.append({"role": role, "parts": [msg.message]})
                    contents.append({"role": "user", "parts": [user_message]})
                    response = model.generate_content(contents)
                    reply = response.text
                except Exception as model_err2:
                    logger.warning(f"Gemini chat with {model_name} failed: {model_err2}. Trying gemini-2.0-flash...")
                    model = genai.GenerativeModel(
                        model_name="gemini-2.0-flash",
                        system_instruction=system_instruction
                    )
                    contents = []
                    for msg in req.history[-10:]:
                        role = "user" if msg.sender == "user" else "model"
                        contents.append({"role": role, "parts": [msg.message]})
                    contents.append({"role": "user", "parts": [user_message]})
                    response = model.generate_content(contents)
                    reply = response.text
            
        except Exception as e:
            logger.error(f"Gemini chat failed: {e}. Using fallback.")
            reply = fallback_chat_response(user_message)

    # Save Assistant reply to persistent history in DB
    try:
        db_assistant_msg = ChatMessageDB(user_id=current_user.id, sender="assistant", message=reply)
        db.add(db_assistant_msg)
        db.commit()
    except Exception as db_err:
        logger.error(f"Failed to save assistant response to DB: {db_err}")

    return ChatResponse(message=reply)

@router.get("/history", response_model=List[ChatMessage])
def get_chat_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Retrieves all past chat messages for the current user."""
    try:
        messages = db.query(ChatMessageDB).filter(
            ChatMessageDB.user_id == current_user.id
        ).order_by(ChatMessageDB.created_at.asc()).all()
        return [ChatMessage(sender=m.sender, message=m.message) for m in messages]
    except Exception as e:
        logger.error(f"Failed to fetch chat history: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

@router.delete("/history")
def clear_chat_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Deletes all chat messages for the current user."""
    try:
        db.query(ChatMessageDB).filter(ChatMessageDB.user_id == current_user.id).delete()
        db.commit()
        return {"message": "Chat history cleared successfully"}
    except Exception as e:
        logger.error(f"Failed to clear chat history: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
