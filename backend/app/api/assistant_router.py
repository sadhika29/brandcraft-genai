import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ChatRequest, ChatResponse, ChatMessage
from app.auth import get_current_user
from app.models import User, ChatMessageDB
from app.config import GEMINI_API_KEY, HAS_GEMINI_KEY

import google.generativeai as genai


router = APIRouter(prefix="/api/assistant", tags=["assistant"])
logger = logging.getLogger(__name__)


# Configure Gemini
if HAS_GEMINI_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


# ---------------------------------------------------------
# BRANDING TOPICS
# ---------------------------------------------------------

BRANDING_TERMS = [
    "brand",
    "branding",
    "brand identity",
    "brand image",
    "brand voice",
    "brand personality",
    "brand values",
    "brand guidelines",
    "brand awareness",
    "brand recognition",
    "brand loyalty",
    "brand trust",
    "brand positioning",
    "brand strategy",
    "brand architecture",
    "brand story",
    "brand name",
    "business name",
    "company name",
    "startup",
    "business",
    "company",
    "product",
    "service",
    "customer",
    "customers",
    "audience",
    "target audience",
    "customer persona",
    "buyer persona",
    "consumer",
    "market",
    "marketing",
    "market research",
    "market positioning",
    "competitor",
    "competition",
    "competitive advantage",
    "unique selling proposition",
    "usp",
    "value proposition",
    "logo",
    "logos",
    "icon",
    "symbol",
    "visual identity",
    "design",
    "graphic",
    "color",
    "colors",
    "colour",
    "colours",
    "color psychology",
    "typography",
    "font",
    "fonts",
    "lettering",
    "slogan",
    "tagline",
    "catchphrase",
    "brand message",
    "messaging",
    "copywriting",
    "copy",
    "content",
    "content marketing",
    "social media",
    "instagram",
    "facebook",
    "linkedin",
    "youtube",
    "twitter",
    "caption",
    "captions",
    "post",
    "posts",
    "reel",
    "reels",
    "advertisement",
    "advertising",
    "ad",
    "ads",
    "campaign",
    "campaigns",
    "promotion",
    "promotions",
    "marketing campaign",
    "email marketing",
    "email",
    "newsletter",
    "sales",
    "lead",
    "leads",
    "conversion",
    "engagement",
    "growth",
    "launch",
    "product launch",
    "customer experience",
    "customer feedback",
    "review",
    "reviews",
    "sentiment",
    "reputation",
    "trust",
    "loyalty",
    "pricing",
    "premium",
    "luxury",
    "niche",
    "market segment",
    "segmentation",
    "retention",
    "awareness",
    "promotion",
    "influencer",
    "influencer marketing",
    "digital marketing",
    "online presence",
    "website",
    "landing page",
    "brand name generator",
    "logo design",
    "brand design",
    "brand colors",
    "brand fonts",
]


# ---------------------------------------------------------
# CLEARLY UNRELATED TOPICS
# ---------------------------------------------------------

UNRELATED_TERMS = [
    "ipl",
    "cricket",
    "football",
    "soccer",
    "basketball",
    "tennis",
    "match score",
    "sports",
    "weather",
    "temperature today",
    "recipe",
    "cooking",
    "movie",
    "movies",
    "actor",
    "actress",
    "politics",
    "election",
    "stock price",
    "share price",
    "cryptocurrency",
    "bitcoin",
    "math problem",
    "mathematics",
    "physics",
    "chemistry",
    "biology",
    "homework",
    "exam question",
    "programming",
    "python code",
    "javascript code",
    "java code",
    "c++ code",
    "coding problem",
    "debug my code",
    "write code",
    "leetcode",
    "medical",
    "medicine",
    "disease",
    "symptom",
    "diagnosis",
    "doctor",
    "legal advice",
    "lawyer",
    "political party",
]


# ---------------------------------------------------------
# HELPER: DETERMINE IF MESSAGE IS BRANDING RELATED
# ---------------------------------------------------------

