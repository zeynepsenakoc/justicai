from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    petitions = db.relationship('Petition', backref='author', lazy=True)

class Petition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    advice = db.Column(db.Text, nullable=True)
    ocr_data = db.Column(db.Text, nullable=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # --- YENİ EKLENEN PERFORMANS METRİKLERİ ---
    processing_time = db.Column(db.Float, default=0.0)  # İşlem süresi (Saniye)
    token_count = db.Column(db.Integer, default=0)      # Harcanan toplam token
    cost_usd = db.Column(db.Float, default=0.0)         # Tahmini maliyet ($)