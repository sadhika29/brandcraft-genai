import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session
import google.generativeai as genai
import random
from random import shuffle

from app.database import get_db
from app.models import User, SavedBrand
from app.schemas import BrandRequest, BrandResponse, SavedBrandCreate, SavedBrandResponse
from app.auth import get_current_user
from app.config import GEMINI_API_KEY, HAS_GEMINI_KEY

router = APIRouter(prefix="/api/generator", tags=["generator"])

# Helper to generate dummy brand data when Gemini API quota is exceeded
def generate_dummy_brands(req: BrandRequest):
    lang = req.preferred_language.lower()

    meaning_templates = {
        "english": [
            "{name} blends {business_type} insight with {personality} flair for {audience}.",
            "A {personality} take on {business_type}, embodied by {name}, aimed at {audience}.",
            "{name} captures the spirit of {industry} and {personality}, resonating with {audience}."
        ],
        "telugu": [
            "{name} {business_type} లో {personality} శక్తిని కలిపి {audience} కి అనుగుణంగా ఉంటుంది.",
            "{business_type} కు {personality} స్పర్శను ఇవ్వడానికి {name} రూపొందించబడింది, {audience} కోసం.",
            "{industry} రంగం యొక్క {personality} భావాన్ని {name} ద్వారా {audience} కు అందిస్తుంది."
        ],
        "hindi": [
            "{name} {business_type} में {personality} ऊर्जा को दर्शाता है, जो {audience} को आकर्षित करता है.",
            "{business_type} के लिए {personality} भावना के साथ {name}, {audience} के लिए.",
            "{industry} क्षेत्र की {personality} भावना को {name} के द्वारा {audience} तक पहुंचाया गया है."
        ],
        "spanish": [
            "{name} combina la visión de {business_type} con {personality} para {audience}.",
            "Una interpretación {personality} de {business_type} reflejada en {name}, dirigida a {audience}.",
            "{name} captura el espíritu de {industry} y {personality}, resonando con {audience}."
        ]
    }

    tagline_templates = {
        "english": "{personality} innovation for {audience}.",
        "telugu": "{audience} కోసం {personality} ఆవిష్కారం.",
        "hindi": "{personality} नवाचार {audience} के लिये।",
        "spanish": "Innovación {personality} para {audience}."
    }

    name_pools = {
        "english": {
            "adjectives": ["Bold", "Bright", "Fresh", "Vivid", "Epic", "Prime", "Nova", "Zesty", "Apex", "Dynamic"],
            "nouns": ["Wave", "Pulse", "Shift", "Forge", "Hive", "Nest", "Peak", "Vista", "Crest", "Flow"]
        },
        "telugu": {
            "adjectives": ["ధైర్య", "తేజస్సు", "అద్భుత", "వేగం", "జ్వల", "ఆకర్షణ", "నవీన", "ప్రాణ"],
            "nouns": ["కళ", "విజయం", "ఆవిష్కారం", "చిత్రం", "ప్రవాహం", "స్ఫూర్తి", "నవ్వు", "వృత్తం"]
        },
        "hindi": {
            "adjectives": ["साहसी", "चमकदार", "नवीन", "जीवंत", "प्रमुख", "तेज", "श्रेष्ठ", "गतिशील"],
            "nouns": ["लहर", "धड़कन", "बदलाव", "शिखर", "दृष्टि", "प्रवाह", "केंद्र", "शक्ति"]
        },
        "spanish": {
            "adjectives": ["Audaz", "Brillante", "Fresco", "Épico", "Ágil", "Vivo", "Cumbre", "Dinámico"],
            "nouns": ["Ola", "Pulso", "Cambio", "Forja", "Cima", "Vista", "Flujo", "Núcleo"]
        }
    }

    pool = name_pools.get(lang, name_pools["english"])
    meanings = meaning_templates.get(lang, meaning_templates["english"]).copy()
    tagline_tmpl = tagline_templates.get(lang, tagline_templates["english"])
    shuffle(meanings)

    brands = []
    used_names = set()
    for _ in range(10):
        while True:
            adj = random.choice(pool["adjectives"])
            noun = random.choice(pool["nouns"])
            name = adj + noun
            if name.lower() not in used_names:
                used_names.add(name.lower())
                break
        if not meanings:
            meanings = meaning_templates.get(lang, meaning_templates["english"]).copy()
            shuffle(meanings)
        meaning = meanings.pop().format(
            name=name,
            business_type=req.business_type,
            industry=req.industry,
            personality=req.brand_personality,
            audience=req.target_audience,
        )
        tagline = tagline_tmpl.format(personality=req.brand_personality, audience=req.target_audience)
        domains = [f"{name.lower()}.com", f"{name.lower()}.io", f"{name.lower()}.co"]
        brands.append({"name": name, "meaning": meaning, "tagline": tagline, "domains": domains})
    return {"brands": brands}

logger = logging.getLogger(__name__)

