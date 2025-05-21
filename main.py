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

# Leer SECRET_KEY y DATABASE_URL de env (Railway) o usar valores locales
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

# Crear tablas al importar el módulo (para Gunicorn/Railway)
with app.app_context():
    db.create_all()

# ——— Login manager ———
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

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

# ——— Loader de usuarios ———
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

@app.route('/admin_manage')
@login_required
def admin_manage():
    users = User.query.filter(User.user_id != 'adminA') \
                      .order_by(User.rating.desc()).all()
    now = datetime.now()
    return render_template(
        'admin_manage.html',
        users=users,
        year=now.year,
        month=now.month
    )

@app.route('/admin_edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.name    = request.form['name']
        user.surname = request.form['surname']
        user.rating  = int(request.form['rating'])
        db.session.commit()
        return redirect(url_for('admin_manage'))
    return render_template('admin_edit.html', user=user)

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    u = User.query.get_or_404(user_id)
    db.session.delete(u)
    db.session.commit()
    return redirect(url_for('admin_manage'))

@app.route('/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if request.method == 'POST':
        name    = request.form['name']
        surname = request.form['surname']
        uid     = User.generate_user_id(name, surname)
        pwd     = User.generate_random_password()
        hashed  = generate_password_hash(pwd)
        new_u   = User(
            user_id=uid,
            user_password=hashed,
            name=name,
            surname=surname,
            rating=User.initial_rating()
        )
        db.session.add(new_u)
        db.session.commit()
        return redirect(
            url_for('user_success', user_id=uid, password=pwd)
        )
    return render_template('add_user.html')

@app.route('/user_success')
@login_required
def user_success():
    return render_template(
        'user_success.html',
        user_id=request.args.get('user_id'),
        password=request.args.get('password')
    )

@app.route('/admin_shift_selection/<int:year>/<int:month>', methods=['GET','POST'])
@login_required
def admin_shift_selection(year, month):
    if month < 1 or month > 12 or year < 1900:
        abort(404, "Invalid year or month!")
    days = get_days_in_month(year, month)

    if request.method == 'POST':
        for d in range(1, days+1):
            for color in ['red','blue','green']:
                avail = int(request.form.get(f'{color}_shift_{d}', 0))
                shift = Shift.query.filter_by(
                    year=year, month=month, day=d, shift_name=color
                ).first()
                if shift:
                    shift.available = avail
                else:
                    db.session.add(Shift(
                        shift_name=color,
                        year=year,
                        month=month,
                        day=d,
                        available=avail
                    ))
        db.session.commit()
        return redirect(
            url_for('admin_shift_selection', year=year, month=month)
        )

    shifts = {d: {c:0 for c in ['red','blue','green']} for d in range(1, days+1)}
    for s in Shift.query.filter_by(year=year, month=month).all():
        shifts[s.day][s.shift_name] = s.available

    prev_month = month - 1 or 12
    prev_year  = year - 1 if month == 1 else year
    next_month = month + 1 if month < 12 else 1
    next_year  = year + 1 if month == 12 else year

    return render_template(
        'admin_shift_selection.html',
        shifts=shifts,
        year=year, month=month,
        days_in_month=days,
        prev_month=prev_month,
        prev_year=prev_year,
        next_month=next_month,
        next_year=next_year
    )

@app.route('/user_shift_selection/<int:year>/<int:month>/<string:username>', methods=['GET','POST'])
@login_required
def user_shift_selection(year, month, username):
    user = User.query.filter_by(user_id=username).first_or_404()
    days = get_days_in_month(year, month)

    # Esperar a usuarios con mayor rating
    for u in User.query.filter(User.rating > user.rating).all():
        for d in range(1, days+1):
            if not any(u.user_id in sh.get_user_list()
                       for sh in Shift.query.filter_by(
                           year=year, month=month, day=d
                       ).all()):
                abort(403, f"Wait for higher-ranked user {u.user_id}")

    shifts = {}
    for d in range(1, days+1):
        row = {}
        for color in ['red','blue','green']:
            sh = Shift.query.filter_by(
                year=year, month=month, day=d, shift_name=color
            ).first()
            row[color] = (sh.available - len(sh.get_user_list())) if sh else 0
        shifts[d] = row

    error = None
    if request.method == 'POST':
        for d in range(1, days+1):
            sel = request.form.get(f'day_{d}_shift')
            if sel:
                sh = Shift.query.filter_by(
                    year=year, month=month, day=d, shift_name=sel
                ).first()
                if not sh or sh.is_full():
                    error = f"Shift '{sel}' on day {d} is full!"
                    break
                sh.add_user(user.user_id)
                db.session.commit()
        if error:
            return render_template(
                'user_shift_selection.html',
                shifts=shifts,
                username=username,
                year=year,
                month=month,
                error_message=error
            )
        return redirect(url_for('normal_staff'))

    return render_template(
        'user_shift_selection.html',
        shifts=shifts,
        username=username,
        year=year,
        month=month,
        error_message=error
    )

@app.route('/normal_staff')
@login_required
def normal_staff():
    return render_template('normal_staff.html')

@app.route('/my_schedule')
@login_required
def my_schedule():
    user = current_user
    year, month = datetime.now().year, datetime.now().month

    user_shifts = Shift.query.filter(
        Shift.user_ids.like(f"%{user.user_id}%")
    ).all()
    selected = {
        (s.year, s.month, s.day): s.shift_name
        for s in user_shifts
    }

    days = get_days_in_month(year, month)
    shifts = []
    for d in range(1, days+1):
        name = selected.get((year, month, d), 'unselected')
        color = name if name in ['red','blue','green'] else 'gray'
        shifts.append({'day': d, 'shift': name, 'color': color})

    return render_template(
        'my_schedule.html',
        year=year,
        month=month,
        shifts=shifts
    )

@app.route('/profile', methods=['GET','POST'])
@login_required
def profile():
    user = current_user
    if request.method == 'POST':
        user.name    = request.form['name']
        user.surname = request.form['surname']
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and allowed_file(file.filename):
                fn = secure_filename(file.filename)
                path = os.path.join(app.config['UPLOAD_FOLDER'], fn)
                file.save(path)
                user.profile_photo = f'static/uploads/{fn}'
        db.session.commit()
        return redirect(url_for('profile'))
    return render_template('profile.html', user=user)

# ——— Arranque de la app ———
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
