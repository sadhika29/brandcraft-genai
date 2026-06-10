import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True)
    reset_token = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    brands = relationship("SavedBrand", back_populates="user", cascade="all, delete-orphan")
    logos = relationship("GeneratedLogo", back_populates="user", cascade="all, delete-orphan")
    contents = relationship("SavedContent", back_populates="user", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessageDB", back_populates="user", cascade="all, delete-orphan")

class SavedBrand(Base):
    __tablename__ = "saved_brands"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    brand_name = Column(String, nullable=False)
    industry = Column(String, nullable=False)
    target_audience = Column(String, nullable=False)
    brand_meaning = Column(Text, nullable=False)
    tagline = Column(String, nullable=False)
    domain_suggestions = Column(Text, nullable=False)  # Stores domain suggestions in JSON format
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="brands")

class GeneratedLogo(Base):
    __tablename__ = "generated_logos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    brand_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    style = Column(String, nullable=False)
    colors = Column(String, nullable=False)
    logo_type = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="logos")

class SavedContent(Base):
    __tablename__ = "saved_contents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    brand_name = Column(String, nullable=False)
    content_data = Column(Text, nullable=False)  # Stores the full generated JSON content bundle
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="contents")

class ChatMessageDB(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String, nullable=False)  # "user" or "assistant"
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="chat_messages")
