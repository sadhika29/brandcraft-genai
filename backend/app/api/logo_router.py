import io
import os
import uuid
import logging
from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from app.database import get_db
from app.models import User, GeneratedLogo
from app.schemas import LogoRequest, LogoResponse
from app.auth import get_current_user
from app.config import UPLOADS_DIR

router = APIRouter(prefix="/api/logo", tags=["logo"])
logger = logging.getLogger(__name__)


def parse_color_to_rgb(color_str: str):
    color_str = (color_str or "").strip().lower().replace("#", "")

    named_colors = {
        "red": (255, 0, 0),
        "green": (0, 180, 80),
        "blue": (0, 100, 220),
        "yellow": (255, 200, 0),
        "cyan": (0, 180, 200),
        "magenta": (220, 0, 150),
        "black": (30, 30, 30),
        "white": (255, 255, 255),
        "orange": (240, 120, 30),
        "purple": (130, 70, 210),
        "pink": (230, 80, 130),
        "peach": (245, 150, 120),
        "gold": (210, 170, 50),
        "rose gold": (183, 110, 121),
        "grey": (128, 128, 128),
        "gray": (128, 128, 128),
        "teal": (0, 140, 140),
        "lavender": (170, 150, 230),
        "violet": (150, 80, 220),
        "indigo": (70, 60, 160),
    }

    if color_str in named_colors:
        return named_colors[color_str]

    try:
        if len(color_str) == 6:
            return tuple(int(color_str[i:i + 2], 16) for i in (0, 2, 4))
        if len(color_str) == 3:
            return tuple(int(c * 2, 16) for c in color_str)
    except Exception:
        pass

    return (201, 117, 138)


def get_theme(color_theme):
    theme = (color_theme or "").lower()

    themes = {
        "pink": ((255, 235, 242), (230, 80, 130), (180, 40, 90)),
        "peach": ((255, 240, 228), (235, 125, 80), (190, 70, 40)),
        "gold": ((255, 249, 225), (210, 170, 50), (145, 110, 20)),
        "rose gold": ((255, 240, 245), (183, 110, 121), (120, 60, 70)),
        "dark": ((35, 35, 42), (220, 90, 130), (255, 210, 220)),
        "blue": ((225, 240, 255), (30, 130, 220), (10, 75, 150)),
        "green": ((225, 250, 235), (35, 170, 90), (15, 105, 55)),
        "purple": ((242, 232, 255), (155, 85, 225), (100, 40, 175)),
    }

    for key, value in themes.items():
        if key in theme:
            return value

    primary = parse_color_to_rgb(color_theme)

    light = tuple(
        int(c * 0.12 + 255 * 0.88)
        for c in primary
    )

    accent = tuple(max(0, int(c * 0.65)) for c in primary)

    return light, primary, accent