def is_branding_question(text: str) -> bool:
    text = text.lower().strip()

    # Direct branding terms
    if any(term in text for term in BRANDING_TERMS):
        return True

    # Common branding/business questions that may not contain
    # an exact keyword from the list above.
    branding_patterns = [
        "how do i attract customers",
        "how can i attract customers",
        "how do i get more customers",
        "how can i get more customers",
        "how do i make people trust",
        "how can i make people trust",
        "how do i stand out",
        "how can i stand out",
        "how do i differentiate",
        "how can i differentiate",
        "how do i promote",
        "how can i promote",
        "how do i grow my business",
        "how can i grow my business",
        "how do i launch",
        "how can i launch",
        "how do i market",
        "how can i market",
        "how do i advertise",
        "how can i advertise",
        "how do i build an identity",
        "how can i build an identity",
        "how do i create an identity",
        "how can i create an identity",
        "how do i build awareness",
        "how can i build awareness",
        "how do i improve my business",
        "how can i improve my business",
        "how do i create a campaign",
        "how can i create a campaign",
        "how do i create content",
        "how can i create content",
        "how do i write an ad",
        "how can i write an ad",
        "how do i write a tagline",
        "how can i write a tagline",
        "how do i choose a name",
        "how can i choose a name",
        "how do i choose colors",
        "how can i choose colors",
        "how do i choose fonts",
        "how can i choose fonts",
        "what makes a good brand",
        "what makes a strong brand",
        "what makes a good logo",
        "what makes a strong logo",
        "what should my logo",
        "what should my brand",
        "how should my brand",
        "how should i position",
        "how should i market",
        "how should i promote",
        "how should i price",
    ]

    return any(pattern in text for pattern in branding_patterns)


# ---------------------------------------------------------
# FALLBACK BRANDING ANSWERS
# ---------------------------------------------------------

