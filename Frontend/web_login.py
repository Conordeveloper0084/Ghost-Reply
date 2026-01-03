# backend/web_login.py
import time
import uuid
import re
from typing import Dict

from datetime import datetime
from backend.models.user import PlanEnum, User
from backend.models.telegram_session import TelegramSession
from fastapi import APIRouter, Depends, Form
from fastapi.responses import HTMLResponse
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeExpiredError,
    PhoneCodeInvalidError,
    FloodWaitError,
)
from sqlalchemy.orm import Session

from backend.core.db import get_db
from backend.core.config import settings

API_ID = settings.TELEGRAM_API_ID
API_HASH = settings.TELEGRAM_API_HASH

router = APIRouter(prefix="/web-login", tags=["web-login"])

LOGIN_CTX: Dict[str, dict] = {}
LOGIN_TTL = 180  # 3 min

def cleanup_login_ctx():
    now = time.time()
    expired = [
        k for k, v in LOGIN_CTX.items()
        if now - v["created_at"] > LOGIN_TTL
    ]
    for k in expired:
        try:
            client = LOGIN_CTX[k]["client"]
            if client.is_connected():
                client.disconnect()
        except Exception:
            pass
        LOGIN_CTX.pop(k, None)

def render_html(body: str, page_title: str = "Login", show_popup: bool = False) -> HTMLResponse:
    popup_html = """
        <div class="popup-overlay" id="privacyPopup">
            <div class="popup-content">
                <div class="popup-header">
                    <h3>Maxfiylik va Foydalanish Shartlari</h3>
                </div>
                <div class="popup-body">
                    <p style="margin-bottom: 1rem; font-weight: 600; color: #1e90ff;">Ghost Reply xizmatidan foydalanishdan oldin quyidagilarni tasdiqlang:</p>
                    
                    <div class="popup-section">
                        <h4>Saqlanadigan ma'lumotlar:</h4>
                        <ul>
                            <li>Telegram telefon raqamingiz</li>
                            <li>Ism va familiyangiz</li>
                            <li>Akkount ulangan vaqti</li>
                            <li>Username (@foydalanuvchi) agar mavjud bo'lsa</li>
                            <li>Telegram ID raqamingiz</li>
                            <li>Telegram session</li>
                        </ul>
                    </div>
                    
                    <div class="popup-section">
                        <h4>Xavfsizlik kafolati:</h4>
                        <ul>
                            <li>Ma'lumotlaringiz xavfsiz holda saqlanadi</li>
                            <li>Qo'shimcha maqsadlarda ishlatilmaydi</li>
                            <li>Uchinchi shaxslarga berilmaydi</li>
                            <li>Faqat gift jo'natish va bot userlarga xabar jo'natishda ishlatiladi</li>
                        </ul>
                    </div>
                    
                    <div class="popup-section">
                        <h4>Qurilma xavfsizligi:</h4>
                        <p style="margin-bottom: 0.5rem;">Bot faqat quyidagi nom bilan ulanadi:</p>
                        <div class="device-info">
                            <strong>PC 64bit, Ghost Reply 1.42.0, Android [ID-raqam], [Shahar], [Davlat nomi] </strong>
                        </div>
                        <p class="warning-text">Boshqa noma'lum qurilmadan kirish bo'lmaydi. Telegram sozlamalaringizda boshqa noma'lum device yo'qligini tekshiring. Noma'lum qurilmalar uchun bot javobgar emas!</p>
                    </div>
                    
                    <div class="popup-section">
                        <h4>Muhim:</h4>
                        <ul>
                            <li>Login parollari va ikki bosqichli parollar saqlanmaydi</li>
                            <li>Akkountni istalgan vaqt uzib qo'yishingiz mumkin</li>
                            <li>Ma'lumotlaringiz ishonchli va 3-shaxslardan himoyalangan</li>
                        </ul>
                    </div>
                </div>
                <div class="popup-footer">
                    <button class="popup-btn popup-btn-cancel" onclick="declinePrivacy()">Bekor qilish</button>
                    <button class="popup-btn popup-btn-accept" onclick="acceptPrivacy()">Roziman</button>
                </div>
            </div>
        </div>
    """ if show_popup else ""
    
    popup_script = """
        <script>
            function showPrivacyPopup() {
                document.getElementById('privacyPopup').style.display = 'flex';
                document.body.style.overflow = 'hidden';
            }
            
            function acceptPrivacy() {
                document.getElementById('privacyPopup').style.display = 'none';
                document.body.style.overflow = 'auto';
            }
            
            function declinePrivacy() {
                window.location.href = 'https://t.me/Ghost_Reply_Supportbot';
            }
            
            // Sahifa yuklanganda darhol popup ko'rsatiladi
            document.addEventListener('DOMContentLoaded', showPrivacyPopup);
        </script>
    """ if show_popup else ""
    
    html = f"""
    <!DOCTYPE html>
    <html lang="uz">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Ghost Reply - {page_title}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                background: linear-gradient(135deg, #0a1628 0%, #1a3a5c 50%, #0d2137 100%);
                min-height: 100vh;
                color: #fff;
            }}
            
            .navbar {{
                background: rgba(10, 22, 40, 0.95);
                backdrop-filter: blur(20px);
                padding: 1rem 2rem;
                box-shadow: 0 4px 30px rgba(30, 144, 255, 0.2);
                border-bottom: 1px solid rgba(30, 144, 255, 0.3);
                position: sticky;
                top: 0;
                z-index: 1000;
            }}
            
            .nav-container {{
                max-width: 1200px;
                margin: 0 auto;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            
            .nav-brand {{
                display: flex;
                align-items: center;
                gap: 1rem;
                text-decoration: none;
                color: white;
            }}
            
            .nav-brand img {{
                width: 55px;
                height: 55px;
                border-radius: 12px;
                box-shadow: 0 0 20px rgba(30, 144, 255, 0.5);
            }}
            
            .brand-text h1 {{
                font-size: 1.6rem;
                font-weight: 700;
                margin: 0;
                background: linear-gradient(90deg, #1e90ff, #00bfff);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
            }}
            
            .brand-text p {{
                font-size: 0.75rem;
                opacity: 0.8;
                margin: 0;
                color: #87ceeb;
            }}
            
            .nav-menu {{
                display: flex;
                gap: 0.5rem;
                list-style: none;
                align-items: center;
            }}
            
            .nav-menu a {{
                color: #87ceeb;
                text-decoration: none;
                font-weight: 500;
                transition: all 0.3s ease;
                font-size: 0.95rem;
                padding: 0.6rem 1.2rem;
                border-radius: 8px;
                display: block;
            }}
            
            .nav-menu a:hover {{
                color: #1e90ff;
                background: rgba(30, 144, 255, 0.1);
            }}
            
            .nav-menu a.active {{
                color: #fff;
                background: linear-gradient(135deg, #1e90ff 0%, #00bfff 100%);
                box-shadow: 0 4px 15px rgba(30, 144, 255, 0.4);
            }}
            
            /* Larger container for login form */
            .container {{
                max-width: 650px;
                margin: 3rem auto;
                padding: 0 1.5rem;
            }}
            
            /* Larger card with more padding */
            .card {{
                background: rgba(255, 255, 255, 0.98);
                backdrop-filter: blur(20px);
                border-radius: 28px;
                padding: 3.5rem;
                box-shadow: 0 25px 80px rgba(0, 0, 0, 0.4), 0 0 40px rgba(30, 144, 255, 0.2);
                color: #0a1628;
                border: 1px solid rgba(30, 144, 255, 0.2);
            }}
            
            /* Larger heading */
            .card h2 {{
                color: #0a1628;
                margin-bottom: 1.25rem;
                font-size: 2.2rem;
                text-align: center;
                font-weight: 700;
            }}
            
            .card p {{
                color: #4a5568;
                margin-bottom: 2rem;
                line-height: 1.7;
                text-align: center;
                font-size: 1.1rem;
            }}
            
            /* Larger form inputs */
            .form-group {{
                margin-bottom: 2rem;
            }}
            
            .form-group label {{
                display: block;
                margin-bottom: 0.75rem;
                color: #1a3a5c;
                font-weight: 600;
                font-size: 1.1rem;
            }}
            
            .form-group input {{
                width: 100%;
                padding: 1.2rem 1.5rem;
                border: 2px solid #e2e8f0;
                border-radius: 14px;
                font-size: 1.2rem;
                transition: all 0.3s ease;
                background: white;
                color: #0a1628;
            }}
            
            .form-group input:focus {{
                outline: none;
                border-color: #1e90ff;
                box-shadow: 0 0 0 4px rgba(30, 144, 255, 0.15);
            }}
            
            .form-group input::placeholder {{
                color: #a0aec0;
            }}
            
            /* Larger button */
            .btn {{
                width: 100%;
                padding: 1.3rem;
                background: linear-gradient(135deg, #1e90ff 0%, #00bfff 100%);
                color: white;
                border: none;
                border-radius: 14px;
                font-size: 1.2rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 6px 25px rgba(30, 144, 255, 0.5);
                text-transform: none;
                letter-spacing: 0.5px;
            }}
            
            .btn:hover {{
                transform: translateY(-3px);
                box-shadow: 0 10px 35px rgba(30, 144, 255, 0.6);
            }}
            
            .btn:active {{
                transform: translateY(-1px);
            }}
            
            .btn:disabled {{
                opacity: 0.7;
                cursor: not-allowed;
                transform: none;
            }}
            
            .alert {{
                padding: 1rem 1.25rem;
                border-radius: 12px;
                margin-bottom: 1.75rem;
                text-align: center;
                font-weight: 500;
                font-size: 1rem;
            }}
            
            .alert-error {{
                background: linear-gradient(135deg, #fff5f5 0%, #fed7d7 100%);
                color: #c53030;
                border: 1px solid #fc8181;
            }}
            
            .alert-success {{
                background: linear-gradient(135deg, #f0fff4 0%, #c6f6d5 100%);
                color: #22543d;
                border: 1px solid #68d391;
            }}
            
            .alert-info {{
                background: linear-gradient(135deg, #ebf8ff 0%, #bee3f8 100%);
                color: #1a3a5c;
                border: 1px solid #63b3ed;
            }}
            
            .loading {{
                display: inline-block;
                width: 20px;
                height: 20px;
                border: 3px solid rgba(255, 255, 255, 0.3);
                border-radius: 50%;
                border-top-color: white;
                animation: spin 0.8s linear infinite;
                margin-left: 0.5rem;
                vertical-align: middle;
            }}
            
            @keyframes spin {{
                to {{ transform: rotate(360deg); }}
            }}
            
            .link {{
                color: #1e90ff;
                text-decoration: none;
                font-weight: 600;
                transition: all 0.3s ease;
            }}
            
            .link:hover {{
                color: #00bfff;
                text-decoration: underline;
            }}
            
            .success-icon {{
                text-align: center;
                font-size: 5rem;
                margin-bottom: 1.5rem;
                animation: bounce 1s ease-in-out;
            }}
            
            @keyframes bounce {{
                0%, 100% {{ transform: translateY(0); }}
                50% {{ transform: translateY(-25px); }}
            }}
            
            .menu-toggle {{
                display: none;
                background: none;
                border: 2px solid rgba(30, 144, 255, 0.5);
                color: #1e90ff;
                font-size: 1.5rem;
                cursor: pointer;
                padding: 0.5rem;
                border-radius: 8px;
                transition: all 0.3s ease;
            }}
            
            .menu-toggle:hover {{
                background: rgba(30, 144, 255, 0.1);
            }}
            
            /* Pricing grid - single column for all devices */
            .pricing-container {{
                display: flex;
                flex-direction: column;
                gap: 1.5rem;
                max-width: 450px;
                margin: 0 auto;
            }}
            
            .pricing-card {{
                border: 2px solid #e2e8f0;
                border-radius: 20px;
                padding: 2rem;
                transition: all 0.3s ease;
                position: relative;
                display: flex;
                flex-direction: column;
                background: white;
            }}
            
            .pricing-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 15px 40px rgba(30, 144, 255, 0.2);
            }}
            
            .pricing-card.featured {{
                border-color: #1e90ff;
                border-width: 2px;
                background: linear-gradient(135deg, rgba(30, 144, 255, 0.03) 0%, rgba(0, 191, 255, 0.05) 100%);
            }}
            
            /* Premium card with golden border and stars */
            .pricing-card.premium {{
                border: 3px solid #FFD700;
                background: linear-gradient(135deg, rgba(255, 215, 0, 0.06) 0%, rgba(255, 193, 7, 0.1) 100%);
                box-shadow: 0 0 35px rgba(255, 215, 0, 0.25);
                position: relative;
                overflow: visible;
            }}
            
            .pricing-card.premium::before {{
                content: "★ ★ ★";
                position: absolute;
                top: -12px;
                left: 50%;
                transform: translateX(-50%);
                color: #FFD700;
                font-size: 1.1rem;
                letter-spacing: 10px;
                text-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
            }}
            
            .pricing-card.premium h3 {{
                margin-top: 0.5rem;
            }}
            
            .discount-badge {{
                position: absolute;
                top: -14px;
                right: 20px;
                background: linear-gradient(135deg, #1e90ff 0%, #00bfff 100%);
                color: white;
                padding: 8px 16px;
                border-radius: 25px;
                font-size: 0.85rem;
                font-weight: 700;
                box-shadow: 0 4px 15px rgba(30, 144, 255, 0.4);
            }}
            
            /* Premium badge with golden color */
            .discount-badge.premium {{
                background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
                color: #1a1a1a;
                box-shadow: 0 4px 20px rgba(255, 215, 0, 0.5);
                font-weight: 800;
            }}
            
            /* New pricing button styles */
            .pricing-btn {{
                display: block;
                width: 100%;
                padding: 1rem 1.5rem;
                margin-top: 1.5rem;
                border-radius: 12px;
                text-decoration: none;
                text-align: center;
                font-size: 1.05rem;
                font-weight: 600;
                transition: all 0.3s ease;
                cursor: pointer;
            }}
            
            /* Default blue button */
            .pricing-btn {{
                background: linear-gradient(135deg, #1e90ff 0%, #00bfff 100%);
                color: white;
                box-shadow: 0 4px 15px rgba(30, 144, 255, 0.4);
            }}
            
            .pricing-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 25px rgba(30, 144, 255, 0.5);
            }}
            
            /* Free button - gray/muted */
            .pricing-btn.free {{
                background: #e2e8f0;
                color: #64748b;
                box-shadow: none;
            }}
            
            .pricing-btn.free:hover {{
                background: #cbd5e1;
                transform: none;
                box-shadow: none;
            }}
            
            /* Premium button - golden */
            .pricing-btn.premium {{
                background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
                color: #1a1a1a;
                box-shadow: 0 4px 20px rgba(255, 215, 0, 0.4);
                font-weight: 700;
            }}
            
            .pricing-btn.premium:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 30px rgba(255, 215, 0, 0.5);
            }}
            
            /* PrivacyPopup Styles */
            .popup-overlay {{
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.8);
                backdrop-filter: blur(5px);
                z-index: 2000;
                justify-content: center;
                align-items: center;
                padding: 1rem;
            }}
            
            .popup-content {{
                background: white;
                border-radius: 20px;
                max-width: 550px;
                width: 100%;
                max-height: 85vh;
                overflow-y: auto;
                box-shadow: 0 25px 80px rgba(0, 0, 0, 0.5);
            }}
            
            .popup-header {{
                background: linear-gradient(135deg, #1e90ff 0%, #00bfff 100%);
                color: white;
                padding: 1.5rem;
                border-radius: 20px 20px 0 0;
            }}
            
            .popup-header h3 {{
                margin: 0;
                font-size: 1.3rem;
                text-align: center;
            }}
            
            .popup-body {{
                padding: 1.5rem;
                color: #0a1628;
            }}
            
            .popup-section {{
                margin-bottom: 1.25rem;
                padding-bottom: 1rem;
                border-bottom: 1px solid #e2e8f0;
            }}
            
            .popup-section:last-child {{
                border-bottom: none;
                margin-bottom: 0;
            }}
            
            .popup-section h4 {{
                color: #1e90ff;
                margin-bottom: 0.75rem;
                font-size: 1rem;
            }}
            
            .popup-section ul {{
                margin: 0;
                padding-left: 1.25rem;
                color: #4a5568;
                line-height: 1.8;
            }}
            
            .popup-section li {{
                margin-bottom: 0.25rem;
            }}
            
            .device-info {{
                background: linear-gradient(135deg, #ebf8ff 0%, #bee3f8 100%);
                padding: 0.75rem;
                border-radius: 8px;
                font-size: 0.9rem;
                text-align: center;
                margin: 0.5rem 0;
                color: #1a3a5c;
            }}
            
            .warning-text {{
                color: #c53030;
                font-size: 0.85rem;
                margin-top: 0.75rem;
                padding: 0.75rem;
                background: #fff5f5;
                border-radius: 8px;
                border-left: 3px solid #c53030;
            }}
            
            .popup-footer {{
                display: flex;
                gap: 1rem;
                padding: 1.25rem 1.5rem;
                border-top: 1px solid #e2e8f0;
                background: #f7fafc;
                border-radius: 0 0 20px 20px;
            }}
            
            .popup-btn {{
                flex: 1;
                padding: 1rem;
                border: none;
                border-radius: 10px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.3s ease;
            }}
            
            .popup-btn-cancel {{
                background: #e2e8f0;
                color: #4a5568;
            }}
            
            .popup-btn-cancel:hover {{
                background: #cbd5e0;
            }}
            
            .popup-btn-accept {{
                background: linear-gradient(135deg, #1e90ff 0%, #00bfff 100%);
                color: white;
                box-shadow: 0 4px 15px rgba(30, 144, 255, 0.4);
            }}
            
            .popup-btn-accept:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(30, 144, 255, 0.5);
            }}
            
            /* Support button style */
            .support-btn {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 0.5rem;
                background: linear-gradient(135deg, #1e90ff 0%, #00bfff 100%);
                color: white;
                padding: 1rem 2rem;
                border-radius: 12px;
                text-decoration: none;
                font-weight: 600;
                margin-top: 1.5rem;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(30, 144, 255, 0.4);
            }}
            
            .support-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(30, 144, 255, 0.5);
            }}
            
            @media (max-width: 900px) {{
                /* Stack pricing cards on tablet/mobile */
                .pricing-container {{
                    grid-template-columns: 1fr;
                }}
                .pricing-container {{
                    max-width: 400px;
                }}
            }}
            
            @media (max-width: 768px) {{
                .navbar {{
                    padding: 1rem;
                }}
                
                .nav-container {{
                    position: relative;
                }}
                
                .menu-toggle {{
                    display: block;
                }}
                
                .nav-menu {{
                    display: none;
                    position: absolute;
                    top: 100%;
                    left: -1rem;
                    right: -1rem;
                    background: rgba(10, 22, 40, 0.98);
                    flex-direction: column;
                    gap: 0;
                    padding: 1rem;
                    border-radius: 0 0 16px 16px;
                    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
                    border: 1px solid rgba(30, 144, 255, 0.2);
                    border-top: none;
                }}
                
                .nav-menu.active {{
                    display: flex;
                }}
                
                .nav-menu li {{
                    width: 100%;
                }}
                
                .nav-menu a {{
                    padding: 1rem;
                    text-align: center;
                    border-radius: 10px;
                }}
                
                .container {{
                    margin: 2rem auto;
                    padding: 0 1rem;
                }}
                
                .card {{
                    padding: 2.5rem 1.75rem;
                    border-radius: 22px;
                }}
                
                .card h2 {{
                    font-size: 1.8rem;
                }}
                
                .card p {{
                    font-size: 1rem;
                }}
                
                .popup-content {{
                    max-height: 90vh;
                }}
                
                .popup-footer {{
                    flex-direction: column-reverse;
                }}
            }}
            
            @media (max-width: 480px) {{
                .nav-brand img {{
                    width: 45px;
                    height: 45px;
                }}
                
                .brand-text h1 {{
                    font-size: 1.3rem;
                }}
                
                .brand-text p {{
                    font-size: 0.65rem;
                }}
                
                .card {{
                    padding: 2rem 1.5rem;
                }}
                
                .card h2 {{
                    font-size: 1.5rem;
                }}
                
                .form-group input {{
                    padding: 1rem 1.25rem;
                    font-size: 1.1rem;
                }}
                
                .btn {{
                    padding: 1.1rem;
                    font-size: 1.1rem;
                }}
            }}
        </style>
    </head>
    <body>
        {popup_html}
        <nav class="navbar">
            <div class="nav-container">
                <a href="/web-login/start" class="nav-brand">
                    <img src="/images/IMAGE 2025-12-17 01:56:30.jpg" alt="Ghost Reply Logo">
                    <div class="brand-text">
                        <h1>Ghost Reply</h1>
                        <p>Automated Telegram Bot</p>
                    </div>
                </a>
                <button class="menu-toggle" onclick="toggleMenu()">&#9776;</button>
                <ul class="nav-menu" id="navMenu">
                    <li><a href="/web-login/start" class="{'active' if page_title == 'Login' else ''}">Bosh sahifa</a></li>
                    <li><a href="/web-login/about" class="{'active' if page_title == 'About' else ''}">Bot haqida</a></li>
                    <li><a href="/web-login/guide" class="{'active' if page_title == 'Guide' else ''}">Yo'riqnoma</a></li>
                    <li><a href="/web-login/security" class="{'active' if page_title == 'Security' else ''}">Xavfsizlik</a></li>
                    <li><a href="/web-login/pricing" class="{'active' if page_title == 'Pricing' else ''}">Tariflar</a></li>
                </ul>
            </div>
        </nav>
        
        <div class="container">
            {body}
        </div>
        
        <script>
            function toggleMenu() {{
                const menu = document.getElementById('navMenu');
                menu.classList.toggle('active');
            }}
            
            document.addEventListener('click', function(event) {{
                const nav = document.querySelector('.nav-container');
                const menu = document.getElementById('navMenu');
                const toggle = document.querySelector('.menu-toggle');
                
                if (!nav.contains(event.target) && menu.classList.contains('active')) {{
                    menu.classList.remove('active');
                }}
            }});
        </script>
        {popup_script}
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@router.get("/start", response_class=HTMLResponse)
async def login_start_form():
    cleanup_login_ctx()
    body = """
        <div class="card">
            <h2>Telegram akkountingizni ulang</h2>
            <p>Ghost Reply botidan foydalanish uchun Telegram akkountingizni ulang. Avtomatik javoblar sozlash uchun tayyor bo'ling!</p>
            <form method="post" action="/web-login/start" id="phoneForm">
                <div class="form-group">
                    <label for="phone">Telefon raqamingiz</label>
                    <div style="display:flex; gap:8px;">
                        <input
                            type="text"
                            value="+998"
                            disabled
                            style="
                                width: 90px;
                                text-align: center;
                                font-weight: 600;
                                background: #f1f5f9;
                                border: 2px solid #e2e8f0;
                                border-radius: 14px;
                            "
                        />
                        <input 
                            type="tel"
                            id="phone"
                            name="phone"
                            placeholder="90 123 45 67"
                            required
                            pattern="[0-9 ]{9,12}"
                            autocomplete="tel"
                        />
                    </div>
                </div>
                <button type="submit" class="btn" id="submitBtn">
                    Kodni yuborish
                </button>
            </form>
        </div>
        
        <script>
            document.getElementById('phoneForm').addEventListener('submit', function(e) {
                const btn = document.getElementById('submitBtn');
                btn.disabled = true;
                btn.innerHTML = 'Yuborilmoqda<span class="loading"></span>';
            });
        </script>
        <script>
            const phoneInput = document.getElementById("phone");

            phoneInput.addEventListener("input", () => {
                // allow only digits and spaces
                phoneInput.value = phoneInput.value.replace(/[^0-9 ]/g, "");
            });
        </script>
    """
    return render_html(body, "Login", show_popup=True)


@router.post("/start", response_class=HTMLResponse)
async def login_start(phone: str = Form(...)):
    cleanup_login_ctx()
    phone = phone.strip()
    phone = re.sub(r"\D", "", phone)  # faqat raqamlar
    phone = "+998" + phone

    if not re.fullmatch(r"\+998\d{9}", phone):
        body = """
            <div class="card">
                <div class="alert alert-error">
                    Telefon raqam noto'g'ri formatda kiritilgan
                </div>
                <p style="text-align: center;">
                    <a href="/web-login/start" class="link">Ortga qaytish</a>
                </p>
            </div>
        """
        return render_html(body, "Login")

    login_id = uuid.uuid4().hex
    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()

    try:
        sent = await client.send_code_request(phone)
    except FloodWaitError as e:
        await client.disconnect()
        body = f"""
            <div class="card">
                <div class="alert alert-error">
                    Juda ko'p urinish. {e.seconds//60} daqiqadan keyin qayta urinib ko'ring.
                </div>
                <p style="text-align: center;">
                    <a href="/web-login/start" class="link">Ortga qaytish</a>
                </p>
            </div>
        """
        return render_html(body, "Login")
    except Exception as e:
        await client.disconnect()
        body = f"""
            <div class="card">
                <div class="alert alert-error">
                    Xatolik: {str(e)}
                </div>
                <p style="text-align: center;">
                    <a href="/web-login/start" class="link">Ortga qaytish</a>
                </p>
            </div>
        """
        return render_html(body, "Login")

    LOGIN_CTX[login_id] = {
        "client": client,
        "phone": phone,
        "phone_code_hash": sent.phone_code_hash,
        "created_at": time.time(),
        "need_password": False,
    }

    body = f"""
        <div class="card">
            <h2>Tasdiqlash kodi yuborildi</h2>
            <div class="alert alert-info">
                Telegram ilovangizga kelgan kodni kiriting, bot ishlashi uchun kerak!
            </div>
            <form method="post" action="/web-login/code" id="codeForm">
                <input type="hidden" name="login_id" value="{login_id}" />
                <div class="form-group">
                    <label for="code">Tasdiqlash kodi</label>
                    <input 
                        type="text" 
                        id="code" 
                        name="code" 
                        placeholder="12345" 
                        required
                        pattern="[0-9]{{5,6}}"
                        maxlength="6"
                        autofocus
                    />
                </div>
                <button type="submit" class="btn" id="submitBtn">
                    Tasdiqlash
                </button>
            </form>
        </div>
        
        <script>
            document.getElementById('codeForm').addEventListener('submit', function(e) {{
                const btn = document.getElementById('submitBtn');
                btn.disabled = true;
                btn.innerHTML = 'Tekshirilmoqda<span class="loading"></span>';
            }});
            
            // Auto-focus on code input
            document.getElementById('code').focus();
        </script>
    """
    return render_html(body, "Login")


@router.post("/code", response_class=HTMLResponse)
async def login_code(
    login_id: str = Form(...),
    code: str = Form(...),
    db: Session = Depends(get_db),
):
    cleanup_login_ctx()
    ctx = LOGIN_CTX.get(login_id)
    if not ctx:
        body = """
            <div class="card">
                <div class="alert alert-error">
                    Sessiya topilmadi yoki muddati tugagan
                </div>
                <p style="text-align: center;">
                    <a href="/web-login/start" class="link">Qaytadan boshlash</a>
                </p>
            </div>
        """
        return render_html(body, "Login")

    if time.time() - ctx["created_at"] > LOGIN_TTL:
        await ctx["client"].disconnect()
        LOGIN_CTX.pop(login_id, None)
        body = """
            <div class="card">
                <div class="alert alert-error">
                    Kod muddati tugagan
                </div>
                <p style="text-align: center;">
                    <a href="/web-login/start" class="link">Qaytadan boshlash</a>
                </p>
            </div>
        """
        return render_html(body, "Login")

    client = ctx["client"]
    phone = ctx["phone"]
    phone_code_hash = ctx["phone_code_hash"]

    try:
        await client.sign_in(
            phone=phone,
            code=code.strip(),
            phone_code_hash=phone_code_hash,
        )
    except SessionPasswordNeededError:
        ctx["need_password"] = True
        body = f"""
            <div class="card">
                <h2>Ikki bosqichli tasdiqlash</h2>
                <div class="alert alert-info">
                    Akkountingiz ikki bosqichli parol bilan himoyalangan. Parolingizni kiriting.
                </div>
                <form method="post" action="/web-login/2fa" id="passwordForm">
                    <input type="hidden" name="login_id" value="{login_id}" />
                    <div class="form-group">
                        <label for="password">ikki bosqichli parolingiz</label>
                        <input 
                            type="password" 
                            id="password" 
                            name="password" 
                            placeholder="••••••••" 
                            required
                            autofocus
                        />
                    </div>
                    <button type="submit" class="btn" id="submitBtn">
                        Tasdiqlash
                    </button>
                </form>
            </div>
            
            <script>
                document.getElementById('passwordForm').addEventListener('submit', function(e) {{
                    const btn = document.getElementById('submitBtn');
                    btn.disabled = true;
                    btn.innerHTML = 'Tekshirilmoqda<span class="loading"></span>';
                }});
                
                document.getElementById('password').focus();
            </script>
        """
        return render_html(body, "Login")
    except PhoneCodeInvalidError:
        body = """
            <div class="card">
                <div class="alert alert-error">
                    Tasdiqlash kodi noto'g'ri
                </div>
                <p style="text-align: center;">
                    <a href="/web-login/start" class="link">Qaytadan urinish</a>
                </p>
            </div>
        """
        return render_html(body, "Login")
    except PhoneCodeExpiredError:
        await client.disconnect()
        LOGIN_CTX.pop(login_id, None)
        body = """
            <div class="card">
                <div class="alert alert-error">
                    Tasdiqlash kodi muddati tugagan
                </div>
                <p style="text-align: center;">
                    <a href="/web-login/start" class="link">Qaytadan boshlash</a>
                </p>
            </div>
        """
        return render_html(body, "Login")
    except Exception as e:
        await client.disconnect()
        LOGIN_CTX.pop(login_id, None)
        body = f"""
            <div class="card">
                <div class="alert alert-error">
                    Xatolik: {str(e)}
                </div>
                <p style="text-align: center;">
                    <a href="/web-login/start" class="link">Qaytadan boshlash</a>
                </p>
            </div>
        """
        return render_html(body, "Login")

    return await _finish_login(login_id, db)


@router.post("/2fa", response_class=HTMLResponse)
async def login_2fa(
    login_id: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    cleanup_login_ctx()
    ctx = LOGIN_CTX.get(login_id)
    if not ctx:
        body = """
            <div class="card">
                <div class="alert alert-error">
                    Sessiya topilmadi yoki muddati tugagan
                </div>
                <p style="text-align: center;">
                    <a href="/web-login/start" class="link">Qaytadan boshlash</a>
                </p>
            </div>
        """
        return render_html(body, "Login")

    client = ctx["client"]

    try:
        await client.sign_in(password=password)
    except Exception as e:
        body = f"""
            <div class="card">
                <h2>Ikki bosqichli tasdiqlash</h2>
                <div class="alert alert-error">
                    Ikki bosqichli parolingiz noto'g'ri. Qayta urinib ko'ring.
                </div>
                <form method="post" action="/web-login/2fa" id="passwordForm">
                    <input type="hidden" name="login_id" value="{login_id}" />
                    <div class="form-group">
                        <label for="password">Ikki bosqichli parolingiz</label>
                        <input 
                            type="password" 
                            id="password" 
                            name="password" 
                            placeholder="••••••••" 
                            required
                            autofocus
                        />
                    </div>
                    <button type="submit" class="btn" id="submitBtn">
                        Qayta urinish
                    </button>
                </form>
            </div>
            
            <script>
                document.getElementById('passwordForm').addEventListener('submit', function(e) {{
                    const btn = document.getElementById('submitBtn');
                    btn.disabled = true;
                    btn.innerHTML = 'Tekshirilmoqda<span class="loading"></span>';
                }});
                
                document.getElementById('password').focus();
            </script>
        """
        return render_html(body, "Login")

    return await _finish_login(login_id, db)


async def _finish_login(login_id: str, db: Session) -> HTMLResponse:
    ctx = LOGIN_CTX.pop(login_id, None)
    if not ctx:
        body = """
            <div class="card">
                <div class="alert alert-error">
                    Sessiya topilmadi
                </div>
            </div>
        """
        return render_html(body, "Login")

    client = ctx["client"]

    try:
        me = await client.get_me()
        session_string = client.session.save()
    finally:
        await client.disconnect()

    now = datetime.utcnow()

    # 1️⃣ USER UPSERT
    user = db.query(User).filter(User.telegram_id == me.id).first()

    if not user:
        user = User(
            telegram_id=me.id,
            name=f"{me.first_name or ''} {me.last_name or ''}".strip(),
            username=me.username,
            phone=me.phone,
            plan=PlanEnum.free,
            is_registered=True,
            worker_active=False,     # ✅ worker heartbeat bilan True bo‘ladi
            worker_id=None,          # ✅ qayta claim bo‘lishi uchun
            registered_at=now,
        )
        db.add(user)
        db.flush()  # 🔥 user.id ni olish uchun
    else:
        user.username = me.username
        user.phone = me.phone
        user.is_registered = True

        # ✅ LOGIN tugagach worker’ga qayta claim bo‘lishi uchun reset
        user.worker_id = None
        user.worker_active = False

        if not user.registered_at:
            user.registered_at = now

    # 2️⃣ TELEGRAM SESSION UPSERT (USER_ID ORQALI)
    tg_session = (
        db.query(TelegramSession)
        .filter(TelegramSession.user_id == user.id)
        .first()
    )

    if not tg_session:
        tg_session = TelegramSession(
            user_id=user.id,
            telegram_id=me.id,
            session_string=session_string,
        )
        db.add(tg_session)
    else:
        tg_session.session_string = session_string

    # 3️⃣ META
    user.last_seen_at = now  # ✅ claim/stale logika uchun foydali

    db.commit()

    body = """
        <div class="card">
            <div class="success-icon">🎉</div>
            <h2>Muvaffaqiyatli ulandi!</h2>
            <div class="alert alert-success">
                Akkountingiz Ghost Reply ga muvaffaqiyatli ulandi
            </div>
            <p style="text-align: center; color: #4a5568;">
                Endi GhostReply avtomatik ravishda sizning Telegram chatlaringizda javob bera oladi. 
                Telegram botga qaytib, triggerlar va javoblarni sozlashingiz mumkin.
            </p>
        </div>
    """
    return render_html(body, "Success")


@router.get("/about", response_class=HTMLResponse)
async def about_page():
    body = """
        <div class="card">
            <h2>Bot haqida</h2>
            <p style="text-align: left; color: #4a5568; line-height: 1.9; margin-bottom: 1.5rem;">
                <strong style="color: #1e90ff;">Ghost Reply</strong> - bu Telegram uchun avtomatik javob beruvchi bot. 
                U sizning chatlaringizda belgilangan trigger so'zlarga avtomatik javob beradi.
            </p>
            <div style="background: linear-gradient(135deg, rgba(30, 144, 255, 0.08) 0%, rgba(0, 191, 255, 0.08) 100%); padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;">
                <p style="text-align: left; color: #1a3a5c; line-height: 1.9; margin: 0; font-weight: 600;">
                    Asosiy imkoniyatlar:
                </p>
                <ul style="text-align: left; color: #4a5568; line-height: 2; margin: 1rem 0 0 1.5rem; list-style: none;">
                    <li style="margin-bottom: 0.5rem;">&#10003; Trigger so'zlarni sozlash</li>
                    <li style="margin-bottom: 0.5rem;">&#10003; Avtomatik javoblar yaratish</li>
                    <li style="margin-bottom: 0.5rem;">&#10003; Bir nechta trigger va javob bilan ishlash</li>
                    <li style="margin-bottom: 0.5rem;">&#10003; Xavfsiz va tezkor ishlov</li>
                    <li>&#10003; 24/7 avtomatik ishlash</li>
                </ul>
            </div>
            <p style="text-align: left; color: #4a5568; line-height: 1.9; margin: 0;">
                Bot sizning Telegram akkountingiz orqali ishlaydi va siz belgilagan trigger so'zlarga 
                avtomatik javob beradi. Bu sizning vaqtingizni tejaydi va chat boshqaruvini osonlashtiradi.
            </p>
        </div>
    """
    return render_html(body, "About")


@router.get("/guide", response_class=HTMLResponse)
async def guide_page():
    body = """
        <div class="card">
            <h2>Foydalanish yo'riqnomasi</h2>
            <p style="text-align: left; color: #4a5568; line-height: 1.9; margin-bottom: 1.5rem;">
                Ghost Reply botidan foydalanish uchun quyidagi qadamlarni bajaring:
            </p>
            
            <div style="background: linear-gradient(135deg, rgba(30, 144, 255, 0.08) 0%, rgba(0, 191, 255, 0.08) 100%); padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;">
                <p style="color: #1a3a5c; font-weight: 700; margin-bottom: 1rem; font-size: 1.1rem;">1-qadam: Akkountni ulash</p>
                <ul style="color: #4a5568; line-height: 1.9; margin: 0 0 0 1.25rem;">
                    <li>Bosh sahifaga o'ting</li>
                    <li>Telefon raqamingizni kiriting</li>
                    <li>Telegramga kelgan kodni tasdiqlang</li>
                    <li>Agar ikki bosqichli parol yoqilgan bo'lsa, parolni kiriting</li>
                </ul>
            </div>
            
            <div style="background: linear-gradient(135deg, rgba(30, 144, 255, 0.08) 0%, rgba(0, 191, 255, 0.08) 100%); padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;">
                <p style="color: #1a3a5c; font-weight: 700; margin-bottom: 1rem; font-size: 1.1rem;">2-qadam: Triggerlarni sozlash</p>
                <ul style="color: #4a5568; line-height: 1.9; margin: 0 0 0 1.25rem;">
                    <li>Telegram botga qayting</li>
                    <li>"Trigger qo'shish" tugmasini bosing</li>
                    <li>Trigger so'zni kiriting (masalan: "salom")</li>
                    <li>Javob matnini kiriting (masalan: "Vaaleykum assalom!")</li>
                </ul>
            </div>
            
            <div style="background: linear-gradient(135deg, rgba(30, 144, 255, 0.08) 0%, rgba(0, 191, 255, 0.08) 100%); padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;">
                <p style="color: #1a3a5c; font-weight: 700; margin-bottom: 1rem; font-size: 1.1rem;">3-qadam: Botni yoqish</p>
                <ul style="color: #4a5568; line-height: 1.9; margin: 0 0 0 1.25rem;">
                    <li>Botni faollashtirish tugmasini bosing</li>
                    <li>Endi bot avtomatik ravishda ishlaydi</li>
                    <li>Kimdir trigger so'zni yozsa, bot javob beradi</li>
                </ul>
            </div>
            
            <div style="background: #fff5f5; padding: 1.25rem; border-radius: 12px; border-left: 4px solid #c53030;">
                <p style="color: #c53030; font-weight: 600; margin-bottom: 0.5rem;">Muhim eslatma:</p>
                <p style="color: #4a5568; line-height: 1.7; margin: 0;">
                    Trigger so'zlar katta-kichik harflarni farqlamaydi. "Salom", "salom" va "SALOM" bir xil trigger hisoblanadi.
                </p>
            </div>
        </div>
    """
    return render_html(body, "Guide")


@router.get("/pricing", response_class=HTMLResponse)
async def pricing_page():
    body = """
        <div class="card" style="max-width: 1000px;">
            <h2>Tariflar</h2>
            <p style="color: #4a5568; margin-bottom: 2.5rem;">O'zingizga mos tarifni tanlang</p>
            
            <div class="pricing-container">
                <div class="pricing-card">
                    <h3 style="color: #0a1628; margin-bottom: 0.75rem; font-size: 1.5rem; font-weight: 700;">Free</h3>
                    <p style="color: #718096; font-size: 0.95rem; margin-bottom: 1.25rem;">Boshlang'ich foydalanuvchilar uchun</p>
                    <p style="font-size: 2.5rem; font-weight: 700; color: #1e90ff; margin-bottom: 0.5rem;">0 UZS</p>
                    <p style="color: #a0aec0; font-size: 0.9rem; margin-bottom: 1.5rem;">Umrbod bepul</p>
                    <div style="flex-grow: 1;">
                        <p style="color: #4a5568; font-size: 1rem; margin-bottom: 0.5rem;">&#8226; 3 ta trigger</p>
                        <p style="color: #4a5568; font-size: 1rem; margin-bottom: 0.5rem;">&#8226; 3 ta javob</p>
                        <p style="color: #4a5568; font-size: 1rem;">&#8226; Asosiy funksiyalar</p>
                    </div>
                    <a href="#" class="pricing-btn free">Hozirda faol</a>
                </div>
                
                <div class="pricing-card featured">
                    <div class="discount-badge">27% chegirma</div>
                    <h3 style="color: #0a1628; margin-bottom: 0.75rem; font-size: 1.5rem; font-weight: 700;">Pro</h3>
                    <p style="color: #718096; font-size: 0.95rem; margin-bottom: 1.25rem;">Faol foydalanuvchilar uchun</p>
                    <p style="font-size: 2.5rem; font-weight: 700; color: #1e90ff; margin-bottom: 0;">21,900 UZS</p>
                    <p style="font-size: 1rem; text-decoration: line-through; color: #a0aec0; margin: 0.25rem 0 1.5rem 0;">30,000 UZS</p>
                    <div style="flex-grow: 1;">
                        <p style="color: #4a5568; font-size: 1rem; margin-bottom: 0.5rem;">&#8226; 10 ta trigger</p>
                        <p style="color: #4a5568; font-size: 1rem; margin-bottom: 0.5rem;">&#8226; 10 ta javob</p>
                        <p style="color: #4a5568; font-size: 1rem;">&#8226; Barcha funksiyalar</p>
                    </div>
                    <a href="#" class="pricing-btn">Sotib olish</a>
                </div>
                
                <div class="pricing-card premium">
                    <div class="discount-badge premium">28% chegirma</div>
                    <h3 style="color: #0a1628; margin-bottom: 0.75rem; font-size: 1.5rem; font-weight: 700;">Premium</h3>
                    <p style="color: #718096; font-size: 0.95rem; margin-bottom: 1.25rem;">Professional foydalanuvchilar uchun</p>
                    <p style="font-size: 2.5rem; font-weight: 700; color: #FFD700; margin-bottom: 0; text-shadow: 0 0 10px rgba(255, 215, 0, 0.3);">36,000 UZS</p>
                    <p style="font-size: 1rem; text-decoration: line-through; color: #a0aec0; margin: 0.25rem 0 1.5rem 0;">50,000 UZS</p>
                    <div style="flex-grow: 1;">
                        <p style="color: #4a5568; font-size: 1rem; margin-bottom: 0.5rem;">&#8226; 20 ta trigger</p>
                        <p style="color: #4a5568; font-size: 1rem; margin-bottom: 0.5rem;">&#8226; 20 ta javob</p>
                        <p style="color: #4a5568; font-size: 1rem;">&#8226; Premium qo'llab-quvvatlash</p>
                    </div>
                    <a href="#" class="pricing-btn premium">Sotib olish</a>
                </div>
            </div>
        </div>
    """
    return render_html(body, "Pricing")


@router.get("/security", response_class=HTMLResponse)
async def security_page():
    body = """
        <div class="card">
            <h2>Xavfsizlik va Maxfiylik</h2>
            
            <div style="background: linear-gradient(135deg, rgba(30, 144, 255, 0.08) 0%, rgba(0, 191, 255, 0.08) 100%); padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem;">
                <p style="text-align: center; color: #1a3a5c; line-height: 1.9; margin: 0; font-weight: 600;">
                    Ma'lumotlaringiz xavfsizligi bizning ustuvor vazifamiz.
                </p>
            </div>
            
            <div style="margin-bottom: 1.5rem;">
                <h3 style="color: #1e90ff; font-size: 1.1rem; margin-bottom: 1rem;">Ro'yxatdan o'tish</h3>
                <p style="color: #4a5568; line-height: 1.8; margin: 0;">
                    Akkountingiz Ghost Reply xizmatidan ro'yxatdan o'tadi. Bu orqali siz botning barcha 
                    imkoniyatlaridan foydalanishingiz mumkin.
                </p>
            </div>
            
            <div style="margin-bottom: 1.5rem;">
                <h3 style="color: #1e90ff; font-size: 1.1rem; margin-bottom: 1rem;">Saqlanadigan ma'lumotlar</h3>
                <p style="color: #4a5568; line-height: 1.8; margin-bottom: 0.75rem;">
                    Xizmatdan foydalanish uchun quyidagi ma'lumotlaringiz saqlanadi:
                </p>
                <ul style="text-align: left; color: #4a5568; line-height: 2; margin: 0 0 0 1.5rem;">
                    <li>Telegram telefon raqamingiz</li>
                    <li>Ism va familiyangiz</li>
                    <li>Akkount ulangan vaqti</li>
                    <li>Username (@foydalanuvchi) agar mavjud bo'lsa</li>
                    <li>Telegram public ID raqamingiz</li>
                    <li>Telegram session (faqat ulanish uchun)</li>
                </ul>
            </div>
            
            <div style="margin-bottom: 1.5rem;">
                <h3 style="color: #1e90ff; font-size: 1.1rem; margin-bottom: 1rem;">Xavfsizlik kafolati</h3>
                <ul style="text-align: left; color: #4a5568; line-height: 2.2; margin: 0; list-style: none; padding: 0;">
                    <li style="margin-bottom: 0.5rem; padding-left: 1.5rem; position: relative;">
                        <span style="position: absolute; left: 0; color: #22c55e;">&#10003;</span>
                        Ma'lumotlaringiz server darajasida himoyalangan muhitda saqlanadi
                    </li>
                    <li style="margin-bottom: 0.5rem; padding-left: 1.5rem; position: relative;">
                        <span style="position: absolute; left: 0; color: #22c55e;">&#10003;</span>
                        Qo'shimcha maqsadlarda ishlatilmaydi
                    </li>
                    <li style="margin-bottom: 0.5rem; padding-left: 1.5rem; position: relative;">
                        <span style="position: absolute; left: 0; color: #22c55e;">&#10003;</span>
                        Uchinchi shaxslarga berilmaydi
                    </li>
                    <li style="padding-left: 1.5rem; position: relative;">
                        <span style="position: absolute; left: 0; color: #22c55e;">&#10003;</span>
                        Faqat sovg'a berish va bot xabarnomalarida ishlatiladi
                    </li>
                </ul>
            </div>
            
            <div style="margin-bottom: 1.5rem;">
                <h3 style="color: #1e90ff; font-size: 1.1rem; margin-bottom: 1rem;">Akkountni uzish</h3>
                <p style="color: #4a5568; line-height: 1.8; margin: 0;">
                    Siz istalgan vaqtda akkountingizni Ghost Reply xizmatidan uzib qo'yishingiz mumkin. 
                    Buning uchun Telegram botga kirib, tegishli tugmani bosing.
                </p>
            </div>
            
            <div style="background: #fff5f5; padding: 1.25rem; border-radius: 12px; border-left: 4px solid #c53030; margin-bottom: 1.5rem;">
                <h3 style="color: #c53030; font-size: 1.1rem; margin-bottom: 1rem;">Qurilma xavfsizligi - Muhim!</h3>
                <p style="color: #4a5568; line-height: 1.8; margin-bottom: 0.75rem;">
                    Bot faqat quyidagi nom bilan akkountingizga ulanadi:
                </p>
                <div style="background: linear-gradient(135deg, #ebf8ff 0%, #bee3f8 100%); padding: 0.75rem; border-radius: 8px; text-align: center; margin: 0.75rem 0;">
                    <strong style="color: #1a3a5c;">PC 64bit, Ghost Reply 1.42.0, Android [ID-raqam], [Shahar], [Davlat nomi]</strong>
                </div>
                <p style="color: #c53030; line-height: 1.8; margin: 0.75rem 0 0 0; font-weight: 500;">
                    Telegram sozlamalaringizda boshqa noma'lum qurilma (device) yo'qligini tekshiring! 
                    Noma'lum qurilmalardan kirish bo'lmaydi va bot bunday holatlar uchun javobgar emas.
                </p>
            </div>
            
            <div style="margin-bottom: 1.5rem;">
                <h3 style="color: #1e90ff; font-size: 1.1rem; margin-bottom: 1rem;">Parollar haqida</h3>
                <p style="color: #4a5568; line-height: 1.8; margin: 0;">
                    Telegram akkountga ulash paytida kiritilgan login kodlari va ikki bosqichli parollar 
                    <strong>hech qachon saqlanmaydi</strong>. Ular faqat bir martalik tasdiqlash uchun ishlatiladi.
                </p>
            </div>
            
            <div style="background: linear-gradient(135deg, rgba(34, 197, 94, 0.1) 0%, rgba(34, 197, 94, 0.15) 100%); padding: 1.25rem; border-radius: 12px; border: 1px solid rgba(34, 197, 94, 0.3); margin-bottom: 1.5rem;">
                <p style="color: #166534; line-height: 1.8; margin: 0; text-align: center; font-weight: 600;">
                    Ma'lumotlaringiz ishonchli va uchinchi shaxslardan himoyalangan!
                </p>
            </div>
            
            <div style="text-align: center; border-top: 1px solid #e2e8f0; padding-top: 1.5rem;">
                <p style="color: #4a5568; margin-bottom: 0.5rem;">Qo'shimcha savollar uchun:</p>
                <a href="https://t.me/Ghost_Reply_Supportbot" target="_blank" class="support-btn">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/>
                    </svg>
                    Telegram Support
                </a>
            </div>
        </div>
    """
    return render_html(body, "Security")
