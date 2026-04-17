import os

from cs50 import SQL
from datetime import datetime, timedelta
from flask import Flask, redirect, render_template, request, session
from flask_font_awesome import FontAwesome
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, get_invite_names, get_strtime, get_time, get_time_and_str, get_todo_names, login_required

# Configure the app
app = Flask(__name__)
font_awesome = FontAwesome(app)

# Configure session to use filesystem (instead of cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///todo.db")

@app.after_request
def after_request(response):
    """Ensure response aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/add", methods=["GET", "POST"])
@login_required
def add_todo():
    """Add a todo"""
    if request.method == "POST":
        # Get the form data
        title = request.form.get("title").strip()
        description = request.form.get("description").strip()
        date = request.form.get("date")
        hour = request.form.get("hour")

        # Verify that data is valid. Blank description is okay.
        if not title:
            return apology("missing title", 403)
        if not date:
            return apology("missing ToDo date", 403)
        if not hour:
            return apology("missing ToDo time", 403)
        try:
            date_hour = date + " T " + hour
            todo_time = get_time(date_hour)
        except:
            return apology("invalid ToDo date or time", 400)
        if todo_time < datetime.now() - timedelta(days=61):
            return apology("Tod date is too old", 400)

        # Record the todo event in the database
        db.execute(
            "INSERT INTO events (user_id, title, description, start, complete) VALUES(?, ?, ?, ?, ?)",
            session["user_id"], title, description, todo_time, False
        )
        return redirect("/")
    else:
        # Create list of hours for the form time select list
        hours = [
            "0:00 am", "0:30 am", "1:00 am", "1:30 am", "2:00 am", "2:30 am", "3:00 am", "3:30 am",
            "4:00 am", "4:30 am", "5:00 am", "5:30 am", "6:00 am", "6:30 am", "7:00 am", "7:30 am",
            "8:00 am", "8:30 am", "9:00 am", "9:30 am", "10:00 am", "10:30 am", "11:00 am", "11:30 am",
            "12:00 pm", "12:30 pm", "1:00 pm", "1:30 pm", "2:00 pm", "2:30 pm", "3:00 pm", "3:30 pm",
            "4:00 pm", "4:30 pm", "5:00 pm", "5:30 pm", "6:00 pm", "6:30 pm", "7:00 pm", "7:30 pm",
            "8:00 pm", "8:30 pm", "9:00 pm", "9:30 pm", "10:00 pm", "10:30 pm", "11:00 pm", "11:30 pm"
        ]

        # Get the next hour to select in the options list
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        hour, minutes = int(current_time[0:2]), int(current_time[3:])
        minutes = 30 if minutes <= 30 else 0
        am_pm = "pm" if hour > 12 else "am"
        hour = (hour + 1) % 12 if minutes == 0 else hour % 12
        current_hour = f"{hour}:{minutes:02d} {am_pm}"

        return render_template("add.html", hours=hours, current_hour=current_hour)


@app.route("/del/<id>", methods=["GET", "POST"])
@login_required
def delete_todo(id):
    """Delete a todo event"""
    if request.method == "POST":
        event = db.execute("SELECT * FROM events WHERE id = ?", id)[0]
        if event["user_id"] == session["user_id"]:
            db.execute("DELETE FROM events WHERE id = ?", id)
            return redirect("/")
        else:
            return redirect("/")
    else:
        # Get ToDo details
        event = db.execute("SELECT * FROM events WHERE id = ?", id)[0]
        user = db.execute("SELECT * FROM users WHERE id = ?", session["user_id"])[0]
        if event["user_id"] != user["id"]:
            return redirect("/")
        event["time"] = get_strtime(event["start"])

        # Make list of names of friends invited ToDo activity if any
        event["friend_names"] = get_todo_names(db, event["id"])

        return render_template("del.html", event=event)


@app.route("/friend/<id>", methods=["GET", "POST"])
@login_required
def friend(id):
    """Add friend to do ToDo together"""
    if request.method == "POST":
        # Get form data
        username = request.form.get("username").strip()

        # Verify that data is valid
        if not username:
            return apology("missing friend's name", 403)
        friend_id = ""
        try:
            friend_id = db.execute("SELECT id FROM users WHERE username = ?", username)[0]
        except:
            pass
        if not friend_id:
            try:
                friend_id = db.execute("SELECT id FROM users WHERE username = ?", username.title())[0]
            except:
                pass
        if not friend_id:
            return apology("friend's name not found", 400)
        if int(friend_id["id"]) == session["user_id"]:
            return apology("no need to add yourself", 403)

        # Add the friend to the todo event in the database
        db.execute("INSERT INTO friends (event_id, friend_id) VALUES(?, ?)", id, int(friend_id["id"]))

        return redirect("/")
    else:
        # Get ToDo details
        event = db.execute("SELECT * FROM events WHERE id = ?", id)[0]
        event["time"] = get_strtime(event["start"])

        # Make list of names of friends invited ToDo activity if any
        event["friend_names"] = get_todo_names(db, event["id"])

        return render_template("friend.html", event=event)


@app.route("/history")
@login_required
def history():
    """View todos marked as done"""
    # Get user and todo event data for user's ToDo history
    user_id = session["user_id"]
    user = db.execute("SELECT * FROM users WHERE id = ?", user_id)
    events = db.execute("SELECT * FROM events WHERE user_id = ? AND complete = ?", user_id, True)
    invite_dict_list = db.execute("SELECT event_id FROM friends WHERE friend_id = ?", user_id)
    invite_ids = [item["event_id"] for item in invite_dict_list]

    if invite_ids:
        invites = db.execute("SELECT * FROM events WHERE id IN (?) AND complete = ?", invite_ids, True)
    else:
        invites = []

    # Transform into list of dicts adding info for each todo event
    now = datetime.now()
    count, too_old = 0, now - timedelta(days=61)
    for event in events:
        # Set a readable datetime string, get event datetime and delete old events
        event_time, event["time"] = get_time_and_str(event["start"])
        if event_time < too_old:
            db.execute("DELETE * FROM events WHERE id = ?", event["id"])
            events.pop(count)
            count += 1
            continue
        count += 1

        # Make an easy to read list of friends if the event has any
        event["friend_names"] = get_todo_names(db, event["id"])

    # Add invite events to the list if any exit
    if invites:
        count = 0
        for event in invites:
            # Set a readable datetime string, get event datetime and delete old events
            event_time, event["time"] = get_time_and_str(event["start"])
            if event_time < too_old:
                db.execute("DELETE * FROM events WHERE id = ?", event["id"])
                events.pop(count)
                count += 1
                continue

            # Skip unfinished events and those already listed
            if not event["complete"]:
                continue
            if event["id"] in [event["id"] for event in events]:
                continue

            # Mark as invite from friend. Make an easy to read list of friends and add event to list.
            event["relevance"] = "friended"
            event["friend_names"], event["owner"] = get_invite_names(db, event["user_id"], event["id"], user_id)
            events.append(event)

    # Sort the events by datetime, most recent first
    events.sort(key = lambda todo:todo["start"])
    events.reverse()

    return render_template("history.html", user=user[0], events=events)


@app.route("/")
@login_required
def index():
    """View todo list"""
    # Get user todo and invite events data for user ToDo list
    user_id = session["user_id"]
    user = db.execute("SELECT * FROM users WHERE id = ?", user_id)
    events = db.execute(
        "SELECT * FROM events WHERE user_id = ? AND complete = ?",
        user_id, False
    )
    invite_dict_list = db.execute(
        "SELECT event_id FROM friends WHERE friend_id = ?", user_id
    )
    invite_ids = [item["event_id"] for item in invite_dict_list]
    if invite_ids:
        invites = db.execute(
            "SELECT * FROM events WHERE id IN (?) AND complete = ?",
            invite_ids, False
        )
    else:
        invites = []

    # Transform into list of dicts adding info for each todo event
    now, count = datetime.now(), 0
    within_24h, too_old = now + timedelta(days=1), now - timedelta(days=61)
    for event in events:

        # Set a readable datetime string, get event datetime and delete old events
        event_time, event["time"] = get_time_and_str(event["start"])

        if event_time < too_old:
            db.execute("DELETE * FROM events WHERE id = ?", event["id"])
            events.pop(count)
            count += 1
            continue
        count += 1

        # Add date relevance for past, overdue or upcoming events
        if event_time < now:
            event["relevance"] = "overdue"
        elif now <= event_time < within_24h:
            event["relevance"] = "upcoming"
        else:
            event["relevance"] = "future"

        # Make an easy to read list of friends if the event has any
        event["friend_names"] = get_todo_names(db, event["id"])

    # Add friend events to the list if any exit
    if invites:
        count = 0
        for event in invites:
            # Set a readable datetime string, get event datetime and delete old events
            event_time, event["time"] = get_time_and_str(event["start"])

            # Add onwership, friend info, date relevance for past, overdue or upcoming events
            if event_time < too_old:
                db.execute("DELETE * FROM events WHERE id = ?", event["id"])
                events.pop(count)
                count += 1
                continue
            
            # Skip finished events and those already listed
            if event["complete"]:
                continue
            if event["id"] in [event["id"] for event in events]:
                continue

            # Mark as invite from friend. Make an easy to read list of friends and add event to list.
            event["relevance"] = "friended"
            event["friend_names"], event["owner"] = get_invite_names(db, event["user_id"], event["id"], user_id)
            events.append(event)

    # Sort the events by datetime
    events.sort(key = lambda evnt:evnt["start"])

    return render_template("index.html", user=user[0], events=events)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User submit login form
    if request.method == "POST":
        # Ensure username submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query DB for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username / password", 403)

        # Remember user until logged out
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached the site, not logged in
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget user's user_id
    session.clear()

    # Redirect user to login form
    return redirect("/login")


@app.route("/done/<id>", methods=["GET", "POST"])
@login_required
def mark_done(id):
    """Mark a todo as done"""
    if request.method == "POST":
        db.execute(
            "UPDATE events SET complete = ? WHERE id = ?",
            True, id
        )
        return redirect("/")
    else:
        # Get ToDo details
        event = db.execute("SELECT * FROM events WHERE id = ?", id)[0]
        event["time"] = get_strtime(event["start"])

        # Make list of names of friends invited ToDo activity if any
        event["friend_names"] = get_todo_names(db, event["id"])

        return render_template("done.html", event=event)


@app.route("/undo/<id>", methods=["GET", "POST"])
@login_required
def mark_undone(id):
    """Mark a todo as done"""
    if request.method == "POST":
        db.execute(
            "UPDATE events SET complete = ? WHERE id = ?",
            False, id
        )
        return redirect("/history")
    else:
        # Get ToDo details
        event = db.execute("SELECT * FROM events WHERE id = ?", id)[0]
        event["time"] = get_strtime(event["start"])

        # Make list of names of friends invited ToDo activity if any
        event["friend_names"] = get_todo_names(db, event["id"])

        return render_template("undo.html", event=event)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register new user"""

    # Forget any user_id
    session.clear()

    # Get form data when user submits registration
    if request.method == "POST":
        username = request.form.get("username")
        name = request.form.get("name")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Ensure username was submitted
        if username.strip() == "":
            return apology("must provide username", 400)

        # Confirm that the username is unique
        elif db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        ):
            return apology("name already taken", 400)

        # Confirm that a name was provided
        elif len(name.strip()) <= 0:
            return apology("must provide a name", 400)

        # Ensure password was submitted
        elif password.strip() == "":
            return apology("must provide password", 400)

        # Ensure password was confirmed
        elif confirmation.strip() == "":
            return apology("must confirm password", 400)

        # Ensure passwords match
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords must match", 400)

        # Hash the user password
        pwHash = generate_password_hash(request.form.get("password"))

        # Create the new user
        db.execute(
            "INSERT INTO users (username, hash, name) VALUES (?, ?, ?)",
            username, pwHash, name
        )

        # Redirect user to login form
        return redirect("/")

    # User lands on registration form page
    else:
        return render_template("register.html")
