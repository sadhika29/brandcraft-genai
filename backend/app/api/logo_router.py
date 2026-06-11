import io
import os
import uuid
import logging
import asyncio
import random
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
import httpx
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

from app.database import get_db
from app.models import User, GeneratedLogo
from app.schemas import LogoRequest, LogoResponse
from app.auth import get_current_user
from app.config import HUGGINGFACE_API_KEY, HAS_HF_KEY, UPLOADS_DIR

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

router = APIRouter(prefix="/api/logo", tags=["logo"])
logger = logging.getLogger(__name__)

HF_SDXL_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"

def parse_color_to_rgb(color_str: str) -> tuple:
    color_str = color_str.strip().lower().replace("#", "")
    named_colors = {
        "red": (255, 0, 0),
        "green": (0, 255, 0),
        "blue": (0, 0, 255),
        "yellow": (255, 255, 0),
        "cyan": (0, 255, 255),
        "magenta": (255, 0, 255),
        "black": (0, 0, 0),
        "white": (255, 255, 255),
        "orange": (255, 165, 0),
        "purple": (128, 0, 128),
        "pink": (255, 192, 203),
        "peach": (255, 218, 185),
        "gold": (255, 215, 0),
        "rose gold": (183, 110, 121),
        "grey": (128, 128, 128),
        "gray": (128, 128, 128),
        "teal": (0, 128, 128),
        "lavender": (230, 230, 250),
        "violet": (238, 130, 238),
        "indigo": (75, 0, 130),
    }
    if color_str in named_colors:
        return named_colors[color_str]
    
    # Try parsing hex
    try:
        if len(color_str) == 6:
            return (int(color_str[0:2], 16), int(color_str[2:4], 16), int(color_str[4:6], 16))
        elif len(color_str) == 3:
            return (int(color_str[0]*2, 16), int(color_str[1]*2, 16), int(color_str[2]*2, 16))
    except Exception:
        pass
    
    # Fallback to a default rose color
    return (216, 27, 96)

