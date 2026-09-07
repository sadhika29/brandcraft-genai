import json
import logging
import re
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import google.generativeai as genai

from app.database import get_db
from app.models import User, SavedContent
from app.schemas import ContentRequest, ContentResponse
from app.auth import get_current_user
from app.config import GEMINI_API_KEY, HAS_GEMINI_KEY

router = APIRouter(prefix="/api/content", tags=["content"])

logger = logging.getLogger(__name__)

if HAS_GEMINI_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def generate_fallback_content(req: ContentRequest) -> dict:
    logger.info("Using procedural fallback content generator.")

    brand_name = req.brand_name.strip()
    industry = req.industry.strip().lower()
    tone = req.tone.strip().lower()

    slogan_templates = [
        "Redefining {industry} with a {tone} touch.",
        "Where {industry} meets excellence.",
        "Your journey in {industry} starts here.",
        "The {tone} way to experience {industry}.",
        "Making {industry} better every day.",
        "Innovating your world through smarter {industry} solutions.",
        "Simple. Smart. Reliable.",
        "The new standard for {industry}.",
        "Unlocking potential through {industry} innovation.",
        "Your trusted partner in modern {industry}.",
        "Built for today. Ready for tomorrow.",
        "Empowering people through better {industry}.",
        "The future of {industry} starts here.",
        "Crafted for performance. Designed for impact.",
        "Ideas that inspire. Solutions that deliver.",
        "Turning possibilities into progress."
    ]

    slogans = []

    for i in range(5):
        slogans.append(
            slogan_templates[i].format(
                industry=industry,
                tone=tone
            )
        )

    story_templates = [
        "Born from a vision to transform {industry}, {brand_name} was created to deliver meaningful, {tone} experiences for modern customers.",
        "At {brand_name}, we believe that great {industry} experiences should be simple, accessible, and memorable.",
        "The journey of {brand_name} began with one goal: to create a better and more meaningful experience in {industry}.",
        "Driven by innovation and customer needs, {brand_name} brings a fresh {tone} perspective to {industry}.",
        "We created {brand_name} to turn everyday challenges into opportunities through thoughtful {industry} solutions.",
        "Behind {brand_name} is a passion for creativity, quality, and continuous improvement in {industry}.",
        "{brand_name} combines modern ideas with a human approach to create lasting value in {industry}.",
        "Our mission at {brand_name} is to make {industry} more engaging, useful, and accessible for everyone.",
        "Every detail of {brand_name} reflects our commitment to quality, innovation, and customer satisfaction.",
        "With a vision for the future, {brand_name} continues to push the boundaries of what is possible in {industry}."
    ]

    brand_stories = [
        story_templates[0].format(
            brand_name=brand_name,
            industry=industry,
            tone=tone
        )
    ]

    product_templates = [
        "Introducing {brand_name} Core, a reliable solution designed to simplify your {industry} experience with a {tone} approach.",
        "Meet {brand_name} Pro, created for users who want better performance, flexibility, and value in {industry}.",
        "{brand_name} Ultra combines advanced features with an intuitive experience built for modern {industry} users.",
        "{brand_name} Classic delivers dependable performance while maintaining a clean and timeless design.",
        "{brand_name} Max is designed for customers who expect powerful performance and a premium {industry} experience.",
        "{brand_name} Prime brings together quality, innovation, and convenience in one complete {industry} solution.",
        "{brand_name} Lite provides a simple and efficient way to manage everyday {industry} needs.",
        "{brand_name} Elite is designed for customers looking for premium quality and an elevated experience.",
        "{brand_name} One brings essential {industry} features together in one convenient solution.",
        "{brand_name} Connect helps modern users stay connected while managing their {industry} needs.",
        "{brand_name} Nova introduces a fresh approach to {industry} through innovative design and functionality.",
        "{brand_name} Apex is built for customers who want high performance and dependable results."
    ]

    product_descriptions = []

    for i in range(2):
        product_descriptions.append(
            product_templates[i].format(
                brand_name=brand_name,
                industry=industry,
                tone=tone
            )
        )

    brand_clean = "".join(
        character for character in brand_name
        if character.isalnum()
    ).lower()

    social_templates = [
        "Elevate your {industry} experience with {brand_name}. Discover what makes our approach different. ✨ #{brand_clean} #branding",
        "Innovation meets purpose at {brand_name}. Built to make your {industry} journey smarter and simpler. 🚀 #{brand_clean} #innovation",
        "A better {industry} experience starts with better ideas. That is the {brand_name} way. 💡 #{brand_clean} #business",
        "Behind every great brand is a clear purpose. Follow the journey of {brand_name}. ❤️ #{brand_clean} #brandstory",
        "Simple ideas can create powerful experiences. Discover {brand_name} and rethink {industry}. ✨ #{brand_clean} #design",
        "Your audience deserves something better. {brand_name} is here to deliver it. 🚀 #{brand_clean} #marketing",
        "Great products begin with great customer understanding. That is what drives {brand_name}. 💙 #{brand_clean} #customers",
        "From concept to experience, {brand_name} is built around creativity and impact. 🎯 #{brand_clean} #branding",
        "Ready to experience {industry} differently? Meet {brand_name}. 🔥 #{brand_clean} #innovation",
        "We are building the future of {industry}, one idea at a time. Join {brand_name}. 🌟 #{brand_clean} #future"
    ]

    social_media_captions = []

    for i in range(2):
        social_media_captions.append(
            social_templates[i].format(
                brand_name=brand_name,
                brand_clean=brand_clean,
                industry=industry
            )
        )

    advertisement_templates = [
        {
            "hook": "Ready for a better {industry} experience?",
            "body": "{brand_name} brings a fresh, {tone}, and customer-focused approach designed for modern users.",
            "cta": "Discover {brand_name} today."
        },
        {
            "hook": "Your {industry} journey deserves better.",
            "body": "Experience the quality, simplicity, and innovation of {brand_name}.",
            "cta": "Explore {brand_name} now."
        },
        {
            "hook": "Meet the next generation of {industry}.",
            "body": "{brand_name} combines thoughtful design with practical solutions for today's customers.",
            "cta": "Get started today."
        },
        {
            "hook": "Stop settling for ordinary.",
            "body": "{brand_name} delivers a modern and {tone} approach to {industry}.",
            "cta": "Experience the difference."
        },
        {
            "hook": "Better ideas. Better experiences.",
            "body": "{brand_name} is designed around what customers really need from {industry}.",
            "cta": "Discover more."
        },
        {
            "hook": "Make your {industry} experience smarter.",
            "body": "Choose {brand_name} for a simple, reliable, and innovative experience.",
            "cta": "Try {brand_name} today."
        },
        {
            "hook": "Innovation starts with a better idea.",
            "body": "{brand_name} turns that idea into a meaningful {industry} experience.",
            "cta": "Start your journey."
        },
        {
            "hook": "Built for modern customers.",
            "body": "{brand_name} brings quality and creativity together to improve your {industry} experience.",
            "cta": "Learn more today."
        },
        {
            "hook": "Your needs come first.",
            "body": "Discover how {brand_name} makes {industry} simpler, smarter, and more enjoyable.",
            "cta": "Explore now."
        },
        {
            "hook": "The future is already here.",
            "body": "{brand_name} is creating a new standard for modern {industry}.",
            "cta": "Join the future."
        }
    ]

    ad = advertisement_templates[0]

    advertisement_copies = [
        (
            f"{ad['hook'].format(industry=industry)}\n\n"
            f"{ad['body'].format(brand_name=brand_name, tone=tone, industry=industry)}\n\n"
            f"{ad['cta'].format(brand_name=brand_name)}"
        )
    ]

    email_templates = [
        {
            "subject": f"Welcome to the {brand_name} experience",
            "body": (
                f"Hello,\n\n"
                f"We are excited to introduce you to {brand_name}, "
                f"a fresh approach to {industry} built around quality, innovation, and customer needs.\n\n"
                f"Discover what makes our {tone} approach different and see how {brand_name} "
                f"can make your experience better.\n\n"
                f"Best regards,\n"
                f"The {brand_name} Team"
            )
        },
        {
            "subject": f"Discover what makes {brand_name} different",
            "body": (
                f"Hello,\n\n"
                f"Great brands are built around great customer experiences. "
                f"At {brand_name}, we are focused on creating meaningful solutions for {industry}.\n\n"
                f"Explore our latest offerings and discover a better way to experience {industry}.\n\n"
                f"Best,\n"
                f"The {brand_name} Team"
            )
        }
    ]

    email_marketing_templates = [email_templates[0]]

    return {
        "slogans": slogans,
        "brand_stories": brand_stories,
        "product_descriptions": product_descriptions,
        "social_media_captions": social_media_captions,
        "advertisement_copies": advertisement_copies,
        "email_marketing_templates": email_marketing_templates
    }


