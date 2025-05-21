import os
import random
import string
import calendar
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ——— Configuración básica ———
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static'
)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL') or
    f"sqlite:///{os.path.join(basedir, 'fallback.db')}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Carpeta de uploads
UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ——— Inyección global de fecha para los templates ———
@app.context_processor
def inject_current_date():
    now = datetime.now()
    return {
        # para base_admin.html (admin)
        'year': now.year,
        'month': now.month,
        # para base.html (staff normal)
        'current_year': now.year,
        'current_month': now.month
    }

# ——— Inicializar base de datos ———
db = SQLAlchemy(app)

def allowed_file(filename):
    return (
        '.' in filename and
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )

# ——— Modelos ———
class User(UserMixin, db.Model):
    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.String(20), unique=True, nullable=False)
    user_password  = db.Column(db.St_
