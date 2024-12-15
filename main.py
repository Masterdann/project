"""
adminA
DF|\CC\S

RogerE
%3k"TUV~

test2
M:SA*q=I

test3
FJI|<_S"

test4
^6ogHeq@

test5
1-xUOqZ@

test6
|@A%+#iY

test8
|>><0A^G

"""
import os
import random
import string
import calendar
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime
from werkzeug.utils import secure_filename


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'secret_key'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'


# Configure upload folder
UPLOAD_FOLDER = os.path.join(basedir, 'static/uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
db = SQLAlchemy(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(20), unique=True, nullable=False)
    user_password = db.Column(db.String(100), nullable=False) 
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    profile_photo = db.Column(db.String(200), nullable=True)
    def __repr__(self):
        return f'<User {self.user_id}>'

    @staticmethod
    def generate_user_id(name, surname):
        base_id = f"{name}{surname[0].upper()}"
        user_id = base_id
        counter = 1
        while User.query.filter_by(user_id=user_id).first() is not None:
            user_id = f"{base_id}{counter}"
            counter += 1
        return user_id

    @staticmethod
    def generate_random_password(length=8):
        characters = string.ascii_letters + string.digits + string.punctuation
        return ''.join(random.choice(characters) for _ in range(length))

    @staticmethod
    def initial_rating():
        return 0

    def get_id(self):
        return str(self.id)


class Shift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shift_name = db.Column(db.String(20), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    month = db.Column(db.Integer, nullable=False)
    day = db.Column(db.Integer, nullable=False)
    available = db.Column(db.Integer, nullable=False)
    user_ids = db.Column(db.Text, nullable=True) 

    def __repr__(self):
        return f'<Shift {self.id} - {self.shift_name} ({self.year}-{self.month}-{self.day})>'

    def add_user(self, user_id):
        if self.is_full():
            raise ValueError("Shift is already full.")
        current_users = self.get_user_list() if self.user_ids else []
        if user_id not in current_users:
            current_users.append(user_id)
            self.user_ids = ','.join(current_users)

    def remove_user(self, user_id):
        if self.user_ids:
            current_users = self.user_ids.split(',')
            if user_id in current_users:
                current_users.remove(user_id)
                self.user_ids = ','.join(current_users) if current_users else None

    def get_user_list(self):
        return self.user_ids.split(',') if self.user_ids else []

    def is_full(self):
        current_users = self.get_user_list()
        return len(current_users) >= self.available

@login_manager.user_loader
def loader_user(user_id):
    return User.query.get(int(user_id))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

def get_days_in_month(year, month):
    return calendar.monthrange(year, month)[1]

@app.template_filter('get_days_in_month')
def get_days_in_month_filter(year, month):
    return get_days_in_month(year, month)

@app.route('/admin_shift_selection/<int:year>/<int:month>', methods=['GET', 'POST'])
@login_required
def admin_shift_selection(year, month):
    if month < 1 or month > 12 or year < 1900:
        return "Invalid year or month!", 404

    days_in_month = get_days_in_month(year, month)

    if month == 12:
        next_month = 1
        next_year = year + 1
    else:
        next_month = month + 1
        next_year = year

    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year

    if request.method == 'POST':
        for day in range(1, days_in_month + 1):
            red_shift = int(request.form.get(f'red_shift_{day}', 0))
            blue_shift = int(request.form.get(f'blue_shift_{day}', 0))
            green_shift = int(request.form.get(f'green_shift_{day}', 0))

            for shift_name, available in [('red', red_shift), ('blue', blue_shift), ('green', green_shift)]:
                shift = Shift.query.filter_by(year=year, month=month, day=day, shift_name=shift_name).first()
                if shift:
                    shift.available = available
                else:
                    new_shift = Shift(
                        shift_name=shift_name,
                        year=year,
                        month=month,
                        day=day,
                        available=available
                    )
                    db.session.add(new_shift)

        db.session.commit()
        return redirect(url_for('admin_shift_selection', year=year, month=month))

    shifts = {}
    for day in range(1, days_in_month + 1):
        shifts[day] = {shift_name: 0 for shift_name in ['red', 'blue', 'green']}
        for shift in Shift.query.filter_by(year=year, month=month, day=day).all():
            shifts[day][shift.shift_name] = shift.available

    return render_template(
        'admin_shift_selection.html',
        shifts=shifts,
        year=year,
        month=month,
        days_in_month=days_in_month,
        prev_month=prev_month,
        prev_year=prev_year,
        next_month=next_month,
        next_year=next_year
    )

@app.route('/user_shift_selection/<int:year>/<int:month>/<string:username>', methods=['GET', 'POST'])
@login_required
def user_shift_selection(year, month, username):
    user = User.query.filter_by(user_id=username).first()
    if not user:
        return "User not found!", 404

    days_in_month = get_days_in_month(year, month)

    higher_ranked_users = User.query.filter(User.rating > user.rating).all()
    for higher_user in higher_ranked_users:
        for day in range(1, days_in_month + 1):
            shifts_for_day = Shift.query.filter_by(year=year, month=month, day=day).all()
            user_selected_for_day = any(
                higher_user.user_id in shift.get_user_list() for shift in shifts_for_day
            )
            if not user_selected_for_day:
                return abort(403, description=f"Wait for higher-ranked user {higher_user.name} ({higher_user.user_id}) to complete their shift selection for the month.")

    shifts = {}
    for day in range(1, days_in_month + 1):
        shifts[day] = {shift_name: 0 for shift_name in ['red', 'blue', 'green']}
        for shift in Shift.query.filter_by(year=year, month=month, day=day).all():
            current_users = shift.get_user_list()
            remaining_slots = shift.available - len(current_users) if current_users else shift.available
            shifts[day][shift.shift_name] = remaining_slots

    error_message = None

    if request.method == 'POST':
        for day in range(1, days_in_month + 1):
            selected_shift = request.form.get(f'day_{day}_shift')

            if selected_shift in ['red', 'blue', 'green']:
                shift = Shift.query.filter_by(year=year, month=month, day=day, shift_name=selected_shift).first()
                conflicting_shift = Shift.query.filter(
                    Shift.year == year,
                    Shift.month == month,
                    Shift.day == day,
                    Shift.user_ids.like(f"%{user.user_id}%")
                ).first()

                if conflicting_shift:
                    error_message = f"You already selected {conflicting_shift.shift_name} on day {day}. You cannot select multiple shifts for the same day."
                    break

                if shift:
                    if shift.is_full():
                        error_message = f"The '{selected_shift}' shift on day {day} is already full."
                        break
                    try:
                        shift.add_user(user.user_id)
                        db.session.commit()
                    except ValueError as e:
                        error_message = str(e)
                        break
                else:
                    error_message = f"Shift '{selected_shift}' on day {day} is unavailable!"
                    break

        if error_message:
            return render_template(
                'user_shift_selection.html',
                shifts=shifts,
                username=username,
                year=year,
                month=month,
                error_message=error_message
            )

        return redirect(url_for('normal_staff'))

    return render_template(
        'user_shift_selection.html',
        shifts=shifts,
        username=username,
        year=year,
        month=month,
        error_message=error_message
    )

@app.context_processor
def inject_current_date():
    now = datetime.now()
    return {'current_year': now.year, 'current_month': now.month}

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user_id = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(user_id=user_id).first()
        print (user_id, password)
        if user and check_password_hash(user.user_password, password):
            login_user(user)
            if user_id == 'adminA':
                return redirect(url_for('admin_main'))
            else:
                return redirect(url_for('normal_staff'))
        else:
            error = 'Invalid Credentials. Please try again.'

    return render_template('login.html', error=error)

@app.route('/admin_main')
@login_required
def admin_main():
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    return render_template('admin_main.html', year=current_year, month=current_month)

@app.route('/admin_manage')
@login_required
def admin_manage():
    now = datetime.now()
    current_year = now.year
    current_month = now.month
    user = User.query.filter(User.user_id != 'adminA').order_by(User.rating.desc()).all()
    return render_template('admin_manage.html', users=user, year=current_year, month=current_month)

@app.context_processor
def inject_date():
    now = datetime.now()
    return {'year': now.year, 'month': now.month}

@app.route('/admin_edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit(user_id):
    user = User.query.get(user_id)
    if request.method == 'POST':
        user.name = request.form['name']
        user.surname = request.form['surname']
        user.rating = request.form['rating']
        db.session.commit()
        return redirect(url_for('admin_manage'))
    return render_template('admin_edit.html', user=user)


@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    user_to_delete = User.query.get(user_id)
    if user_to_delete:
        db.session.delete(user_to_delete)
        db.session.commit()
        return redirect(url_for('admin_manage'))
    else:
        return "User not found", 404

@app.route('/normal_staff')
@login_required
def normal_staff():
    return render_template('normal_staff.html')


@app.route('/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']

        user_id = User.generate_user_id(name, surname)
        password = User.generate_random_password()
        rating = User.initial_rating()

        hashed_password = generate_password_hash(password)

        new_user = User(user_id=user_id, user_password=hashed_password, name=name, surname=surname, rating=rating)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('user_success', user_id=user_id, password=password))
    return render_template('add_user.html')


@app.route('/user_success')
@login_required
def user_success():
    user_id = request.args.get('user_id')
    password = request.args.get('password')
    return render_template('user_success.html', user_id=user_id, password=password)


@app.route('/my_schedule', methods=['GET'])
@login_required
def my_schedule():
    user = current_user  # Get the current logged-in user
    year = datetime.now().year
    month = datetime.now().month

    # Get all shifts for the current user
    user_shifts = Shift.query.filter(
        Shift.user_ids.like(f"%{user.user_id}%")
    ).all()

    # Build a dictionary of shifts the user has selected
    selected_shifts = {
        (shift.year, shift.month, shift.day): shift.shift_name for shift in user_shifts
    }

    # Get all shifts for the current month
    days_in_month = get_days_in_month(year, month)

    # Map shift names to colors
    shift_colors = {
        'red': 'red',
        'blue': 'blue',
        'green': 'green',
        'unselected': 'gray',
    }

    # Prepare data for rendering
    shifts = []
    for day in range(1, days_in_month + 1):
        if (year, month, day) in selected_shifts:
            shift_name = selected_shifts[(year, month, day)]
            shifts.append({'day': day, 'shift': shift_name, 'color': shift_colors[shift_name]})
        else:
            shifts.append({'day': day, 'shift': 'unselected', 'color': shift_colors['unselected']})

    return render_template(
        'my_schedule.html',
        year=year,
        month=month,
        shifts=shifts,
    )

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = current_user

    if request.method == 'POST':
        user.name = request.form['name']
        user.surname = request.form['surname']

        # Handle file upload
        if 'profile_photo' in request.files:
            file = request.files['profile_photo']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                user.profile_photo = f'static/uploads/{filename}'  

        db.session.commit()
        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)


"""
-------------------------------------
@app.route('/user_schedule/<int:year>/<int:month>/<string:username>', methods=['GET', 'POST'])
--------------------------------------
"""


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
