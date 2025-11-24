from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Veritabanı nesnesini oluşturuyoruz
db = SQLAlchemy()

# 1. KULLANICI TABLOSU
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False) # Hashlenmiş şifre tutulacak
    petitions = db.relationship('Petition', backref='author', lazy=True)

# 2. DİLEKÇE TABLOSU
class Petition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False) # Dilekçe metni
    advice = db.Column(db.Text, nullable=True)   # Hukuki öneriler
    ocr_data = db.Column(db.Text, nullable=True) # OCR'dan okunan ham veri
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    # İlişki: Bu dilekçe hangi kullanıcıya ait?
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)