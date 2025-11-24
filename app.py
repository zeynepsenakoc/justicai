# app.py — ULTIMATE ENGINEERING BUILD (Auth + DB + OCR + AI + PDF + Admin)
import os
import json
import logging
from datetime import datetime
import io
import time

from flask import Flask, render_template, request, session, redirect, url_for, flash, send_file
import requests
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from sqlalchemy import func # İstatistikler için gerekli

# MODÜLLER
from config import BASE_PROMPT, CATEGORIES, PETITION_HTML_TEMPLATE
from ocr_service import extract_text_from_file
from models import db, User, Petition
from logic_services import search_legal_docs, check_rules

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "bitirme2025_gizli_anahtar")

# DB & LOGIN SETUP
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth"
login_manager.login_message_category = "warning"

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

logging.basicConfig(level=logging.INFO, handlers=[logging.FileHandler("app.log"), logging.StreamHandler()])
logger = logging.getLogger(__name__)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- AKILLI SİMÜLASYON (INTERACTIVE FLOW) ---
def get_mock_response(user_text="", ocr_text="", rules_feedback="", rag_context=""):
    time.sleep(0.8)
    total_len = len(str(user_text)) + len(str(ocr_text))
    
    if total_len < 30:
        return {
            "status": "SORGU",
            "questions": [
                "Ürünü satın aldığınız tam tarih nedir?",
                "Satıcı firma ile daha önce iletişime geçtiniz mi?",
                "Elinizde fatura, fiş veya sözleşme var mı?",
                "Tam olarak talebiniz nedir (Para iadesi, değişim, onarım)?"
            ]
        }

    return {
        "status": "DILEKCE_HAZIR",
        "hitap_makam": "İSTANBUL NÖBETÇİ TÜKETİCİ MAHKEMESİNE",
        "dilekce_metni": f"""KONU: Ayıplı Mal Nedeniyle Bedel İadesi Talebi.

AÇIKLAMALAR:

1. Müvekkil, (Sistem OCR ile tarihi buraya işler) tarihinde davalı firmadan hizmet/ürün satın almıştır.
2. Ürün garanti süresi içerisinde arızalanmış olup, {rag_context[:50] if rag_context else "6502 Sayılı Kanun"} kapsamında ayıplı mal niteliğindedir.
3. Sistemin yaptığı kural analizi sonucunda: {rules_feedback if rules_feedback else "Herhangi bir usul engeli tespit edilmemiştir."}

HUKUKİ SEBEPLER:
{rag_context[:300]}...

SONUÇ VE İSTEM:
Yukarıda arz ve izah edilen nedenlerle, ürün bedelinin yasal faiziyle birlikte iadesine karar verilmesini saygılarımla arz ve talep ederim.

(NOT: Bu metin 'Simülasyon Modu' ile oluşturulmuştur. API Kredisi yüklendiğinde yapay zeka devreye girecektir.)""",
        "hukuki_oneriler": f"• Sistem Uyarısı: {rules_feedback}\n• Bulunan Emsal Kanun: {rag_context[:50]}..."
    }

def call_llm(prompt_context, user_text="", ocr_text="", rules="", rag="") -> dict:
    if not OPENAI_API_KEY or "benim keyim" in OPENAI_API_KEY:
        return get_mock_response(user_text, ocr_text, rules, rag)

    full_prompt = BASE_PROMPT.format(context_data=prompt_context)
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": full_prompt}],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }
    try:
        r = requests.post("https://api.openai.com/v1/chat/completions", headers={"Authorization": f"Bearer {OPENAI_API_KEY}"}, json=payload, timeout=60)
        if r.status_code != 200: 
            logger.error(f"API Hatası: {r.status_code}")
            return get_mock_response(user_text, ocr_text, rules, rag)
        return json.loads(r.json()["choices"][0]["message"]["content"])
    except Exception as e:
        logger.error(f"LLM Hatası: {e}")
        return get_mock_response(user_text, ocr_text, rules, rag)

def html_to_pdf_playwright(html_content: str) -> bytes:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html_content)
        return page.pdf(format="A4", margin={"top":"2.5cm","right":"2.5cm","bottom":"2.5cm","left":"2.5cm"})

# --- ROTALAR ---

@app.route("/auth", methods=["GET"])
def auth():
    if current_user.is_authenticated: return redirect(url_for("index"))
    return render_template("auth.html", active_tab="login")

@app.route("/register", methods=["POST"])
def register():
    username = request.form.get("username")
    password = request.form.get("password")
    if User.query.filter_by(username=username).first():
        flash("Kullanıcı adı dolu.", "danger")
        return render_template("auth.html", active_tab="register")
    new_user = User(username=username, password=generate_password_hash(password, method='pbkdf2:sha256'))
    db.session.add(new_user)
    db.session.commit()
    flash("Kayıt başarılı.", "success")
    return render_template("auth.html", active_tab="login")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET": return render_template("auth.html", active_tab="login")
    username = request.form.get("username")
    password = request.form.get("password")
    user = User.query.filter_by(username=username).first()
    if user and check_password_hash(user.password, password):
        login_user(user)
        return redirect(url_for("index"))
    flash("Hatalı giriş.", "danger")
    return render_template("auth.html", active_tab="login")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth"))

@app.route("/dashboard")
@login_required
def dashboard():
    user_petitions = Petition.query.filter_by(user_id=current_user.id).order_by(Petition.date_created.desc()).all()
    return render_template("dashboard.html", petitions=user_petitions)