def fallback_chat_response(prompt: str) -> str:
    text = prompt.lower().strip()

    if any(
        x in text
        for x in [
            "hello",
            "hi",
            "hey",
            "hola",
            "good morning",
            "good afternoon",
            "good evening",
        ]
    ):
        return (
            "Hello! I am your BrandCraft AI Assistant. "
            "I can help with brand naming, positioning, logos, colors, "
            "taglines, marketing, content, social media, customer research, "
            "and business strategy. What branding challenge are you working on?"
        )

    if "who are you" in text or "what is your name" in text:
        return (
            "I am BrandCraft AI Assistant, your branding and marketing consultant. "
            "I help you develop brand names, positioning, visual identity, "
            "marketing strategies, taglines, content, campaigns, and customer-focused branding."
        )

    if "what can you do" in text or "capabilities" in text or "features" in text:
        return (
            "I can help you with:\n\n"
            "• Brand naming and name evaluation\n"
            "• Taglines and slogans\n"
            "• Logo concepts and design direction\n"
            "• Colors and color psychology\n"
            "• Fonts and typography\n"
            "• Brand positioning and USP\n"
            "• Target audience and customer personas\n"
            "• Marketing campaigns\n"
            "• Social media content and captions\n"
            "• Brand stories and messaging\n"
            "• Product launches and promotions\n"
            "• Customer reviews and brand sentiment\n"
            "• Business and growth strategy"
        )

    if "color" in text or "colour" in text:
        return (
            "Choose brand colors based on the emotion you want customers to associate with your business. "
            "Blue often communicates trust and professionalism, green suggests growth and natural values, "
            "red creates energy and urgency, purple can communicate creativity or premium positioning, "
            "and black can communicate sophistication. The best palette should also fit your audience, "
            "industry, competitors, and brand personality."
        )

    if "font" in text or "typography" in text:
        return (
            "Choose typography according to your brand personality. "
            "Serif fonts can communicate tradition, authority, and luxury. "
            "Sans-serif fonts usually feel modern, clean, and accessible. "
            "Display fonts can add personality but should be used carefully. "
            "For a professional brand system, use one primary font and one complementary font."
        )

    if "logo" in text:
        return (
            "A strong logo should be simple, memorable, relevant, scalable, and recognizable. "
            "Start with the brand's personality and audience rather than decorating the logo with too many elements. "
            "A good logo should work in color, black and white, on websites, social media, packaging, "
            "and small sizes such as a profile icon."
        )

    if "tagline" in text or "slogan" in text:
        return (
            "A strong tagline is short, memorable, distinctive, and connected to the brand's value. "
            "Instead of simply describing the product, communicate the benefit or feeling customers should associate "
            "with the brand. Aim for a phrase that is easy to say, remember, and use consistently."
        )

    if "name" in text:
        return (
            "A strong brand name should be distinctive, easy to pronounce, memorable, relevant to the positioning, "
            "and flexible enough to support future growth. Before finalizing it, check trademark availability, "
            "domain availability, social handles, pronunciation, and possible negative meanings in your target markets."
        )

    if "position" in text or "strategy" in text:
        return (
            "Build your brand strategy around five things: target audience, customer problem, unique value proposition, "
            "brand personality, and competitive differentiation. Your positioning should clearly answer: "
            "who you serve, what problem you solve, why customers should choose you, and what makes you different."
        )

    if "social media" in text or "instagram" in text or "caption" in text:
        return (
            "For social media branding, maintain a consistent voice, visual style, colors, and messaging. "
            "Mix educational, entertaining, promotional, and community-focused content. "
            "Every post should have a clear purpose and a consistent connection to the brand."
        )

    if "customer" in text or "audience" in text:
        return (
            "Start by defining your ideal customer: demographics, goals, pain points, buying behavior, motivations, "
            "and expectations. Then adapt your brand message, visual identity, content, and marketing channels "
            "to that audience. A strong brand speaks to a specific customer rather than trying to appeal to everyone."
        )

    if "marketing" in text or "promot" in text or "campaign" in text:
        return (
            "A good marketing campaign starts with a clear objective, defined target audience, strong value proposition, "
            "consistent brand messaging, suitable channels, and a measurable call to action. "
            "Track awareness, engagement, leads, conversions, and customer response so you can improve future campaigns."
        )

    if "story" in text:
        return (
            "A strong brand story explains the problem you noticed, why your brand exists, how you solve the problem, "
            "and the transformation customers receive. Keep the customer at the center of the story rather than making "
            "the company the only hero."
        )

    if "review" in text or "sentiment" in text:
        return (
            "Customer reviews can reveal how people perceive your brand. Look for repeated positive and negative themes, "
            "customer emotions, product issues, service problems, and frequently mentioned strengths. "
            "Use those insights to improve your positioning, messaging, product experience, and customer communication."
        )

    return (
        "For this branding question, start by defining your target customer, desired brand perception, "
        "unique value proposition, and competitive difference. Then make sure your name, logo, colors, typography, "
        "messaging, and marketing content consistently communicate that positioning."
    )


# ---------------------------------------------------------
# MAIN CHAT ENDPOINT
# ---------------------------------------------------------

