from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict
from datetime import datetime

# Auth Schemas
class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    confirm_password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    remember_me: Optional[bool] = False

class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: UserResponse

class TokenData(BaseModel):
    email: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordConfirm(BaseModel):
    token: str
    password: str = Field(..., min_length=6)

# Brand Generator Schemas
class BrandRequest(BaseModel):
    business_type: str
    industry: str
    target_audience: str
    brand_personality: str
    preferred_language: str
    country: str

class DomainSuggestion(BaseModel):
    domain: str
    available: bool

class BrandItem(BaseModel):
    name: str
    meaning: str
    tagline: str
    domains: List[str]

class BrandResponse(BaseModel):
    brands: List[BrandItem]

class SavedBrandCreate(BaseModel):
    brand_name: str
    industry: str
    target_audience: str
    brand_meaning: str
    tagline: str
    domain_suggestions: List[str]

class SavedBrandResponse(BaseModel):
    id: int
    brand_name: str
    industry: str
    target_audience: str
    brand_meaning: str
    tagline: str
    domain_suggestions: List[str]
    created_at: datetime

    class Config:
        from_attributes = True

# Logo Schemas
class LogoRequest(BaseModel):
    brand_name: str
    industry: str
    style: str
    colors: str
    logo_type: str

class LogoResponse(BaseModel):
    id: int
    brand_name: str
    file_path: str  # URL or path to access the file
    style: str
    colors: str
    logo_type: str
    created_at: datetime

    class Config:
        from_attributes = True

# Content Schemas
class ContentRequest(BaseModel):
    brand_name: str
    industry: str
    tone: str

class ContentDataSchema(BaseModel):
    slogans: List[str]
    brand_stories: List[str]
    product_descriptions: List[str]
    social_media_captions: List[str]
    advertisement_copies: List[str]
    email_marketing_templates: List[Dict[str, str]] # e.g. [{subject: '...', body: '...'}]

class ContentResponse(BaseModel):
    id: int
    brand_name: str
    content_data: ContentDataSchema
    created_at: datetime

    class Config:
        from_attributes = True

# Sentiment Schemas
class SentimentRequest(BaseModel):
    reviews: str

class SentimentResult(BaseModel):
    label: str
    score: float

class EmotionDetection(BaseModel):
    happy: float
    angry: float
    excited: float
    frustrated: float
    satisfied: float

class SentimentResponse(BaseModel):
    positive_percentage: float
    negative_percentage: float
    neutral_percentage: float
    keywords: List[str]
    emotions: EmotionDetection

# Chat Assistant Schemas
class ChatMessage(BaseModel):
    sender: str  # "user" or "assistant"
    message: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage]

class ChatResponse(BaseModel):
    message: str