# --- YENİ EKLENEN: ADMIN PANELİ ROTASI ---
@app.route("/admin")
@login_required
def admin_panel():
    # Basit yetki kontrolü: Kullanıcı adı "admin" değilse içeri alma
    if current_user.username != "admin":
        flash("Bu alana sadece yöneticiler girebilir.", "danger")
        return redirect(url_for("dashboard"))
    
    # 1. Genel İstatistikler
    total_users = User.query.count()
    total_petitions = Petition.query.count()
    
    # 2. Kategorilere Göre Başvuru Sayıları (SQL Group By)
    category_stats = db.session.query(Petition.category, func.count(Petition.id)).group_by(Petition.category).all()
    
    labels = [c[0] for c in category_stats]
    data = [c[1] for c in category_stats]
    
    return render_template("admin.html", 
                           total_users=total_users, 
                           total_petitions=total_petitions,
                           labels=labels,
                           data=data)
# -----------------------------------------

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "GET":
        session.pop('result', None)
        return render_template("index.html", categories=CATEGORIES, mode="initial", user=current_user)

    step = request.form.get("step")
    if step == "answers": return cevap_ver()
    
    ocr_text = ""
    uploaded_file = request.files.get("dosya")
    if uploaded_file and uploaded_file.filename != '':
        res = extract_text_from_file(uploaded_file)
        if "text" in res: 
            ocr_text = res["text"]
            logger.info("OCR Başarılı")

    kategori = request.form.get("kategori")
    aciklama = request.form.get("aciklama", "").strip()
    
    rules_feedback = check_rules(kategori, aciklama, ocr_text)
    rag_context = search_legal_docs(aciklama + " " + ocr_text, kategori)
    
    if rules_feedback:
        flash(f"SİSTEM UYARISI: {rules_feedback}", "warning")

    final_context = f"""
    KULLANICI BEYANI: {aciklama}
    BELGE İÇERİĞİ (OCR): {ocr_text}
    SİSTEM UYARILARI (RULES): {rules_feedback}
    MEVZUAT BİLGİSİ (RAG): {rag_context}
    """
    
    if kategori not in CATEGORIES: return redirect(url_for("index"))
    
    result = call_llm(final_context, aciklama, ocr_text, rules_feedback, rag_context)
    
    if result.get("status") == "SORGU":
        session["state"] = {
            "kategori": kategori, 
            "aciklama": final_context, 
            "ad_soyad": current_user.username, 
            "questions": result.get("questions", [])
        }
        return render_template("index.html", mode="questions", sorular=enumerate(result.get("questions", [])), ad_soyad=current_user.username)

    if result.get("status") == "DILEKCE_HAZIR":
        try:
            new_petition = Petition(
                category=CATEGORIES[kategori]["title"],
                content=result.get("dilekce_metni", ""),
                advice=result.get("hukuki_oneriler", ""),
                ocr_data=ocr_text,
                user_id=current_user.id
            )
            db.session.add(new_petition)
            db.session.commit()
            session['current_petition_id'] = new_petition.id
        except Exception as e:
            logger.error(f"DB Kayıt Hatası: {e}")

    session["result"] = result
    return redirect(url_for("sonuc"))

def cevap_ver():
    state = session.get("state")
    if not state: return redirect(url_for("index"))
    
    result = get_mock_response(state.get("aciklama", ""), "Kullanıcı cevapları alındı.", "", "")
    result["status"] = "DILEKCE_HAZIR" 
    session["result"] = result
    
    try:
        new_petition = Petition(
            category=CATEGORIES[state["kategori"]]["title"],
            content=result.get("dilekce_metni", ""),
            advice=result.get("hukuki_oneriler", ""),
            ocr_data="Cevaplar alındı",
            user_id=current_user.id
        )
        db.session.add(new_petition)
        db.session.commit()
        session['current_petition_id'] = new_petition.id
    except: pass

    return redirect(url_for("sonuc"))

@app.route("/sonuc")
@login_required
def sonuc():
    p_id = request.args.get('id') or session.get('current_petition_id')
    if p_id:
        petition = Petition.query.get(p_id)
        if petition and petition.user_id == current_user.id:
            data = {"hitap_makam": "KAYITLI DİLEKÇE", "dilekce_metni": petition.content, "hukuki_oneriler": petition.advice}
            session['result'] = data
            return render_template("sonuc.html", data=data, ad_soyad=current_user.username)

    data = session.get("result")
    if not data or not data.get("dilekce_metni"):
        data = get_mock_response("Veri kurtarıldı.")
        session['result'] = data

    return render_template("sonuc.html", data=data, ad_soyad=current_user.username)

@app.route("/pdf")
@login_required
def pdf():
    data = session.get("result")
    if not data or not data.get("dilekce_metni"):
        data = get_mock_response("PDF için veri kurtarıldı.")

    html = PETITION_HTML_TEMPLATE.format(
        hitap_makam=data.get("hitap_makam", "İLGİLİ MAKAMA"),
        dilekce_metni=data.get("dilekce_metni", "").replace("\n", "<br>"),
        hukuki_oneriler=data.get("hukuki_oneriler", "").replace("\n", "<br>"),
        tarih=datetime.now().strftime("%d.%m.%Y"),
        ad_soyad=current_user.username
    )
    try:
        pdf_bytes = html_to_pdf_playwright(html)
        return send_file(io.BytesIO(pdf_bytes), as_attachment=True, download_name="Dilekce.pdf", mimetype="application/pdf")
    except: return "PDF Oluşturma Hatası", 500

@app.template_filter('strftime')
def _jinja2_filter_strftime(date, fmt=None):
    if not date or date == "now": return datetime.now().strftime(fmt or '%d.%m.%Y')
    if hasattr(date, 'strftime'): return date.strftime(fmt or '%d.%m.%Y')
    return str(date)

if __name__ == "__main__":
    app.run(debug=True, port=5000)