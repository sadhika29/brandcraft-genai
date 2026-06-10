import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session
import google.generativeai as genai

from backend.app.database import get_db
from backend.app.models import User, SavedBrand
from backend.app.schemas import BrandRequest, BrandResponse, SavedBrandCreate, SavedBrandResponse
from backend.app.auth import get_current_user
from backend.app.config import GEMINI_API_KEY, HAS_GEMINI_KEY

router = APIRouter(prefix="/api/generator", tags=["generator"])
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
            
        # Clean and ensure brand name uniqueness (case-insensitive)
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI brand name generation failed: {str(e)}"
        )

@router.post("/save", response_model=SavedBrandResponse)
def save_brand(brand_data: SavedBrandCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Save the brand
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
    
    # Return serializable object
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