def draw_procedural_logo(brand_name: str, industry: str, style: str, color_theme: str, logo_type: str, seed: int) -> Image.Image:
    """Generates a premium styled logo procedurally using Pillow. Highly varied designs based on seed (0-9)."""
    # Setup canvas (800x800 for high resolution)
    img = Image.new("RGBA", (800, 800), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Parse color theme
    color_map = {
        "pink": ((255, 229, 236), (255, 128, 150), (216, 27, 96)),
        "peach": ((255, 235, 220), (255, 180, 140), (230, 90, 40)),
        "gold": ((255, 248, 220), (212, 175, 55), (140, 110, 20)),
        "rose gold": ((255, 240, 245), (183, 110, 121), (120, 60, 70)),
        "dark": ((30, 30, 36), (60, 60, 72), (216, 27, 96)),
        "blue": ((224, 242, 254), (14, 165, 233), (3, 105, 161)),
        "green": ((220, 252, 231), (34, 197, 94), (21, 128, 61)),
        "purple": ((243, 232, 255), (168, 85, 247), (109, 40, 217)),
    }
    
    color_key = color_theme.lower()
    selected_theme = None
    for k, v in color_map.items():
        if k in color_key:
            selected_theme = v
            break
            
    if selected_theme is not None:
        bg_light, primary_color, accent_color = selected_theme
    else:
        # Dynamically generate theme from custom user-chosen color
        primary_color = parse_color_to_rgb(color_theme)
        bg_light = (
            int(primary_color[0] * 0.12 + 255 * 0.88),
            int(primary_color[1] * 0.12 + 255 * 0.88),
            int(primary_color[2] * 0.12 + 255 * 0.88)
        )
        accent_color = (
            max(0, int(primary_color[0] * 0.65)),
            max(0, int(primary_color[1] * 0.65)),
            max(0, int(primary_color[2] * 0.65))
        )
    
    # 1. VARIED BACKGROUND DESIGNS (0-3 styles)
    bg_style = seed % 4
    if bg_style == 0:
        # Diagonal Linear Gradient (Elegant transition)
        for y in range(800):
            blend = y / 800.0
            r = int(bg_light[0] * (1 - blend) + 255 * blend)
            g = int(bg_light[1] * (1 - blend) + 255 * blend)
            b = int(bg_light[2] * (1 - blend) + 255 * blend)
            draw.line([(0, y), (800, y)], fill=(r, g, b, 255))
    elif bg_style == 1:
        # Solid Dark metallic background
        dark_color = (20, 20, 24, 255)
        draw.rectangle([0, 0, 800, 800], fill=dark_color)
        # Add subtle inner border
        draw.rectangle([15, 15, 785, 785], fill=None, outline=(primary_color[0], primary_color[1], primary_color[2], 80), width=2)
    elif bg_style == 2:
        # Clean white background with premium double outer border
        draw.rectangle([0, 0, 800, 800], fill=(255, 255, 255, 255))
        draw.rectangle([25, 25, 775, 775], fill=None, outline=accent_color, width=4)
        draw.rectangle([35, 35, 765, 765], fill=None, outline=primary_color, width=1)
    else:
        # Radial Gradient (Simulated center glow)
        cx, cy = 400, 400
        for r_val in range(600, 0, -3):
            blend = r_val / 600.0
            r = int(bg_light[0] * blend + 255 * (1 - blend))
            g = int(bg_light[1] * blend + 255 * (1 - blend))
            b = int(bg_light[2] * blend + 255 * (1 - blend))
            draw.ellipse([cx-r_val, cy-r_val, cx+r_val, cy+r_val], fill=(r, g, b, 255))

    # Determine colors to use for foreground based on background brightness
    is_dark_bg = (bg_style == 1)
    text_color = accent_color if not is_dark_bg else bg_light
    sub_color = primary_color if not is_dark_bg else primary_color
    if is_dark_bg:
        text_color = (255, 255, 255)
        sub_color = (int(primary_color[0] * 0.4 + 255 * 0.6), int(primary_color[1] * 0.4 + 255 * 0.6), int(primary_color[2] * 0.4 + 255 * 0.6))
        
    initials = brand_name[:2].upper() if len(brand_name) >= 2 else brand_name[:1].upper()
    
    # Fonts loading fallback
    BUNDLED_FONT = Path(__file__).parent.parent / "assets" / "fonts" / "DejaVuSans.ttf"

    is_serif = (seed % 2 == 0) or ("luxury" in style.lower()) or ("vintage" in style.lower())

    serif_candidates = [
        str(BUNDLED_FONT),
        "C:\\Windows\\Fonts\\Georgia.ttf",
        "C:\\Windows\\Fonts\\cambriab.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    ]
    sans_candidates = [
        str(BUNDLED_FONT),
        "C:\\Windows\\Fonts\\segoeuib.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]

    selected_font = None
    for path in (serif_candidates if is_serif else sans_candidates):
        if os.path.exists(path):
            selected_font = path
            break

    try:
        font_initials = ImageFont.truetype(selected_font, 180)
        font_brand = ImageFont.truetype(selected_font, 85)
        font_sub = ImageFont.truetype(selected_font, 28)
    except Exception:
        font_initials = ImageFont.load_default()
        font_brand = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    cx, cy = 400, 290
    
    # 2. DRASTICALLY VARIED FOREGROUND ICON DESIGNS (0-9)
    design_type = seed % 10
    
    if design_type == 0:
        # Classical Circular Monogram Crest (Luxury Style)
        draw.ellipse([cx-140, cy-140, cx+140, cy+140], fill=None, outline=text_color, width=6)
        draw.ellipse([cx-125, cy-125, cx+125, cy+125], fill=None, outline=sub_color, width=2)
        # Decorative stars around the ring
        import math
        for star_idx in range(12):
            angle = star_idx * (360 / 12)
            rad = math.radians(angle)
            sx = cx + int(132 * math.cos(rad))
            sy = cy + int(132 * math.sin(rad))
            # Draw a star-like diamond
            draw.polygon([(sx, sy-6), (sx+4, sy), (sx, sy+6), (sx-4, sy)], fill=sub_color)
        draw.text((cx, cy - 10), initials, fill=text_color, anchor="mm", font=font_initials)
        
    elif design_type == 1:
        # Modern Hexagon Circuit Tech Badge
        draw.regular_polygon((cx, cy, 140), 6, rotation=30, fill=None, outline=text_color, width=8)
        draw.regular_polygon((cx, cy, 115), 6, rotation=30, fill=None, outline=sub_color, width=2)
        # Circuit connections
        draw.line([(cx-121, cy-70), (cx-150, cy-100)], fill=text_color, width=4)
        draw.ellipse([cx-156, cy-106, cx-144, cy-94], fill=text_color)
        draw.line([(cx+121, cy+70), (cx+150, cy+100)], fill=text_color, width=4)
        draw.ellipse([cx+144, cy+94, cx+156, cy+106], fill=text_color)
        draw.text((cx, cy - 10), initials, fill=text_color, anchor="mm", font=font_initials)
        
    elif design_type == 2:
        # Overlapping Venn Rings (Modern SaaS / Innovation Style)
        # Transparent overlapping rings
        r_col = (primary_color[0], primary_color[1], primary_color[2], 120)
        a_col = (accent_color[0], accent_color[1], accent_color[2], 120)
        draw.ellipse([cx-110, cy-70, cx+20, cy+60], fill=r_col, outline=text_color, width=4)
        draw.ellipse([cx-20, cy-60, cx+110, cy+70], fill=a_col, outline=sub_color, width=4)
        # Center core shield
        draw.ellipse([cx-45, cy-45, cx+45, cy+45], fill=(255, 255, 255, 230), outline=text_color, width=2)
        try:
            icon_font = ImageFont.truetype(selected_font, 65)
        except Exception:
            icon_font = font_sub
        draw.text((cx, cy), initials, fill=text_color, anchor="mm", font=icon_font)
        
    elif design_type == 3:
        # Botanical Laurel Wreath (Wellness / Life Style)
        # Draw laurel branch paths
        draw.arc([cx-130, cy-130, cx+130, cy+130], start=35, end=325, fill=text_color, width=4)
        # Draw leaves
        import math
        for angle_deg in range(40, 330, 25):
            rad = math.radians(angle_deg)
            lx = cx + int(130 * math.cos(rad))
            ly = cy + int(130 * math.sin(rad))
            # Leaf rotation vectors
            nx = int(16 * math.cos(rad + 0.5))
            ny = int(16 * math.sin(rad + 0.5))
            draw.ellipse([lx-nx-6, ly-ny-6, lx+nx+6, ly+ny+6], fill=sub_color)
        # Draw central rosebud or leaf crest
        draw.polygon([(cx, cy-80), (cx+30, cy-30), (cx, cy+20), (cx-30, cy-30)], fill=text_color)
        draw.ellipse([cx-15, cy-40, cx+15, cy-10], fill=sub_color)
        
    elif design_type == 4:
        # Mountain Peak / Geometric Triangle (Adventure / Tech Style)
        # Glow background sun
        draw.ellipse([cx-60, cy-80, cx+60, cy+40], fill=sub_color)
        # Draw 3 nested peaks
        draw.polygon([(cx-140, cy+100), (cx-40, cy-80), (cx+60, cy+100)], fill=(accent_color[0], accent_color[1], accent_color[2], 180), outline=text_color, width=4)
        draw.polygon([(cx-60, cy+100), (cx+40, cy-60), (cx+140, cy+100)], fill=(primary_color[0], primary_color[1], primary_color[2], 220), outline=text_color, width=4)
        draw.polygon([(cx-100, cy+100), (cx, cy-100), (cx+100, cy+100)], fill=None, outline=text_color, width=6)
        # Horizontal base cut lines
        draw.line([(cx-160, cy+115), (cx+160, cy+115)], fill=text_color, width=4)
        
    elif design_type == 5:
        # Rotated Diamond Badge (Vintage Style)
        draw.regular_polygon((cx, cy, 140), 4, rotation=45, fill=None, outline=text_color, width=8)
        draw.regular_polygon((cx, cy, 120), 4, rotation=45, fill=None, outline=sub_color, width=2)
        # Horizontal ribbon belt
        draw.rectangle([cx-150, cy-35, cx+150, cy+35], fill=text_color)
        draw.rectangle([cx-140, cy-25, cx+140, cy+25], fill=None, outline=bg_light if not is_dark_bg else bg_light, width=2)
        try:
            ribbon_font = ImageFont.truetype(selected_font, 50)
        except Exception:
            ribbon_font = font_sub
        draw.text((cx, cy), initials, fill=bg_light if not is_dark_bg else (20, 20, 24), anchor="mm", font=ribbon_font)
        
    elif design_type == 6:
        # Isometric Technology Cube Wireframe
        # Draw isometric wire lines
        pts = [
            (cx, cy-120), (cx+110, cy-60), (cx+110, cy+60),
            (cx, cy+120), (cx-110, cy+60), (cx-110, cy-60)
        ]
        draw.polygon(pts, fill=None, outline=text_color, width=6)
        # Internal cube struts
        draw.line([(cx, cy-120), (cx, cy+120)], fill=text_color, width=4)
        draw.line([(cx, cy), (cx+110, cy-60)], fill=sub_color, width=4)
        draw.line([(cx, cy), (cx-110, cy-60)], fill=sub_color, width=4)
        # Vertex terminals (nodes)
        for pt in pts + [(cx, cy), (cx, cy-120), (cx, cy+120)]:
            draw.ellipse([pt[0]-10, pt[1]-10, pt[0]+10, pt[1]+10], fill=sub_color, outline=text_color, width=2)
            
    elif design_type == 7:
        # Traditional Quartered Heraldic Shield Crest
        shield_pts = [
            (cx - 120, cy - 130), (cx + 120, cy - 130),
            (cx + 120, cy + 10), (cx, cy + 140),
            (cx - 120, cy + 10)
        ]
        draw.polygon(shield_pts, fill=None, outline=text_color, width=8)
        # Quadrant lines
        draw.line([(cx, cy-130), (cx, cy+140)], fill=sub_color, width=3)
        draw.line([(cx-120, cy+10), (cx+120, cy+10)], fill=sub_color, width=3)
        # Small star toppers
        draw.polygon([(cx, cy-160), (cx+12, cy-142), (cx, cy-150), (cx-12, cy-142)], fill=text_color)
        draw.text((cx, cy - 50), initials, fill=text_color, anchor="mm", font=font_sub)
        
    elif design_type == 8:
        # Infinite Ribbon Wreath (Modern Abstract Loop)
        r_col = (primary_color[0], primary_color[1], primary_color[2], 140)
        a_col = (accent_color[0], accent_color[1], accent_color[2], 140)
        # 3 nested rotated oval ellipses
        draw.ellipse([cx-140, cy-70, cx+140, cy+70], fill=None, outline=r_col, width=8)
        draw.ellipse([cx-70, cy-140, cx+70, cy+140], fill=None, outline=a_col, width=8)
        # Intersection dots
        draw.ellipse([cx-8, cy-8, cx+8, cy+8], fill=text_color)
        try:
            icon_font = ImageFont.truetype(selected_font, 90)
        except Exception:
            icon_font = font_sub
        draw.text((cx, cy - 5), initials, fill=text_color, anchor="mm", font=icon_font)
        
    else:
        # Typographic Crest Badge
        draw.rectangle([cx-120, cy-120, cx+120, cy+120], fill=None, outline=text_color, width=8)
        draw.rectangle([cx-105, cy-105, cx+105, cy+105], fill=None, outline=sub_color, width=2)
        # Corner diamonds
        for offset in [-120, 120]:
            draw.polygon([(cx+offset, cy-6), (cx+offset+6, cy), (cx+offset, cy+6), (cx+offset-6, cy)], fill=text_color)
            draw.polygon([(cx, cy+offset-6), (cx+6, cy+offset), (cx, cy+offset+6), (cx-6, cy+offset)], fill=text_color)
        draw.text((cx, cy - 10), initials, fill=text_color, anchor="mm", font=font_initials)

    # 3. TEXT POSITIONS
    text_y = 550
    # Render Brand Name (Bold, clear, and prominent)
    draw.text((cx, text_y), brand_name, fill=text_color, anchor="mm", font=font_brand)
    
    # Subtitle (Industry / Tagline)
    sub_text = industry.upper()
    draw.text((cx, text_y + 70), sub_text, fill=sub_color, anchor="mm", font=font_sub)
    
    # Elegant divider accents flanking the subtitle text
    draw.line([(cx-230, text_y + 70), (cx-110, text_y + 70)], fill=text_color, width=2)
    draw.line([(cx+110, text_y + 70), (cx+230, text_y + 70)], fill=text_color, width=2)

    return img

async def generate_sd_logo(prompt: str, seed: int) -> bytes:
    """Queries Hugging Face serverless Stable Diffusion XL endpoint."""
    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
        "X-Use-Cache": "false"
    }
    payload = {
        "inputs": prompt,
        "parameters": {
            "seed": seed
        }
    }
    
    async with httpx.AsyncClient(timeout=45.0) as client:
        response = await client.post(HF_SDXL_URL, headers=headers, json=payload)
        if response.status_code != 200:
            raise Exception(f"HF API Error: {response.text}")
        return response.content

async def generate_single_logo_image(i: int, req: LogoRequest) -> bytes:
    # Directly use procedural Pillow generator to load instantly (under 10ms per logo)
    loop = asyncio.get_running_loop()
    img = await loop.run_in_executor(
        None,
        draw_procedural_logo,
        req.brand_name,
        req.industry,
        req.style,
        req.colors,
        req.logo_type,
        i
    )
    buffer = io.BytesIO()
    img.save(buffer, "PNG")
    return buffer.getvalue()

@router.post("/generate", response_model=List[LogoResponse])
async def generate_logos(
    req: LogoRequest,
    count: int = Query(default=30, ge=30, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Fire all generation tasks in parallel
    tasks = [generate_single_logo_image(i, req) for i in range(count)]
    
    # Run in parallel and wait for all to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    logo_list = []
    
    # Process results sequentially to write files and stage database models
    for i, res in enumerate(results):
        logo_uuid = str(uuid.uuid4())
        filename = f"logo_{logo_uuid}.png"
        file_path = os.path.join("backend", "uploads", filename)
        abs_file_path = os.path.join(UPLOADS_DIR, filename)
        
        success = False
        img_bytes = None
        
        if not isinstance(res, Exception) and res is not None:
            img_bytes = res
            success = True
        else:
            logger.error(f"Logo generation task {i+1} failed with exception: {res}. Using immediate local Pillow fallback.")
            try:
                img = draw_procedural_logo(
                    brand_name=req.brand_name,
                    industry=req.industry,
                    style=req.style,
                    color_theme=req.colors,
                    logo_type=req.logo_type,
                    seed=i
                )
                buffer = io.BytesIO()
                img.save(buffer, "PNG")
                img_bytes = buffer.getvalue()
                success = True
            except Exception as e:
                logger.error(f"Synchronous Pillow fallback failed for variant {i+1}: {e}")
                
        if success and img_bytes:
            try:
                with open(abs_file_path, "wb") as f:
                    f.write(img_bytes)
                
                db_logo = GeneratedLogo(
                    user_id=current_user.id,
                    brand_name=req.brand_name,
                    file_path=file_path,
                    style=req.style,
                    colors=req.colors,
                    logo_type=req.logo_type
                )
                db.add(db_logo)
                logo_list.append(db_logo)
            except Exception as e:
                logger.error(f"Failed to write logo {i+1} file or stage to DB: {e}")
                
    # Commit all staged database records in a single transaction
    try:
        db.commit()
        for logo in logo_list:
            db.refresh(logo)
    except Exception as e:
        logger.error(f"Failed to commit logos to database: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save generated logos to database.")
        
    if not logo_list:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate any logos."
        )
        
    return logo_list

@router.get("/gallery", response_model=List[LogoResponse])
def get_gallery(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    logos = db.query(GeneratedLogo).filter(GeneratedLogo.user_id == current_user.id).order_by(GeneratedLogo.created_at.desc()).all()
    return logos

@router.delete("/delete/{logo_id}")
def delete_logo(logo_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    logo = db.query(GeneratedLogo).filter(GeneratedLogo.id == logo_id, GeneratedLogo.user_id == current_user.id).first()
    if not logo:
        raise HTTPException(status_code=404, detail="Logo not found")
        
    # Delete local file if it exists
    from app.config import BASE_DIR
    full_path = BASE_DIR.parent / logo.file_path
    if full_path.exists():
        try:
            full_path.unlink()
        except Exception as e:
            logger.error(f"Could not delete file {full_path}: {e}")
            
    db.delete(logo)
    db.commit()
    return {"message": "Logo deleted successfully"}

@router.get("/download/{logo_id}/{img_format}")
def download_logo(logo_id: int, img_format: str, db: Session = Depends(get_db)):
    # Serve without auth dependency so download links are simple standard links in browser
    logo = db.query(GeneratedLogo).filter(GeneratedLogo.id == logo_id).first()
    if not logo:
        raise HTTPException(status_code=404, detail="Logo asset not found")
        
    from app.config import BASE_DIR
    file_path = BASE_DIR.parent / logo.file_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Logo file not found on server disk")
        
    img_format = img_format.lower()
    
    # 1. Return PNG
    if img_format == "png":
        return FileResponse(
            path=str(file_path),
            media_type="image/png",
            filename=f"{logo.brand_name.replace(' ', '_')}_logo.png"
        )
        
    # 2. Return JPG
    elif img_format == "jpg" or img_format == "jpeg":
        try:
            img = Image.open(file_path)
            # Convert RGBA to RGB for JPEG save
            if img.mode == "RGBA":
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3]) # 3 is alpha channel
                img = background
            else:
                img = img.convert("RGB")
                
            buffer = io.BytesIO()
            img.save(buffer, "JPEG", quality=95)
            buffer.seek(0)
            return StreamingResponse(
                buffer,
                media_type="image/jpeg",
                headers={"Content-Disposition": f"attachment; filename={logo.brand_name.replace(' ', '_')}_logo.jpg"}
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to convert logo to JPEG: {e}")
            
    # 3. Compile ReportLab PDF sheet
    elif img_format == "pdf":
        try:
            buffer = io.BytesIO()
            # Standard Letter page
            doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
            
            # Setup styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                name="TitleStyle",
                parent=styles["Title"],
                fontName="Helvetica-Bold",
                fontSize=26,
                leading=30,
                textColor=colors.HexColor("#d81b60"),
                spaceAfter=15
            )
            meta_style = ParagraphStyle(
                name="MetaStyle",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=12,
                leading=16,
                textColor=colors.HexColor("#555555"),
                alignment=1 # Center
            )
            
            elements = []
            
            # Add Brand Header
            elements.append(Paragraph(f"BrandCraft Identity Sheet", title_style))
            elements.append(Paragraph(f"<b>Brand Name:</b> {logo.brand_name} | <b>Style:</b> {logo.style} | <b>Logo Type:</b> {logo.logo_type}", meta_style))
            elements.append(Spacer(1, 20))
            
            # Add logo image (resized for PDF grid - 350x350pt)
            logo_width, logo_height = 300, 300
            elements.append(RLImage(str(file_path), width=logo_width, height=logo_height))
            elements.append(Spacer(1, 20))
            
            # Add decorative border and specifications grid
            spec_data = [
                ["Property", "Value"],
                ["Brand Name", logo.brand_name],
                ["Associated Industry", logo.logo_type],
                ["Selected Colors", logo.colors],
                ["Aesthetic Style", logo.style],
                ["Generated Date", logo.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")]
            ]
            t = Table(spec_data, colWidths=[150, 250])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#ffe5ec")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#d81b60")),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('TOPPADDING', (0,0), (-1,-1), 8),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#ffe5ec")),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            elements.append(t)
            
            doc.build(elements)
            buffer.seek(0)
            return StreamingResponse(
                buffer,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={logo.brand_name.replace(' ', '_')}_identity_sheet.pdf"}
            )
        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to compile PDF Identity Sheet: {e}")
            
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported download format '{img_format}'")
