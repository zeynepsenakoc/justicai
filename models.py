from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    
    
    full_name = db.Column(db.String(150), nullable=True)
    tckn = db.Column(db.String(11), nullable=True)
    address = db.Column(db.Text, nullable=True)
  
    
    petitions = db.relationship('Petition', backref='author', lazy=True)
    is_admin = db.Column(db.Boolean, default=False)

class Petition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    hitap_makam = db.Column(db.Text, nullable=True, default="DİLEKÇE BAŞLIĞI YOK")
    advice = db.Column(db.Text, nullable=True)
    ocr_data = db.Column(db.Text, nullable=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    

    processing_time = db.Column(db.Float, default=0.0)
    token_count = db.Column(db.Integer, default=0)
    cost_usd = db.Column(db.Float, default=0.0)

    status = db.Column(db.String(50), default="Taslak") 
    tracking_number = db.Column(db.String(50), nullable=True)
    signature_data = db.Column(db.Text, nullable=True)
    
  
    improvement_note = db.Column(db.Text, nullable=True)

    document_hash = db.Column(db.String(64), nullable=True)


    graph_data = db.Column(db.JSON, nullable=True)


    feedback = db.relationship('Feedback', backref='petition', uselist=False, lazy=True)

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    petition_id = db.Column(db.Integer, db.ForeignKey('petition.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Boolean, nullable=False) 
    comment = db.Column(db.String(500), nullable=True) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('petition_id', 'user_id', name='unique_user_feedback'),
    )