def get_font(size, bold=True):
    base = Path(__file__).parent.parent / "assets" / "fonts"

    candidates = [
        base / "DejaVuSans-Bold.ttf" if bold else base / "DejaVuSans.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ]

    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except Exception:
                pass

    return ImageFont.load_default()


def draw_centered(draw, xy, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]

    draw.text(
        (xy[0] - width / 2, xy[1] - height / 2),
        text,
        font=font,
        fill=fill
    )


def draw_procedural_logo(
    brand_name,
    industry,
    style,
    color_theme,
    logo_type,
    seed
):
    img = Image.new("RGB", (800, 800), "white")
    draw = ImageDraw.Draw(img)

    bg_light, primary, accent = get_theme(color_theme)

    style_lower = (style or "").lower()
    dark = seed % 5 == 1

    if dark:
        background = (28, 28, 34)
        text_color = (255, 255, 255)
        secondary = tuple(
            int(primary[i] * 0.6 + 255 * 0.4)
            for i in range(3)
        )
    else:
        background = bg_light
        text_color = accent
        secondary = primary

    draw.rectangle([0, 0, 800, 800], fill=background)

    # Decorative border
    if seed % 3 == 0:
        draw.rounded_rectangle(
            [35, 35, 765, 765],
            radius=35,
            outline=primary,
            width=4
        )

    cx, cy = 400, 285
    design = seed % 8

    initials = "".join(
        word[0] for word in brand_name.split()[:2]
    ).upper()

    if not initials:
        initials = "BC"

    font_initials = get_font(125)
    font_brand = get_font(58)
    font_sub = get_font(24)

    # 1. Circle
    if design == 0:
        draw.ellipse(
            [cx - 135, cy - 135, cx + 135, cy + 135],
            outline=text_color,
            width=8
        )
        draw.ellipse(
            [cx - 110, cy - 110, cx + 110, cy + 110],
            outline=secondary,
            width=3
        )
        draw_centered(
            draw,
            (cx, cy),
            initials,
            font_initials,
            text_color
        )

    # 2. Hexagon
    elif design == 1:
        draw.regular_polygon(
            (cx, cy, 145),
            6,
            rotation=30,
            outline=text_color,
            width=8
        )
        draw.regular_polygon(
            (cx, cy, 115),
            6,
            rotation=30,
            outline=secondary,
            width=3
        )
        draw_centered(
            draw,
            (cx, cy),
            initials,
            get_font(100),
            text_color
        )

    # 3. Diamond
    elif design == 2:
        draw.regular_polygon(
            (cx, cy, 145),
            4,
            rotation=45,
            outline=text_color,
            width=8
        )
        draw.regular_polygon(
            (cx, cy, 110),
            4,
            rotation=45,
            outline=secondary,
            width=3
        )
        draw_centered(
            draw,
            (cx, cy),
            initials,
            get_font(100),
            text_color
        )

    # 4. Shield
    elif design == 3:
        points = [
            (cx - 120, cy - 125),
            (cx + 120, cy - 125),
            (cx + 105, cy + 55),
            (cx, cy + 140),
            (cx - 105, cy + 55)
        ]

        draw.polygon(
            points,
            outline=text_color,
            width=8
        )

        draw.line(
            [(cx, cy - 125), (cx, cy + 120)],
            fill=secondary,
            width=4
        )

        draw_centered(
            draw,
            (cx, cy),
            initials,
            get_font(90),
            text_color
        )

    # 5. Mountain
    elif design == 4:
        draw.polygon(
            [
                (cx - 150, cy + 100),
                (cx, cy - 115),
                (cx + 150, cy + 100)
            ],
            outline=text_color,
            width=8
        )

        draw.polygon(
            [
                (cx - 75, cy + 100),
                (cx, cy - 20),
                (cx + 75, cy + 100)
            ],
            fill=primary
        )

        draw.line(
            [(cx - 165, cy + 120), (cx + 165, cy + 120)],
            fill=text_color,
            width=5
        )

    # 6. Rings
    elif design == 5:
        draw.ellipse(
            [cx - 145, cy - 80, cx + 20, cy + 80],
            outline=primary,
            width=10
        )

        draw.ellipse(
            [cx - 20, cy - 80, cx + 145, cy + 80],
            outline=secondary,
            width=10
        )

        draw_centered(
            draw,
            (cx, cy),
            initials,
            get_font(80),
            text_color
        )

    # 7. Laurel
    elif design == 6:
        draw.arc(
            [cx - 145, cy - 145, cx + 145, cy + 145],
            35,
            325,
            fill=text_color,
            width=5
        )

        for angle in range(45, 330, 25):
            import math
            r = math.radians(angle)

            x = cx + int(135 * math.cos(r))
            y = cy + int(135 * math.sin(r))

            draw.ellipse(
                [x - 14, y - 7, x + 14, y + 7],
                fill=secondary
            )

        draw_centered(
            draw,
            (cx, cy),
            initials,
            get_font(90),
            text_color
        )

    # 8. Square monogram
    else:
        draw.rounded_rectangle(
            [cx - 140, cy - 140, cx + 140, cy + 140],
            radius=20,
            outline=text_color,
            width=8
        )

        draw.rounded_rectangle(
            [cx - 115, cy - 115, cx + 115, cy + 115],
            radius=15,
            outline=secondary,
            width=3
        )

        draw_centered(
            draw,
            (cx, cy),
            initials,
            font_initials,
            text_color
        )

    # Brand name
    brand = (brand_name or "BrandCraft").strip()

    # Automatically reduce font for long names
    brand_size = 58

    if len(brand) > 16:
        brand_size = 45
    if len(brand) > 24:
        brand_size = 35

    font_brand = get_font(brand_size)

    draw_centered(
        draw,
        (400, 555),
        brand,
        font_brand,
        text_color
    )

    # Industry
    industry_text = (industry or "BRAND").upper()

    draw_centered(
        draw,
        (400, 625),
        industry_text[:32],
        font_sub,
        secondary
    )

    # Decorative divider
    draw.line(
        [(150, 625), (270, 625)],
        fill=text_color,
        width=2
    )

    draw.line(
        [(530, 625), (650, 625)],
        fill=text_color,
        width=2
    )

    return img


def create_logo_bytes(req, seed):
    img = draw_procedural_logo(
        req.brand_name,
        req.industry,
        req.style,
        req.colors,
        req.logo_type,
        seed
    )

    buffer = io.BytesIO()
    img.save(buffer, "PNG", optimize=True)
    buffer.seek(0)

    return buffer.getvalue()


@router.post("/generate", response_model=List[LogoResponse])
async def generate_logos(
    req: LogoRequest,
    count: int = Query(default=30, ge=30, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    os.makedirs(UPLOADS_DIR, exist_ok=True)

    logo_list = []

    try:
        for i in range(count):
            img_bytes = create_logo_bytes(req, i)

            filename = f"logo_{uuid.uuid4().hex}.png"
            abs_file_path = os.path.join(UPLOADS_DIR, filename)

            with open(abs_file_path, "wb") as f:
                f.write(img_bytes)

            db_logo = GeneratedLogo(
                user_id=current_user.id,
                brand_name=req.brand_name,
                file_path=f"backend/uploads/{filename}",
                style=req.style,
                colors=req.colors,
                logo_type=req.logo_type
            )

            db.add(db_logo)
            logo_list.append(db_logo)

        db.commit()

        for logo in logo_list:
            db.refresh(logo)

        return logo_list

    except Exception as e:
        db.rollback()
        logger.exception("Logo generation failed")

        raise HTTPException(
            status_code=500,
            detail=f"Logo generation failed: {str(e)}"
        )


@router.get("/gallery", response_model=List[LogoResponse])
def get_gallery(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return (
        db.query(GeneratedLogo)
        .filter(GeneratedLogo.user_id == current_user.id)
        .order_by(GeneratedLogo.created_at.desc())
        .all()
    )


@router.delete("/delete/{logo_id}")
def delete_logo(
    logo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logo = (
        db.query(GeneratedLogo)
        .filter(
            GeneratedLogo.id == logo_id,
            GeneratedLogo.user_id == current_user.id
        )
        .first()
    )

    if not logo:
        raise HTTPException(
            status_code=404,
            detail="Logo not found"
        )

    from app.config import BASE_DIR

    file_path = BASE_DIR.parent / logo.file_path

    if file_path.exists():
        try:
            file_path.unlink()
        except Exception:
            pass

    db.delete(logo)
    db.commit()

    return {"message": "Logo deleted successfully"}


@router.get("/download/{logo_id}/{img_format}")
def download_logo(
    logo_id: int,
    img_format: str,
    db: Session = Depends(get_db)
):
    logo = (
        db.query(GeneratedLogo)
        .filter(GeneratedLogo.id == logo_id)
        .first()
    )

    if not logo:
        raise HTTPException(
            status_code=404,
            detail="Logo asset not found"
        )

    from app.config import BASE_DIR

    file_path = BASE_DIR.parent / logo.file_path

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Logo file not found on server"
        )

    img_format = img_format.lower()
    safe_name = logo.brand_name.replace(" ", "_")

    if img_format == "png":
        return FileResponse(
            str(file_path),
            media_type="image/png",
            filename=f"{safe_name}_logo.png"
        )

    if img_format in ("jpg", "jpeg"):
        try:
            img = Image.open(file_path).convert("RGB")

            buffer = io.BytesIO()
            img.save(buffer, "JPEG", quality=95)
            buffer.seek(0)

            return StreamingResponse(
                buffer,
                media_type="image/jpeg",
                headers={
                    "Content-Disposition":
                        f'attachment; filename="{safe_name}_logo.jpg"'
                }
            )

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to convert logo to JPEG: {e}"
            )

    if img_format == "pdf":
        try:
            buffer = io.BytesIO()

            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=50,
                leftMargin=50,
                topMargin=50,
                bottomMargin=50
            )

            styles = getSampleStyleSheet()

            title_style = ParagraphStyle(
                "TitleStyle",
                parent=styles["Title"],
                fontName="Helvetica-Bold",
                fontSize=26,
                leading=30,
                textColor=colors.HexColor("#d81b60"),
                alignment=1,
                spaceAfter=15
            )

            meta_style = ParagraphStyle(
                "MetaStyle",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=11,
                leading=15,
                textColor=colors.HexColor("#555555"),
                alignment=1
            )

            elements = [
                Paragraph("BrandCraft Identity Sheet", title_style),
                Paragraph(
                    f"<b>Brand:</b> {logo.brand_name} | "
                    f"<b>Style:</b> {logo.style} | "
                    f"<b>Type:</b> {logo.logo_type}",
                    meta_style
                ),
                Spacer(1, 20),
                RLImage(
                    str(file_path),
                    width=300,
                    height=300
                ),
                Spacer(1, 20)
            ]

            spec_data = [
                ["Property", "Value"],
                ["Brand Name", logo.brand_name],
                ["Industry / Type", logo.logo_type],
                ["Colors", logo.colors],
                ["Style", logo.style],
                [
                    "Generated Date",
                    logo.created_at.strftime("%Y-%m-%d %H:%M:%S")
                ]
            ]

            table = Table(
                spec_data,
                colWidths=[150, 250]
            )

            table.setStyle(
                TableStyle([
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#ffe5ec")
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#d81b60")
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold"
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor("#dddddd")
                    ),
                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "CENTER"
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE"
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        8
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        8
                    )
                ])
            )

            elements.append(table)

            doc.build(elements)
            buffer.seek(0)

            return StreamingResponse(
                buffer,
                media_type="application/pdf",
                headers={
                    "Content-Disposition":
                        f'attachment; filename="{safe_name}_identity_sheet.pdf"'
                }
            )

        except Exception as e:
            logger.exception("PDF generation failed")

            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate PDF: {e}"
            )

    raise HTTPException(
        status_code=400,
        detail=f"Unsupported download format '{img_format}'"
    )