@router.post("/chat", response_model=ChatResponse)
def chat_assistant(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_message = req.message.strip()

    if not user_message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty."
        )

    user_message_lower = user_message.lower().strip()

    # -----------------------------------------------------
    # Allow greetings and basic assistant questions
    # -----------------------------------------------------

    greetings = [
        "hello",
        "hi",
        "hey",
        "hola",
        "howdy",
        "greetings",
        "good morning",
        "good afternoon",
        "good evening",
    ]

    is_greeting = any(
        user_message_lower == greeting
        or user_message_lower.startswith(greeting + " ")
        or user_message_lower.startswith(greeting + ",")
        for greeting in greetings
    )

    allowed_smalltalk = [
        "who are you",
        "what is your name",
        "your name",
        "what can you do",
        "features",
        "capabilities",
        "how can you help",
        "help me",
        "how are you",
        "thank you",
        "thanks",
        "what model",
        "which model",
    ]

    is_smalltalk = any(
        phrase in user_message_lower
        for phrase in allowed_smalltalk
    )

    # -----------------------------------------------------
    # STRICT BRANDING FILTER
    # -----------------------------------------------------

    branding = is_branding_question(user_message)

    clearly_unrelated = any(
        term in user_message_lower
        for term in UNRELATED_TERMS
    )

    # If clearly unrelated, stay inside BrandCraft scope.
    if clearly_unrelated and not branding:
        reply = (
            "I specialize in branding and marketing assistance. "
            "Please ask me about brand strategy, naming, logos, "
            "marketing, content, customers, positioning, or business identity."
        )

        return ChatResponse(message=reply)

    # Greetings / capabilities can always be answered.
    if is_greeting or is_smalltalk:
        branding = True

    # Unknown questions should NOT be sent outside BrandCraft.
    if not branding:
        reply = (
            "I specialize in branding and marketing assistance. "
            "Please ask me about brand strategy, brand names, logos, "
            "taglines, marketing, content, social media, customers, "
            "positioning, or business identity."
        )

        return ChatResponse(message=reply)

    # -----------------------------------------------------
    # SAVE USER MESSAGE
    # -----------------------------------------------------

    try:
        db_user_msg = ChatMessageDB(
            user_id=current_user.id,
            sender="user",
            message=user_message
        )

        db.add(db_user_msg)
        db.commit()

    except Exception as db_err:
        logger.error(
            f"Failed to save user message to DB: {db_err}"
        )

    # -----------------------------------------------------
    # GEMINI
    # -----------------------------------------------------

    if not HAS_GEMINI_KEY:
        reply = fallback_chat_response(user_message)

    else:

        system_instruction = """
You are BrandCraft AI Assistant.

You are a specialized AI consultant for BRANDING, MARKETING, BUSINESS IDENTITY,
and CUSTOMER-FACING BRAND COMMUNICATION.

Your job is to answer the user's branding questions directly and helpfully.

==================================================
ALLOWED TOPICS
==================================================

You may answer questions about:

- Brand strategy
- Brand positioning
- Brand identity
- Brand personality
- Brand values
- Brand awareness
- Brand recognition
- Brand trust
- Brand loyalty
- Brand naming
- Company naming
- Product naming
- Business naming
- Taglines
- Slogans
- Brand stories
- Brand messaging
- Unique Value Proposition (UVP)
- Unique Selling Proposition (USP)
- Target audience
- Customer personas
- Customer segmentation
- Market positioning
- Competitor differentiation
- Competitive advantage
- Logo concepts
- Logo design principles
- Logo styles
- Visual identity
- Brand colors
- Color psychology
- Typography
- Fonts
- Packaging branding
- Website branding
- Social media branding
- Instagram content
- LinkedIn content
- Facebook content
- Social media captions
- Marketing content
- Copywriting
- Advertisements
- Advertising campaigns
- Marketing campaigns
- Product launches
- Promotions
- Email marketing
- Customer engagement
- Customer retention
- Customer experience
- Customer feedback
- Reviews
- Brand sentiment
- Digital marketing
- Influencer marketing
- Content strategy
- Marketing strategy
- Business growth when directly related to branding or marketing
- Startup branding
- Brand guidelines
- Rebranding
- Personal branding
- E-commerce branding

==================================================
STRICT SCOPE
==================================================

You MUST stay within branding, marketing, business identity,
customer communication, and closely related business topics.

If the user asks about an unrelated topic such as:

sports, cricket, IPL, weather, cooking, recipes, medicine,
politics, entertainment, mathematics, general programming,
coding, homework, or unrelated technical questions,

respond exactly:

"I specialize in branding and marketing assistance. Please ask me a branding-related question."

Do not answer unrelated questions.

==================================================
ANSWER QUALITY
==================================================

For branding questions:

1. Directly answer the user's question.
2. Do not simply repeat your introduction.
3. Do not tell the user to use another feature unless it genuinely helps.
4. Give practical recommendations.
5. Use examples when useful.
6. If the user asks for names, provide actual name ideas.
7. If the user asks for taglines, provide actual taglines.
8. If the user asks for social media content, write the content.
9. If the user asks for a marketing strategy, provide an actionable strategy.
10. If the user asks about a logo, provide concrete design direction.
11. If the user asks about colors, recommend actual color combinations and explain them.
12. If the user asks about fonts, recommend actual font combinations.
13. If the user asks about positioning, provide positioning statements and differentiation ideas.
14. If the user provides a business, product, audience, or industry, customize the answer to it.

Do not be unnecessarily verbose, but provide enough information to be genuinely useful.

==================================================
CONVERSATION STYLE
==================================================

Be professional, friendly, creative, and practical.

The user may ask follow-up questions.
Remember the conversation context and build on previous answers.

Never respond with the generic greeting when the user asks a real branding question.

For example:

User:
"How can I make my clothing brand look luxurious?"

You should answer with specific advice about:
colors, typography, photography, packaging, logo style,
messaging, pricing perception, and social media presentation.

Do NOT respond with:
"Hello! I am BrandCraft AI Assistant..."

==================================================
"""

        try:

            # Try current lightweight model first
            model_names = [
                "gemini-2.5-flash-lite",
                "gemini-2.5-flash",
                "gemini-2.0-flash",
            ]

            reply = None

            for model_name in model_names:

                try:
                    logger.info(
                        f"Trying Gemini model: {model_name}"
                    )

                    model = genai.GenerativeModel(
                        model_name=model_name,
                        system_instruction=system_instruction
                    )

                    contents = []

                    # Add recent conversation history
                    for msg in req.history[-10:]:
                        role = (
                            "user"
                            if msg.sender == "user"
                            else "model"
                        )

                        contents.append(
                            {
                                "role": role,
                                "parts": [msg.message]
                            }
                        )

                    # Current user message
                    contents.append(
                        {
                            "role": "user",
                            "parts": [user_message]
                        }
                    )

                    response = model.generate_content(
                        contents
                    )

                    if response and response.text:
                        reply = response.text.strip()
                        break

                except Exception as model_err:

                    logger.warning(
                        f"Gemini model {model_name} failed: {model_err}"
                    )

            # If all Gemini models failed
            if not reply:
                logger.warning(
                    "All Gemini models failed. Using local branding fallback."
                )

                reply = fallback_chat_response(
                    user_message
                )

        except Exception as e:

            logger.error(
                f"Gemini chat failed: {e}"
            )

            reply = fallback_chat_response(
                user_message
            )

    # -----------------------------------------------------
    # SAVE ASSISTANT RESPONSE
    # -----------------------------------------------------

    try:

        db_assistant_msg = ChatMessageDB(
            user_id=current_user.id,
            sender="assistant",
            message=reply
        )

        db.add(db_assistant_msg)
        db.commit()

    except Exception as db_err:

        logger.error(
            f"Failed to save assistant response to DB: {db_err}"
        )

    return ChatResponse(message=reply)


# ---------------------------------------------------------
# GET CHAT HISTORY
# ---------------------------------------------------------

@router.get("/history", response_model=List[ChatMessage])
def get_chat_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    try:

        messages = (
            db.query(ChatMessageDB)
            .filter(
                ChatMessageDB.user_id == current_user.id
            )
            .order_by(
                ChatMessageDB.created_at.asc()
            )
            .all()
        )

        return [
            ChatMessage(
                sender=m.sender,
                message=m.message
            )
            for m in messages
        ]

    except Exception as e:

        logger.error(
            f"Failed to fetch chat history: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail=f"Database error: {e}"
        )


# ---------------------------------------------------------
# DELETE CHAT HISTORY
# ---------------------------------------------------------

@router.delete("/history")
def clear_chat_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    try:

        db.query(ChatMessageDB).filter(
            ChatMessageDB.user_id == current_user.id
        ).delete()

        db.commit()

        return {
            "message": "Chat history cleared successfully"
        }

    except Exception as e:

        logger.error(
            f"Failed to clear chat history: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail=f"Database error: {e}"
        )