def clean_slogans(slogans: list) -> list:
    """
    Removes numbering from slogans so numbering is displayed only once
    by the frontend.

    Examples:
    1. Build Better Brands -> Build Better Brands
    2) Think Different -> Think Different
    Option 3: Grow Smarter -> Grow Smarter
    """

    cleaned = []

    for slogan in slogans:
        if not isinstance(slogan, str):
            continue

        slogan = slogan.strip()

        # Remove common Gemini numbering formats
        slogan = re.sub(
            r"^\s*(?:option\s*)?\d+\s*[\.\)\:\-\–\—]\s*",
            "",
            slogan,
            flags=re.IGNORECASE
        )

        # Remove Markdown bullets
        slogan = re.sub(
            r"^\s*[-*•]\s*",
            "",
            slogan
        )

        slogan = slogan.strip()

        if slogan and slogan not in cleaned:
            cleaned.append(slogan)

    return cleaned


def validate_content_data(content_data: dict) -> bool:
    required_keys = [
        "slogans",
        "brand_stories",
        "product_descriptions",
        "social_media_captions",
        "advertisement_copies",
        "email_marketing_templates"
    ]

    for key in required_keys:
        if key not in content_data:
            return False

        if not isinstance(content_data[key], list):
            return False

    return True


@router.post(
    "/generate",
    response_model=ContentResponse
)
def generate_content(
    req: ContentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    content_data = None

    if HAS_GEMINI_KEY:

        prompt = f"""
You are an expert brand strategist, marketing copywriter, and creative director.

Create a complete content pack for this brand:

Brand Name: {req.brand_name}
Industry: {req.industry}
Tone of Voice: {req.tone}

Generate EXACTLY:

1. 5 completely different slogans.
2. 1 short brand story / About Us paragraph.
3. 2 different product descriptions.
4. 2 different social media captions.
5. 1 advertisement copy.
6. 1 email marketing template containing subject and body.

IMPORTANT RULES FOR SLOGANS:

- Return exactly 5 slogans.
- Every slogan must be different.
- Do NOT repeat the same slogan.
- Do NOT add numbering.
- Do NOT write "1.", "2.", "3.", etc.
- Do NOT write "Option 1", "Option 2", etc.
- Do NOT use bullet points.
- Return only the actual slogan text.
- Do not prefix slogans with numbers.
- Do not create duplicate slogans with only small wording changes.
- Make the slogans specific to the brand and industry.
- Avoid generic repeated phrases.

IMPORTANT RULES FOR ALL CONTENT:

- Make the content specific to the brand name and industry.
- Keep the requested tone consistent.
- Avoid repetitive sentences.
- Do not include unnecessary explanations.
- Return ONLY valid JSON.
- Do not use Markdown.
- Do not put the JSON inside code blocks.

Return exactly this JSON structure:

{{
    "slogans": [
        "slogan one",
        "slogan two",
        "slogan three",
        "slogan four",
        "slogan five"
    ],
    "brand_stories": [
        "brand story"
    ],
    "product_descriptions": [
        "product description one",
        "product description two"
    ],
    "social_media_captions": [
        "social media caption one",
        "social media caption two"
    ],
    "advertisement_copies": [
        "advertisement copy"
    ],
    "email_marketing_templates": [
        {{
            "subject": "email subject",
            "body": "email body"
        }}
    ]
}}
"""

        try:

            models_to_try = [
                "gemini-2.5-flash-lite",
                "gemini-2.5-flash",
                "gemini-2.0-flash"
            ]

            last_error = None

            for model_name in models_to_try:

                try:

                    logger.info(
                        f"Trying Gemini model: {model_name}"
                    )

                    model = genai.GenerativeModel(model_name)

                    response = model.generate_content(
                        prompt,
                        generation_config={
                            "response_mime_type": "application/json"
                        }
                    )

                    raw_text = response.text.strip()

                    if raw_text.startswith("```"):
                        raw_text = re.sub(
                            r"^```(?:json)?",
                            "",
                            raw_text,
                            flags=re.IGNORECASE
                        )

                        raw_text = re.sub(
                            r"```$",
                            "",
                            raw_text
                        ).strip()

                    content_data = json.loads(raw_text)

                    if not validate_content_data(content_data):
                        raise ValueError(
                            "Gemini returned an invalid content structure."
                        )

                    break

                except Exception as model_error:

                    last_error = model_error

                    logger.warning(
                        f"Gemini model {model_name} failed: "
                        f"{model_error}"
                    )

                    content_data = None

            if content_data is None:
                raise last_error or Exception(
                    "Gemini content generation failed."
                )

        except Exception as e:

            logger.error(
                f"Gemini content generation failed: {e}"
            )

            content_data = generate_fallback_content(req)

    else:

        logger.warning(
            "Gemini API key is not configured. "
            "Using fallback content generator."
        )

        content_data = generate_fallback_content(req)

    # Clean slogans returned by Gemini
    if "slogans" in content_data:

        content_data["slogans"] = clean_slogans(
            content_data["slogans"]
        )

    # Guarantee exactly 5 slogans
    if len(content_data.get("slogans", [])) < 5:

        fallback = generate_fallback_content(req)

        existing = content_data.get("slogans", [])

        for slogan in fallback["slogans"]:

            slogan = clean_slogans([slogan])[0]

            if slogan not in existing:
                existing.append(slogan)

            if len(existing) == 5:
                break

        content_data["slogans"] = existing[:5]

    else:

        content_data["slogans"] = (
            content_data["slogans"][:5]
        )

    # Save generated content
    try:

        db_content = SavedContent(
            user_id=current_user.id,
            brand_name=req.brand_name,
            content_data=json.dumps(
                content_data,
                ensure_ascii=False
            )
        )

        db.add(db_content)
        db.commit()
        db.refresh(db_content)

    except Exception as db_error:

        db.rollback()

        logger.error(
            f"Failed to save generated content: {db_error}"
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to save generated content."
        )

    return ContentResponse(
        id=db_content.id,
        brand_name=db_content.brand_name,
        content_data=content_data,
        created_at=db_content.created_at
    )


@router.get(
    "/saved",
    response_model=List[ContentResponse]
)
def get_saved_content(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    contents = (
        db.query(SavedContent)
        .filter(
            SavedContent.user_id == current_user.id
        )
        .order_by(
            SavedContent.created_at.desc()
        )
        .all()
    )

    response_list = []

    for content in contents:

        try:

            parsed_data = json.loads(
                content.content_data
            )

        except Exception:

            parsed_data = generate_fallback_content(
                ContentRequest(
                    brand_name=content.brand_name,
                    industry="Unknown",
                    tone="Professional"
                )
            )

        if "slogans" in parsed_data:

            parsed_data["slogans"] = clean_slogans(
                parsed_data["slogans"]
            )

        response_list.append(
            ContentResponse(
                id=content.id,
                brand_name=content.brand_name,
                content_data=parsed_data,
                created_at=content.created_at
            )
        )

    return response_list


@router.delete(
    "/saved/{content_id}"
)
def delete_saved_content(
    content_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    content = (
        db.query(SavedContent)
        .filter(
            SavedContent.id == content_id,
            SavedContent.user_id == current_user.id
        )
        .first()
    )

    if not content:

        raise HTTPException(
            status_code=404,
            detail="Saved content not found"
        )

    db.delete(content)
    db.commit()

    return {
        "message": "Content deleted successfully"
    }