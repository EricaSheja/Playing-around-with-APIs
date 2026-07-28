from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# This db object gets connected to our Flask app in app.py
db = SQLAlchemy()

# Table 1: stores registered users
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

# Table 2: stores scholarships a user has saved
class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(300))
    link = db.Column(db.String(500))
    snippet = db.Column(db.Text)
    source_site = db.Column(db.String(200))
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

# Table 3: stores each search a user makes, so we can show their history
class SearchHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    keyword = db.Column(db.String(150))
    location = db.Column(db.String(100))  # a country name, or "Remote"
    searched_at = db.Column(db.DateTime, default=datetime.utcnow)
