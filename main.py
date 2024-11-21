import os
import random
import string
import calendar
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session, abort
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


"""
adminA
DF|\CC\S

testT
{o/#$T"Z
"""

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] =\
        'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(20), unique=True, nullable=False) 
    user_password = db.Column(db.String(8), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<User {self.user_id}>'

    def generate_user_id(name, surname):
        base_id = f"{name}{surname[0].upper()}"
        user_id = base_id
        counter = 1
        while User.query.filter_by(user_id=user_id).first() is not None:
            user_id = f"{base_id}{counter}"
            counter += 1
        return user_id

    def generate_random_password(length=8):
        characters = string.ascii_letters + string.digits + string.punctuation
        return ''.join(random.choice(characters) for _ in range(length))
    
    def initial_rating():
        return 0
    
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
        if self.user_ids:
            current_users = self.user_ids.split(',')
        else:
            current_users = []
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

    
def get_days_in_month(year, month):
    return calendar.monthrange(year, month)[1]

@app.template_filter('get_days_in_month')
def get_days_in_month_filter(year, month):
    return get_days_in_month(year, month)



@app.route('/admin_shift_selection/<int:year>/<int:month>', methods=['GET', 'POST'])
def admin_shift_selection(year, month):
    if month < 1 or month > 12 or year < 1900:
        return "Invalid year or month!", 404

    days_in_month = get_days_in_month(year, month)
    
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
            
    return render_template('admin_shift_selection.html', shifts=shifts, year=year, month=month)

@app.route('/user_shift_selection/<int:year>/<int:month>/<string:username>', methods=['GET', 'POST'])
def user_shift_selection(year, month, username):
    user = User.query.filter_by(user_id=username).first()
    if not user:
        return "User not found!", 404

    days_in_month = get_days_in_month(year, month)

    all_users = User.query.order_by(User.rating.desc()).all()
    grouped_users = {}
    for u in all_users:
        if u.rating not in grouped_users:
            grouped_users[u.rating] = []
        grouped_users[u.rating].append(u.user_id)

    user_group_rating = user.rating
    for rating, user_ids in grouped_users.items():
        if rating > user_group_rating:
            for higher_user_id in user_ids:
                if not Shift.query.filter_by(year=year, month=month, user_ids=higher_user_id).first():
                    return abort(403, description="Wait for higher-ranked users to select their shifts.")

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
                    current_users = shift.get_user_list()
                    if len(current_users) < shift.available:
                        shift.add_user(user.user_id)
                        db.session.commit()
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

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user_id = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(user_id=user_id).first()
        
        if user and check_password_hash(user.user_password, password): 
            if user_id == 'adminA': 
                return redirect(url_for('admin_main'))  
            else:
                return redirect(url_for('normal_staff')) 
        else:
            error = 'Invalid Credentials. Please try again.'

    return render_template('login.html', error=error)
    
@app.route('/admin_main')
def admin_main():
    return render_template('admin_main.html')

@app.route('/admin_manage')
def admin_manage():
    user = User.query.filter(User.user_id != 'adminA').order_by(User.rating.desc()).all()
    return render_template('admin_manage.html', users=user)

@app.route('/admin_edit/<int:user_id>', methods=['GET', 'POST'])
def admin_edit(user_id):
    user = User.query.get(user_id)  
    if request.method == 'POST':
        user.name = request.form['name']
        user.surname = request.form['surname']
        user.rating = request.form['rating']
        
        db.session.commit() 
        return redirect(url_for('admin_manage'))

    return render_template('admin_edit.html', user=user) 


    return render_template('admin_edit.html')

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    user_to_delete = User.query.get(user_id)
    
    if user_to_delete:
        db.session.delete(user_to_delete)
        db.session.commit()
        return redirect(url_for('admin_manage'))
    else:
        return "User not found", 404

@app.route('/normal_staff')
def normal_staff():
    return render_template('normal_staff.html')

@app.route('/add_user', methods=['GET', "POST"])
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
def user_success():
    user_id = request.args.get('user_id')
    password = request.args.get('password')
    return render_template('user_success.html', user_id=user_id, password=password)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  
    app.run(debug=True)