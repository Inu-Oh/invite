from datetime import datetime

from flask import redirect, render_template, session
from functools import wraps
import inflect

from flask import render_template


# List of months for datetime and time string formatting in functions
months = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December"
]


def apology(message, code=400):
    """Render message as an apology to user."""

    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def get_time(time_str):
    """Converts time string from HTML form into datetime object"""
    date_data, time_data = time_str.split(" T ")
    year, month, day = date_data.split("-")
    hour_minutes, am_pm = time_data.split(" ")
    hour, minutes = hour_minutes.split(":")
    hour = int(hour) + 12 if am_pm == "pm" else int(hour)
    return datetime(int(year), int(month), int(day), hour, int(minutes))


def get_time_elements(time_str):
    """Returns time variables for next two functions"""
    date_data, time_data = time_str.split(" ")
    year, month, day = date_data.split("-")
    hour, minutes, _ = time_data.split(":")
    am_pm = "pm" if int(hour) >= 12 else "am"
    ampm_hour = int(hour) % 12
    return int(year), int(month), int(day), int(hour), minutes, am_pm, ampm_hour


def get_time_and_str(time_str):
    """Converts SQL time data into datetime object and humanized todo time string for HTML display"""
    year, month, day, hour, minutes, am_pm, ampm_hour = get_time_elements(time_str)
    event_time_str = f"{months[month-1]} {day} at {ampm_hour}:{minutes} {am_pm}"
    event_time = datetime(year, month, day, hour, int(minutes))
    return event_time, event_time_str


def get_strtime(time_str):
    """Converts SQL time data into humanized todo time string for HTML display"""
    _, month, day, _, minutes, am_pm, ampm_hour = get_time_elements(time_str)
    return f"{months[month-1]} {day} at {ampm_hour}:{minutes} {am_pm}"


def get_todo_names(database, event_id):
    """Return list friend names that have been added ToDo"""
    friend_list = []
    friend_data  = database.execute(
        "SELECT friend_id FROM friends WHERE event_id = ?", event_id
    )
    for friend in friend_data:
        friend_name = database.execute(
            "SELECT name FROM users WHERE id = ?", friend["friend_id"]
        )
        friend_list.append(friend_name[0]["name"])
    if friend_list:
        friend_names = inflect.engine()
        return friend_names.join(friend_list)
    return False


def get_invite_names(database, event_user_id, event_id, user_id):
    """Return list friend names that have been added to invite"""
    friend_name = database.execute(
        "SELECT name FROM users WHERE id = ?", event_user_id
    )
    owner = friend_name[0]["name"]
    user_name = database.execute(
        "SELECT name FROM users WHERE id = ?", user_id
    )
    friend_list = [owner]
    friend_data  = database.execute(
        "SELECT friend_id FROM friends WHERE event_id = ?", event_id
    )
    for friend in friend_data:
        name = database.execute(
            "SELECT name FROM users WHERE id = ?", friend["friend_id"]
        )
        if name[0]["name"] != user_name[0]["name"]:
            friend_list.append(name[0]["name"])
    if friend_list:
        friend_names = inflect.engine()
        return friend_names.join(friend_list), owner
    return owner


def login_required(f):
    """
    Decorate routes to require login.

    https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function
