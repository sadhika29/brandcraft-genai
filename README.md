# BrandCraft – Generative AI Powered Branding Automation System

BrandCraft is a production-style branding platform designed to help startups, entrepreneurs, creators, and small businesses create a complete brand identity using AI. The application features a premium Glassmorphism Single Page Application (SPA) frontend and a FastAPI backend with integrated SQLite database persistence.

## Key Features
1. **User Authentication System**: JWT token verification, password hashing with bcrypt, SMTP email configuration for verification, and forgot password flows.
2. **Brand Name Generator**: Generates 30 to 50 brand names, tagline recommendations, brand meanings, and matching domain suggestions using **Gemini API**.
3. **AI Logo Generator**: Creates batches of 8 to 12 logos based on selected styling, colors, and industry blueprints. Uses **Stable Diffusion XL** via Hugging Face and contains a custom procedural fallback logo designer that draws unique vector monogram assets using **Pillow**. Supports PNG, JPEG, and multi-element PDF sheet compilation via **ReportLab**.
4. **Content Automation Kit**: Instantly automates 50+ slogans, 10 brand stories, 20 product descriptions, 20 social media captions, 10 ad copies, and 10 email templates using **Gemini API**.
5. **Review Sentiment Tracker**: Runs lexicon-based customer feedback evaluation to produce positive/negative sentiment ratios, dynamic SVG charts, multi-label emotion categorization (Happy, Angry, Excited, Frustrated, Satisfied), and keyword extractions.
6. **BrandCraft AI Assistant**: A conversational marketing chatbot powered by **Gemini API** that strictly enforces branding-specific discussion filters and suggestions.

---

## Directory Structure

```
buildwise_genai/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── auth_router.py
│   │   │   ├── generator_router.py
│   │   │   ├── logo_router.py
│   │   │   ├── content_router.py
│   │   │   ├── sentiment_router.py
│   │   │   └── assistant_router.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── auth.py
│   │   ├── mail.py
│   │   └── main.py
│   ├── uploads/
│   ├── .env
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── venv/
└── README.md
```

---

## Installation and Setup

### Prerequisites
- Python 3.11 or Python 3.12 installed on your system.

### 1. Configure Environment Variables
Inside the `backend/` folder, a default `.env` file is pre-configured for local testing. To enable live AI services and SMTP mail verification, open `backend/.env` and fill in the values:
```env
GEMINI_API_KEY=your_gemini_api_key_here
HUGGINGFACE_API_KEY=your_huggingface_api_key_here

# SMTP Configuration (Optional - e.g. Mailtrap or Brevo)
SMTP_HOST=sandbox.smtp.mailtrap.io
SMTP_PORT=2525
SMTP_USER=your_smtp_username
SMTP_PASSWORD=your_smtp_password
SMTP_FROM=noreply@brandcraft.ai
```
*Note: If no API keys are supplied, the system operates in a **graceful fallback mode**, procedurally generating mock data and vector logo shapes so the entire application interface can be fully explored without external connections.*

### 2. Run the Server
Activate your virtual environment and start the Uvicorn development server:

**Windows PowerShell:**
```powershell
.\venv\Scripts\activate
uvicorn app.main:app --reload
```

**Linux / macOS Terminal:**
```bash
source venv/bin/activate
uvicorn app.main:app --reload
```

### 3. Open the Application
Navigate to [http://127.0.0.1:8000](http://127.0.0.1:8000) in your web browser.

---

## Developer Verification Tips
- **Email Verification Fallback**: When registering a new account, check the terminal logs where uvicorn is running. The email service prints the raw verification HTML containing the activation link. Copy and paste it into your browser to activate the account.
- **Sentiment Tracker SVG Chart**: The positive feedback ratio dynamically updates the stroke dash offsets of the SVG circular gauge chart on the Sentiment dashboard.
- **Logo Spec PDF**: The PDF download button utilizes ReportLab to generate print-ready grid tables listing the metadata specs of the generated logo.
