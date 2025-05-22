# -*- coding: utf-8 -*-

import calendar
import os
import random
import string
from datetime import datetime

from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import (
    check_password_hash,
    generate_password_hash,
)

BASEDIR = os.path.abspath(os.path.dirname(__file__))


app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "dev-secret-key"
)
db_url = os.environ.get("DATABASE_URL") or (
    f"sqlite:///{os.path.join(BASEDIR, 'fallback.db')}"
)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

UPLOAD_FOLDER = os.path.join(BASEDIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def inject_current_date():
    now = datetime.now()
    return {
        "year": now.year,
        "month": now.month,
        "current_year": now.year,
        "current_month": now.month,
    }


app.context_processor(inject_current_date)


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = (
    "Please log in to access this page."
)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(20), unique=True, nullable=False)
    user_password = db.Column(db.String(300), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    profile_photo = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f"<User {self.user_id}>"

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
        chars = (
            string.ascii_letters
            + string.digits
            + string.punctuation
        )
        return "".join(random.choice(chars) for _ in range(length))

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
        return (
            f"<Shift {self.id} - {self.shift_name} "
            f"({self.year:04d}-{self.month:02d}-{self.day:02d})>"
        )

    def get_user_list(self):
        if self.user_ids:
            return self.user_ids.split(",")
        return []

    def is_full(self):
        return len(self.get_user_list()) >= self.available

    def add_user(self, user_id):
        if self.is_full():
            raise ValueError("Shift is already full.")
        users = self.get_user_list()
        if user_id not in users:
            users.append(user_id)
            self.user_ids = ",".join(users)

    def remove_user(self, user_id):
        users = self.get_user_list()
        if user_id in users:
            users.remove(user_id)
            self.user_ids = ",".join(users) if users else None


with app.app_context():
    if not User.query.filter_by(user_id="adminA").first():
        hashed_pw = generate_password_hash("admin123")
        admin = User(
            user_id="adminA",
            user_password=hashed_pw,
            name="Admin",
            surname="Account",
            rating=5,
            profile_photo=None,
        )
        db.session.add(admin)
        db.session.commit()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.template_filter("get_days_in_month")
def get_days_in_month_filter(year, month):
    return calendar.monthrange(year, month)[1]


@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        uid = request.form["username"]
        pwd = request.form["password"]
        user = User.query.filter_by(user_id=uid).first()
        if user and check_password_hash(user.user_password, pwd):
            login_user(user)
            if uid == "adminA":
                return redirect(url_for("admin_main"))
            return redirect(url_for("normal_staff"))
        error = "Invalid Credentials. Please try again."
    return render_template("login.html", error=error)


@app.route("/logout")
@login_required
 def logout():
     logout_user()
     return redirect(url_for("login"))


@app.route("/admin_main")
@login_required
 def admin_main():
     return render_template("admin_main.html")


@app.route("/admin_manage")
@login_required
 def admin_manage():
     users = (
         User.query
         .filter(User.user_id != "adminA")
         .order_by(User.rating.desc())
         .all()
     )
     return render_template("admin_manage.html", users=users)


@app.route("/admin_edit/<int:user_id>", methods=["GET", "POST"])
@login_required
 def admin_edit(user_id):
     user = User.query.get_or_404(user_id)
     if request.method == "POST":
         user.name = request.form["name"]
         user.surname = request.form["surname"]
         user.rating = int(request.form["rating"])
         db.session.commit()
         return redirect(url_for("admin_manage"))
     return render_template("admin_edit.html", user=user)


@app.route("/delete_user/<int:user_id>", methods=["POST"])
@login_required
 def delete_user(user_id):
     user = User.query.get_or_404(user_id)
     db.session.delete(user)
     db.session.commit()
     return redirect(url_for("admin_manage"))


@app.route("/add_user", methods=["GET", "POST"])
@login_required
 def add_user():
     if request.method == "POST":
         name = request.form["name"]
         surname = request.form["surname"]
         uid = User.generate_user_id(name, surname)
         pwd = User.generate_random_password()
         hashed_pw = generate_password_hash(pwd)
         new_user = User(
             user_id=uid,
             user_password=hashed_pw,
             name=name,
             surname=surname,
             rating=User.initial_rating(),
         )
         db.session.add(new_user)
         db.session.commit()
         return redirect(
             url_for(
                 "user_success", user_id=uid, password=pwd
             )
         )
     return render_template("add_user.html")


@app.route("/user_success")
@login_required
 def user_success():
     return render_template(
         "user_success.html",
         user_id=request.args.get("user_id"),
         password=request.args.get("password"),
     )


@app.route(
    "/admin_shift_selection/<int:year>/<int:month>",
    methods=["GET", "POST"],
)
@login_required
 def admin_shift_selection(year, month):
     if not (1 <= month <= 12 and year >= 1900):
         abort(404, "Invalid year or month!")
     days = calendar.monthrange(year, month)[1]
     if request.method == "POST":
         for day in range(1, days + 1):
             for color in ("red", "blue", "green"):
                 form_key = f"{color}_shift_{day}"
                 available = int(request.form.get(form_key, 0))
                 shift = Shift.query.filter_by(
                     year=year,
                     month=month,
                     day=day,
                     shift_name=color,
                 ).first()
                 if shift:
                     shift.available = available
                 else:
                     db.session.add(
                         Shift(
                             shift_name=color,
                             year=year,
                             month=month,
                             day=day,
                             available=available,
                         )
                     )
         db.session.commit()
         return redirect(
             url_for("admin_shift_selection", year=year, month=month)
         )
     shifts = {d: {c: 0 for c in ("red", "blue", "green")} for d in range(1, days + 1)}
     for shift in Shift.query.filter_by(year=year, month=month).all():
         shifts[shift.day][shift.shift_name] = shift.available
     prev_month = 12 if month == 1 else month - 1
     prev_year = year - 1 if month == 1 else year
     next_month = 1 if month == 12 else month + 1
     next_year = year + 1 if month == 12 else year
     return render_template(
         "admin_shift_selection.html",
         shifts=shifts,
         year=year,
         month=month,
         days_in_month=days,
         prev_month=prev_month,
         prev_year=prev_year,
         next_month=next_month,
         next_year=next_year,
     )


@app.route(
    "/user_shift_selection/<int:year>/<int:month>/<string:username>",
    methods=["GET", "POST"],
)
@login_required
 def user_shift_selection(year, month, username):
     days = calendar.monthrange(year, month)[1]
     # Remaining logic goes here.
     return render_template(
         "user_shift_selection.html",
         shifts={},  # define shifts
         username=username,
         year=year,
         month=month,
         days_in_month=days,
         error_message=None,
     )


@app.route("/normal_staff")
@login_required
 def normal_staff():
     return render_template("normal_staff.html")


@app.route("/my_schedule")
@login_required
 def my_schedule():
     # Logic for user's schedule
     return render_template("my_schedule.html", shifts={})


@app.route("/profile", methods=["GET", "POST"])
@login_required
 def profile():
     # Logic for profile view
     return render_template("profile.html", user=current_user)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
