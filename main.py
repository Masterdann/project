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
    user_password  = db.Column(db.String(300), nullable=False)
    name           = db.Column(db.String(100), nullable=False)
    surname        = db.Column(db.String(100), nullable=False)
    rating         = db.Column(db.Integer, nullable=False)
    profile_photo  = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f'<User {self.user_id}>'

    @staticmethod
    def generate_user_id(name, surname):
        base_id = f"{name}{surname[0].upper()}"
        uid = base_id
        counter = 1
        while User.query.filter_by(user_id=uid).first():
            uid = f"{base_id}{counter}"
            counter += 1
        return uid

    @staticmethod
    def generate_random_password(length=8):
        chars = string.ascii_letters + string.digits + string.punctuation
        return ''.join(random.choice(chars) for _ in range(length))

    @staticmethod
    def initial_rating():
        return 0

    def get_id(self):
        return str(self.id)

class Shift(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    shift_name  = db.Column(db.String(20), nullable=False)
    year        = db.Column(db.Integer, nullable=False)
    month       = db.Column(db.Integer, nullable=False)
    day         = db.Column(db.Integer, nullable=False)
    available   = db.Column(db.Integer, nullable=False)
    user_ids    = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return (
            f'<Shift {self.id} - {self.shift_name} '
            f'({self.year}-{self.month:02d}-{self.day:02d})>'
        )

    def get_user_list(self):
        return self.user_ids.split(',') if self.user_ids else []

    def is_full(self):
        return len(self.get_user_list()) >= self.available

    def add_user(self, user_id):
        if self.is_full():
            raise ValueError("Shift is already full.")
        users = self.get_user_list()
        if user_id not in users:
            users.append(user_id)
            self.user_ids = ','.join(users)

    def remove_user(self, user_id):
        users = self.get_user_list()
        if user_id in users:
            users.remove(user_id)
            self.user_ids = ','.join(users) if users else None

# ——— Crear tablas AHORA que los modelos existen ———
with app.app_context():
    db.create_all()

# ——— Login manager ———
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def loader_user(user_id):
    return User.query.get(int(user_id))

# ——— Helpers de calendario ———
def get_days_in_month(year, month):
    return calendar.monthrange(year, month)[1]

@app.template_filter('get_days_in_month')
def get_days_in_month_filter(year, month):
    return get_days_in_month(year, month)

# ——— Rutas ———

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        uid = request.form['username']
        pwd = request.form['password']
        user = User.query.filter_by(user_id=uid).first()
        if user and check_password_hash(user.user_password, pwd):
            login_user(user)
            return redirect(
                url_for('admin_main') if uid == 'adminA'
                else url_for('normal_staff')
            )
        error = 'Invalid Credentials. Please try again.'
    return render_template('login.html', error=error)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin_main')
@login_required
def admin_main():
    now = datetime.now()
    return render_template(
        'admin_main.html',
        year=now.year,
        month=now.month
    )

# … (resto de rutas igual que antes) …

# ——— Arranque de la app ———
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