# Configure Gemini if key is present
if HAS_GEMINI_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

@router.post("/names", response_model=BrandResponse)
def generate_names(req: BrandRequest, current_user: User = Depends(get_current_user)):
    # Validate required fields
    missing = []
    if not req.business_type:
        missing.append('business_type')
    if not req.industry:
        missing.append('industry')
    if not req.target_audience:
        missing.append('target_audience')
    if not req.brand_personality:
        missing.append('brand_personality')
    if not req.preferred_language:
        missing.append('preferred_language')
    if not req.country:
        missing.append('country')
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required fields: {', '.join(missing)}")
    if not HAS_GEMINI_KEY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gemini API Key is not configured in backend/.env. Please configure GEMINI_API_KEY to generate brand names with AI."
        )

    prompt = f"""
    You are an expert branding consultant and namer.
    Generate a JSON list of exactly 10 to 12 creative brand names for the following business parameters:
    - Business Type: {req.business_type}
    - Industry: {req.industry}
    - Target Audience: {req.target_audience}
    - Brand Personality: {req.brand_personality}
    - Preferred Language for Name, Meaning, and Tagline: {req.preferred_language}
    - Target Country: {req.country}
    
    For each brand name, provide:
    1. The name (spelled appropriately in the preferred language or in roman letters if suitable).
    2. A brief description of the brand meaning or why this name works, written in the preferred language ({req.preferred_language}).
    3. A catchy tagline aligned with the brand personality, written in the preferred language ({req.preferred_language}).
    4. A list of 3 domain name ideas (e.g. name.com, name.io, name.co) that match the brand name.
    
    Return ONLY a JSON object with a single key "brands" mapping to an array of items. 
    Each item in the array MUST have the keys: "name", "meaning", "tagline", and "domains".
    
    Example output format:
    {{
      "brands": [
        {{
          "name": "ExampleBrand",
          "meaning": "Stands for reliability and growth.",
          "tagline": "Grow your dream.",
          "domains": ["examplebrand.com", "examplebrand.co", "examplebrand.io"]
        }}
      ]
    }}
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
            logger.warning(f"Gemini generation with {model_name} failed: {model_err}. Trying gemini-2.5-flash...")
            model_name = "gemini-2.5-flash"
            try:
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
            except Exception as model_err2:
                logger.warning(f"Gemini generation with {model_name} failed: {model_err2}. Trying gemini-2.0-flash...")
                model = genai.GenerativeModel("gemini-2.0-flash")
                response = model.generate_content(
                    prompt,
                    generation_config={"response_mime_type": "application/json"}
                )
        result = json.loads(response.text)
        if "brands" not in result or not isinstance(result["brands"], list):
            raise ValueError("Invalid Gemini Response format")
        # Ensure uniqueness
        unique_brands = []
        seen_names = set()
        for brand in result["brands"]:
            name = brand.get("name", "").strip()
            if name and name.lower() not in seen_names:
                seen_names.add(name.lower())
                unique_brands.append(brand)
        result["brands"] = unique_brands
        return result
    except Exception as e:
        logger.error(f"Gemini brand generation failed: {e}")
        err_str = str(e).lower()
        if "quota" in err_str or "429" in err_str or "rate limit" in err_str:
            logger.info("Falling back to local dummy brand generation due to quota or rate limit.")
            return generate_dummy_brands(req)
        logger.info("Falling back to dummy brand generation for unexpected error.")
        return generate_dummy_brands(req)

@router.post("/save", response_model=SavedBrandResponse)
def save_brand(brand_data: SavedBrandCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_brand = SavedBrand(
        user_id=current_user.id,
        brand_name=brand_data.brand_name,
        industry=brand_data.industry,
        target_audience=brand_data.target_audience,
        brand_meaning=brand_data.brand_meaning,
        tagline=brand_data.tagline,
        domain_suggestions=json.dumps(brand_data.domain_suggestions)
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

@router.get("/saved", response_model=List[SavedBrandResponse])
def get_saved_brands(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    brands = db.query(SavedBrand).filter(SavedBrand.user_id == current_user.id).all()
    response_list = []
    for b in brands:
        try:
            domains = json.loads(b.domain_suggestions)
        except Exception:
            domains = []
        response_list.append(
            SavedBrandResponse(
                id=b.id,
                brand_name=b.brand_name,
                industry=b.industry,
                target_audience=b.target_audience,
                brand_meaning=b.brand_meaning,
                tagline=b.tagline,
                domain_suggestions=domains,
                created_at=b.created_at
            )
        )
    return response_list

@router.delete("/saved/{brand_id}")
def delete_saved_brand(brand_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    brand = db.query(SavedBrand).filter(SavedBrand.id == brand_id, SavedBrand.user_id == current_user.id).first()
    if not brand:
        raise HTTPException(status_code=404, detail="Saved brand not found")
    db.delete(brand)
    db.commit()
    return {"message": "Brand deleted successfully"}
