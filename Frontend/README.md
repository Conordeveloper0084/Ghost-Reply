# Ghost Reply - Web Login Interface

Complete web interface for Ghost Reply Telegram bot with beautiful blue gradient design.

## Overview

This is a fully integrated web login system for the Ghost Reply bot that allows users to authenticate their Telegram accounts directly through a beautiful, responsive web interface. All templates are embedded directly in the FastAPI backend - no separate HTML files needed!

## Features

- Beautiful blue gradient design matching Ghost Reply logo
- Fully responsive and mobile-friendly
- Complete Telegram authentication flow (phone, code, 2FA)
- Loading states and inline error messages
- Multi-page navigation (Login, About, Pricing, Security)
- Professional pricing page with discount badges
- All templates embedded in backend (no external HTML files required)

## Installation

### 1. Update Your FastAPI Application

Add the web_login router to your main FastAPI app:

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from backend.web_login import router as web_login_router

app = FastAPI()

# Mount static files for logo image
app.mount("/images", StaticFiles(directory="public/images"), name="images")

# Include the web login router
app.include_router(web_login_router)
```

### 2. Add Logo Image

Place your Ghost Reply logo at:
```
public/images/image-202025-12-16-2023-3a15-3a08.jpg
```

### 3. Configure Environment Variables

Make sure your FastAPI app has these environment variables:
```
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
```

### 4. Run the Application

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Available Routes

### Login Flow
- `GET /web-login/start` - Phone number input page
- `POST /web-login/start` - Submit phone number
- `POST /web-login/code` - Submit verification code
- `POST /web-login/2fa` - Submit 2FA password (if required)

### Information Pages
- `GET /web-login/about` - About the bot
- `GET /web-login/pricing` - Pricing plans
- `GET /web-login/security` - Privacy and security information

## Pages Overview

### Bosh sahifa (Home/Login)
Complete Telegram authentication flow:
1. Phone number input with validation
2. Code verification with loading state
3. 2FA password (if enabled on account)
4. Success screen

### Bot haqida (About)
Information about Ghost Reply bot features and capabilities.

### Tariflar (Pricing)
Three pricing tiers:
- **Free**: 3 triggers and responses
- **Pro**: 10 triggers and responses - 21,900 UZS (27% discount)
- **Premium**: 20 triggers and responses - 36,000 UZS (28% discount)

### Xavfsizlik (Security)
Privacy and security information about data handling.

## Design Features

- Beautiful blue gradient background (#1e3c72 → #2a5298 → #7e8ba3)
- Glass-morphism effects with backdrop blur
- Smooth animations and transitions
- Responsive navigation with mobile menu
- Professional form styling with focus states
- Loading spinners during API calls
- Color-coded error, success, and info alerts

## Mobile Responsive

All pages are fully responsive with breakpoints at:
- 768px: Tablet layout with collapsible menu
- 480px: Mobile layout with optimized spacing

## Security

- All authentication handled server-side
- Session management with 3-minute timeout
- Secure password handling (never stored)
- Error messages without exposing sensitive data
- HTTPS recommended for production

## Customization

To customize the design, edit the CSS in the `render_html()` function in `web_login.py`. All styles are embedded for easy deployment.

## Technologies

- **Backend**: FastAPI, Telethon
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Design**: Custom gradient design, responsive flexbox layout
- **Database**: SQLAlchemy (configured in your backend)

## Support

For issues or questions, contact the development team or check the security page for privacy concerns.
