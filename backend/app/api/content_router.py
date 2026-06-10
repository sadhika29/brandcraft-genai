import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session
import google.generativeai as genai

from backend.app.database import get_db
from backend.app.models import User, SavedContent
from backend.app.schemas import ContentRequest, ContentResponse, ContentDataSchema
from backend.app.auth import get_current_user
from backend.app.config import GEMINI_API_KEY, HAS_GEMINI_KEY

router = APIRouter(prefix="/api/content", tags=["content"])
logger = logging.getLogger(__name__)

# Configure Gemini if key is present
if HAS_GEMINI_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def generate_fallback_content(req: ContentRequest) -> dict:
    """Procedurally generates varied mock content matching the required counts."""
    logger.info("Using procedural fallback content generator.")
    
    # 1. 50 Slogans
    slogan_templates = [
        "Redefining {industry} with a {tone} touch.",
        "Where {industry} meets excellence.",
        "Your journey in {industry} starts here.",
        "The {tone} way to experience your daily routine.",
        "Making {industry} better everyday.",
        "Innovating your life, one {industry} solution at a time.",
        "Simple. Smart. Reliable.",
        "The gold standard of {industry}.",
        "Unlocking potential, inspiring growth.",
        "Your partner in modern {industry}.",
        "Simply the best for you.",
        "Empowering your tomorrow.",
        "The future of {industry} starts now.",
        "Crafted for performance, styled for elegance.",
        "Designed to inspire.",
        "Your dream, our blueprint."
    ]
    
    slogans = []
    for i in range(5):
        tmpl = slogan_templates[i % len(slogan_templates)]
        formatted = tmpl.format(industry=req.industry.lower(), tone=req.tone.lower())
        slogans.append(f"{req.brand_name}: {formatted} (Option {i+1})")
        
    # 2. 10 Brand Stories
    story_templates = [
        "Founded with a vision to revolutionize {industry}, {brand_name} was born out of a desire for authentic, {tone} solutions that empower everyday builders.",
        "At {brand_name}, we believe that {industry} should be accessible, high-quality, and tailored to your lifestyle. We exist to bring simplicity to a complex world.",
        "From humble beginnings in a small workshop to a leading name in {industry}, {brand_name} stands for trust, quality, and endless innovation.",
        "Our journey began with a single question: How can we make {industry} more human? Today, {brand_name} answers that question for thousands of customers.",
        "We don't just build products; we craft experiences. At {brand_name}, our core values revolve around absolute {tone} integrity and customer empowerment.",
        "Innovation is in our DNA. We consistently push the boundaries of what is possible in {industry} to bring you the best performance.",
        "Behind {brand_name} is a team of designers, engineers, and visionaries united by a common passion: creating a better standard for {industry}.",
        "We believe in sustainability. {brand_name} combines eco-conscious materials with state-of-the-art technology to shape a better future.",
        "Every line, every detail, every product at {brand_name} is crafted with a single purpose: helping you achieve your branding goals with ease.",
        "The history of {brand_name} is written by our customers. We grow together, building a legacy of excellence and trust in {industry}."
    ]
    
    brand_stories = []
    for i in range(1):
        tmpl = story_templates[i]
        brand_stories.append(tmpl.format(brand_name=req.brand_name, industry=req.industry.lower(), tone=req.tone.lower()))

    # 3. 20 Product Descriptions
    product_lines = ["Core", "Pro", "Ultra", "Classic", "Go", "Max", "Prime", "Lite", "Elite", "Signature", "One", "Connect", "X", "Alpha", "Apex", "Nova", "Quest", "Link", "Sync", "Plus"]
    product_templates = [
        "Introducing {brand_name} {line}: The quintessential addition to your {industry} routine, blending a {tone} finish with exceptional performance.",
        "The {brand_name} {line}: Designed for demanding {industry} environments, delivering top-tier reliability and value.",
        "Meet {brand_name} {line}: Compact, smart, and fully optimized for modern users. Experience {industry} like never before.",
        "Our signature {brand_name} {line} features an elegant, {tone} design combined with state of the art technology in {industry}.",
        "The {brand_name} {line} brings sustainable materials and {tone} craftsmanship to your favorite {industry} utilities."
    ]
    
    product_descriptions = []
    for i in range(2):
        line = product_lines[i]
        tmpl = product_templates[i % len(product_templates)]
        product_descriptions.append(tmpl.format(brand_name=req.brand_name, line=line, industry=req.industry.lower(), tone=req.tone.lower()))

    # 4. 20 Social Media Captions
    social_templates = [
        "Elevating your day-to-day routine with {brand_name}. ✨ How do you handle your {industry} needs? #{brand_clean} #lifestyle",
        "Minimalist design, maximum output. That is the {brand_name} promise. 💼 #{brand_clean} #business",
        "Behind the scenes at our {industry} studio. Hard work meets a {tone} vision! 🛠️ #{brand_clean} #innovation",
        "Sunday mornings are better with {brand_name}. ☕ What is your favorite product from our catalog? #relax #weekend",
        "Big announcements coming soon! Stay tuned as we prepare to change the face of {industry} forever. 🚀 #staytuned",
        "Performance isn't an accident. It's a design choice. Check out our {tone} collection. Link in bio! 🔗 #design",
        "Our customers speak for themselves: '{brand_name} changed my workflow!' Thank you for the love! ❤️ #grateful",
        "Simple, sleek, and highly effective. Which color path fits your vibe? 🎨 #colorpalette #branding",
        "Start your week strong with {brand_name}. We have got your {industry} worries covered. 💪 #motivation #monday",
        "Celebrating 5 years of quality. Thank you for making {brand_name} your primary choice! 🎉 #anniversary"
    ]
    
    social_media_captions = []
    brand_clean = req.brand_name.replace(" ", "")
    for i in range(2):
        tmpl = social_templates[i % len(social_templates)]
        social_media_captions.append(tmpl.format(brand_name=req.brand_name, brand_clean=brand_clean, industry=req.industry.lower(), tone=req.tone.lower()) + f" (Option {i+1})")

    # 5. 10 Advertisement Copies
    ad_templates = [
        "Tired of average {industry}? Discover the {brand_name} difference today. Get 20% off your first order! Click Learn More.",
        "Built for those who demand a {tone} experience. Upgrade to {brand_name} and feel the performance shift immediately.",
        "Can your current {industry} tools do this? Meet {brand_name} – the smart, reliable solution built for modern creators.",
        "Stop wasting time on sub-par setups. {brand_name} delivers premium {industry} features at an affordable cost. Buy now!",
        "Simplicity is the ultimate sophistication. {brand_name} brings a clean, {tone} design to your daily life. Explore now.",
        "Say goodbye to complications. {brand_name} is here to streamline your {industry} projects. Try it risk-free today!",
        "What makes a brand memorable? It starts with the right foundation. Build yours with {brand_name} today. Sign up.",
        "Quality you can trust. Style you can see. {brand_name} is the gold standard for modern {industry}. Buy today.",
        "Engineered for speed, crafted for comfort. Experience {brand_name} now and get free shipping worldwide!",
        "Your startup deserves the best. Boost your brand identity with the {tone} style of {brand_name}. Get started."
    ]
    
    advertisement_copies = []
    for i in range(1):
        tmpl = ad_templates[i]
        advertisement_copies.append(tmpl.format(brand_name=req.brand_name, industry=req.industry.lower(), tone=req.tone.lower()))

    # 6. 10 Email Templates
    subjects = [
        "Welcome to the {brand_name} Family!",
        "Your exclusive 15% discount code is inside",
        "How to optimize your {industry} strategy",
        "Introducing our new premium line",
        "A personal message from the founder of {brand_name}",
        "Is your branding holding you back?",
        "Tips for creating a modern brand identity",
        "Here is what you missed this week at {brand_name}",
        "Unlock 24/7 access to branding expert guides",
        "Your opinion matters to us (Quick feedback request)"
    ]
    
    bodies = [
        "Dear Customer,\n\nDiscover how {brand_name} is bringing a {tone} approach to {industry}. We are thrilled to have you with us!\n\nBest regards,\nThe {brand_name} Team",
        "Hello,\n\nAs a thank you for joining us, here is a 15% discount code for your next purchase: BRIGHT15. Enter it at checkout.\n\nBest,\nThe {brand_name} Team",
        "Hi there,\n\nSuccessful brands don't happen by accident. Here are 3 tips to streamline your {industry} positioning and stand out in the crowd.\n\nRead more on our blog.\n\nBest,\n{brand_name}",
        "Dear Customer,\n\nWe are proud to unveil our latest premium catalog. Crafted with absolute {tone} design principles to fit your startup needs.\n\nShop now,\nThe {brand_name} Team",
        "Hello,\n\nI started {brand_name} with a simple goal: to make {industry} accessible, high-quality, and elegant. Thank you for supporting our dream.\n\nWarmly,\nFounder of {brand_name}",
        "Hi,\n\nIs your messaging reaching the right audience? Let's audit your current {industry} campaign together and fix the bottlenecks.\n\nTalk soon,\n{brand_name} Support",
        "Hello,\n\nIn this newsletter, we discuss typography, logo guidelines, and slogans. Learn how to craft a {tone} identity.\n\nRead now,\n{brand_name}",
        "Hi there,\n\nIt has been a busy week! Here is a recap of our top articles, product releases, and updates regarding {industry}.\n\nBest,\n{brand_name}",
        "Hello,\n\nReady to scale? Unlock unlimited resources and connect with branding experts to elevate your startup today.\n\nGet started,\n{brand_name}",
        "Dear Customer,\n\nWe strive to improve everyday. Please take 2 minutes to let us know how we can make your {industry} experience better.\n\nTake survey,\n{brand_name} Team"
    ]
    
    email_marketing_templates = []
    for i in range(1):
        subject = subjects[i].format(brand_name=req.brand_name, industry=req.industry)
        body = bodies[i].format(brand_name=req.brand_name, industry=req.industry.lower(), tone=req.tone.lower())
        email_marketing_templates.append({
            "subject": subject,
            "body": body
        })

    return {
        "slogans": slogans,
        "brand_stories": brand_stories,
        "product_descriptions": product_descriptions,
        "social_media_captions": social_media_captions,
        "advertisement_copies": advertisement_copies,
        "email_marketing_templates": email_marketing_templates
    }

