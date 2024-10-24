import os
import random
import string
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy

"""
adminA
8|DJVuF:

testT2
l|=3m@xP
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

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user_id = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(user_id=user_id).first()
        
        if user and check_password_hash(user.user_password, password): 
            if user_id == 'adminA': 
                return redirect(url_for('add_user'))  
            else:
                return redirect(url_for('normal_staff')) 
        else:
            error = 'Invalid Credentials. Please try again.'

    return render_template('login.html', error=error)
    
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

        hashed_password = generate_password_hash(password)

        new_user = User(user_id=user_id, user_password=hashed_password, name=name, surname=surname)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('user_success', user_id=user_id, password=password))
    return render_template('add_user.html')

@app.route('/user_success')
def user_success():
    user_id = request.args.get('user_id')
    password = request.args.get('password')
    return render_template('user_success.html', user_id=user_id, password=password)

@app.route('/admin1')
def admin1():
    return render_template('admin1.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  
    app.run(debug=True)
