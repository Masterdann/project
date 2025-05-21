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

# ——— Crear tablas y seed de admin y shifts ———
with app.app_context():
    db.create_all()
    now = datetime.now()
    # Seed: crear adminA si no existe
    if not User.query.filter_by(user_id='adminA').first():
        hashed = generate_password_hash("admin123")
        admin = User(
            user_id       = "adminA",
            user_password = hashed,
            name          = "Admin",
            surname       = "Account",
            rating        = 5,
            profile_photo = None
        )
        db.session.add(admin)
    # Seed: crear shifts para el mes actual
    year = now.year
    month = now.month
    days = calendar.monthrange(year, month)[1]
    for d in range(1, days+1):
        for color in ['red','blue','green']:
            if not Shift.query.filter_by(year=year, month=month, day=d, shift_name=color).first():
                db.session.add(Shift(shift_name=color, year=year, month=month, day=d, available=0))
    db.session.commit()

# ——— Login manager ———
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in.'

@login_manager.user_loader
def loader_user(user_id):
    return User.query.get(int(user_id))

# ——— Context processor ———
@app.context_processor
def inject_globals():
    now = datetime.now()
    return {
        'year': now.year,
        'month': now.month,
        'current_year': now.year,
        'current_month': now.month
    }

# ——— Rutas ———
@app.route('/', methods=['GET','POST'])
def login():
    error = None
    if request.method == 'POST':
        uid = request.form.get('username')
        pwd = request.form.get('password')
        user = User.query.filter_by(user_id=uid).first()
        if user and check_password_hash(user.user_password, pwd):
            login_user(user)
            if uid == 'adminA':
                return redirect(url_for('admin_main'))
            else:
                return redirect(url_for('user_shift_selection', year=now.year, month=now.month, username=uid))
        error = 'Credenciales inválidas.'
    return render_template('login.html', error=error)

@app.route('/add_user', methods=['GET','POST'])
@login_required
def add_user():
    if request.method == 'POST':
        name    = request.form.get('name')
        surname = request.form.get('surname')
        uid     = User.generate_user_id(name, surname)
        pwd     = User.generate_random_password()
        hashed  = generate_password_hash(pwd)
        new_u   = User(user_id=uid, user_password=hashed, name=name, surname=surname, rating=0)
        db.session.add(new_u)
        db.session.commit()
        return redirect(url_for('user_success', user_id=uid, password=pwd))
    return render_template('add_user.html')

# ... resto de rutas sin cambios ...

@app.route('/user_shift_selection/<int:year>/<int:month>/<string:username>', methods=['GET','POST'])
@login_required
def user_shift_selection(year, month, username):
    user = User.query.filter_by(user_id=username).first_or_404()
    days = get_days_in_month(year, month)
    # lógica de selección de turnos...
    return render_template('user_shift_selection.html', shifts={}, username=username, year=year, month=month, error_message=None)

# ——— Arranque de la app ———
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