@router.post("/generate", response_model=ContentResponse)
def generate_content(req: ContentRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    content_data = None
    
    if HAS_GEMINI_KEY:
        prompt = f"""
        You are an expert copywriter. 
        Generate a complete brand content pack for the following parameters:
        - Brand Name: {req.brand_name}
        - Industry: {req.industry}
        - Tone of Voice: {req.tone}
        
        Generate exactly:
        1. 5 distinct slogans/slogans.
        2. 1 short brand story or about us copy variation.
        3. 2 product description copy blocks.
        4. 2 engaging social media captions (e.g. for Instagram/LinkedIn) with hashtags.
        5. 1 high-converting advertisement copy variation (hook, body, and call-to-action).
        6. 1 email marketing template, with a "subject" and "body" key.
        
        Return ONLY a JSON object containing the following keys mapping to arrays:
        - "slogans" (array of strings)
        - "brand_stories" (array of strings)
        - "product_descriptions" (array of strings)
        - "social_media_captions" (array of strings)
        - "advertisement_copies" (array of strings)
        - "email_marketing_templates" (array of objects with keys "subject" and "body")
        
        Ensure you generate the exact numbers requested.
        """
        
        try:
            model_name = "gemini-2.5-flash-lite"
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
            except Exception as model_err:
                logger.warning(f"Gemini content generation with {model_name} failed: {model_err}. Trying gemini-2.5-flash...")
                model_name = "gemini-2.5-flash"
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(
                        prompt,
                        generation_config={"response_mime_type": "application/json"}
                    )
                except Exception as model_err2:
                    logger.warning(f"Gemini content generation with {model_name} failed: {model_err2}. Trying gemini-2.0-flash...")
                    model = genai.GenerativeModel("gemini-2.0-flash")
                    response = model.generate_content(
                        prompt,
                        generation_config={"response_mime_type": "application/json"}
                    )
            
            content_data = json.loads(response.text)
            
            # Basic key verification
            required_keys = ["slogans", "brand_stories", "product_descriptions", "social_media_captions", "advertisement_copies", "email_marketing_templates"]
            for key in required_keys:
                if key not in content_data or not isinstance(content_data[key], list):
                    raise ValueError(f"Missing or invalid key in JSON output: {key}")
                    
        except Exception as e:
            logger.error(f"Gemini content generation failed: {e}. Falling back to procedural content.")
            content_data = generate_fallback_content(req)
    else:
        content_data = generate_fallback_content(req)
        
    # Save to database
    db_content = SavedContent(
        user_id=current_user.id,
        brand_name=req.brand_name,
        content_data=json.dumps(content_data)
    )
    db.add(db_content)
    db.commit()
    db.refresh(db_content)
    
    # Return formatted schema
    return ContentResponse(
        id=db_content.id,
        brand_name=db_content.brand_name,
        content_data=content_data,
        created_at=db_content.created_at
    )

@router.get("/saved", response_model=List[ContentResponse])
def get_saved_content(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    contents = db.query(SavedContent).filter(SavedContent.user_id == current_user.id).order_by(SavedContent.created_at.desc()).all()
    
    response_list = []
    for c in contents:
        try:
            parsed_data = json.loads(c.content_data)
        except Exception:
            parsed_data = generate_fallback_content(ContentRequest(brand_name=c.brand_name, industry="Unknown", tone="Professional"))
            
        response_list.append(
            ContentResponse(
                id=c.id,
                brand_name=c.brand_name,
                content_data=parsed_data,
                created_at=c.created_at
            )
        )
    return response_list

@router.delete("/saved/{content_id}")
def delete_saved_content(content_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    content = db.query(SavedContent).filter(SavedContent.id == content_id, SavedContent.user_id == current_user.id).first()
    if not content:
        raise HTTPException(status_code=404, detail="Saved content not found")
        
    db.delete(content)
    db.commit()
    return {"message": "Content deleted successfully"}
