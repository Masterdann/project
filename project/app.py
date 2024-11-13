from flask import Flask, render_template, request, redirect, url_for, session, abort
import calendar
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'supersecretkey'


def get_days_in_month(month_name):
    current_year = datetime.now().year
    month_num = list(calendar.month_name).index(month_name)
    _, num_days = calendar.monthrange(current_year, month_num)
    return num_days


months = {month: {day: {'red': 15, 'blue': 8, 'green': 13} for day in range(1, get_days_in_month(month) + 1)} for month in calendar.month_name[1:]}


user_selections = {month: {} for month in calendar.month_name[1:]}

# User ratings (used for priority access)
user_ratings = {
    'user1': 90,
    'user2': 80,
    'user3': 70,
    'user4': 80,
    'user5': 30,
    'user6': 10
}


ordered_users = sorted(user_ratings.items(), key=lambda item: item[1], reverse=True)


def get_user_position(username):
    for i, (user, rating) in enumerate(ordered_users):
        if user == username:
            return i
    return -1

#Admin Shift Selection page, where it should be uploaded the number of available shifts
@app.route('/admin_shift_selection/<month>', methods=['GET', 'POST'])
def admin_shift_selection(month):
    if month not in months:
        return "Invalid month!", 404

    if request.method == 'POST':
        for day in range(1, get_days_in_month(month) + 1):
            months[month][day]['red'] = int(request.form.get(f'red_shift_{day}', 0))
            months[month][day]['blue'] = int(request.form.get(f'blue_shift_{day}', 0))
            months[month][day]['green'] = int(request.form.get(f'green_shift_{day}', 0))
        
        return redirect(url_for('admin_shift_selection', month=month))

    return render_template('admin_shift_selection.html', shifts=months[month], month=month)


# User Shift Selection Page (users select their shifts)
@app.route('/user_shift_selection/<month>/<username>', methods=['GET', 'POST'])
def user_shift_selection(month, username):
    if month not in months:
        return "Invalid month!", 404

    user_position = get_user_position(username)

    for i in range(user_position):
        higher_rank_user = ordered_users[i][0]
        if not user_selections[month].get(higher_rank_user):
            return abort(403, description="Wait for higher-ranked users to select their shifts.")

    if request.method == 'POST':
        selected_shifts = {}
        for day in range(1, get_days_in_month(month) + 1):
            selected_shifts[day] = request.form.get(f'day_{day}_shift')

        user_selections[month][username] = selected_shifts

        
        for day, selected_shift in selected_shifts.items():
            if selected_shift in ['red', 'blue', 'green']:
                if months[month][day][selected_shift] > 0:
                    months[month][day][selected_shift] -= 1

        return redirect(url_for('user_schedule', month=month, username=username))

    
    return render_template('user_shift_selection.html', shifts=months[month], username=username, month=month)

   
# User Schedule Page (displays the user's selected shifts in a calendar view)
@app.route('/user_schedule/<month>/<username>')
def user_schedule(month, username):
    if month not in months:
        return "Invalid month!", 404
    selected_shifts = user_selections[month].get(username, {})
    return render_template('user_schedule.html', shifts=selected_shifts, username=username, month=month)

# Index page to select a month (redirects to admin shift selection for each month)
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        selected_month = request.form.get('selected_month')
        return redirect(url_for('admin_shift_selection', month=selected_month))
    
    return render_template('index.html', months=calendar.month_name[1:])

if __name__ == '__main__':
    app.run(debug=True)
