import os
import datetime

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date

from helpers import apology, login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///project.db")



@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    #TODO
    if request.method == "GET":
        user_todos = db.execute("SELECT id, task FROM u_todo WHERE user_id = :current_id", current_id = session["user_id"])
        family_todos = db.execute("SELECT id, task FROM f_todo WHERE family_id in (SELECT family_id FROM members WHERE user_id = :current_id)", current_id = session["user_id"])
        user_todo_list = []
        family_todo_list = []
        for task in user_todos:
            temp = list(task.values())
            user_todo_list.append(temp)
        for task in family_todos:
            temp = list(task.values())
            family_todo_list.append(temp)
        return render_template("index.html", todos = user_todo_list, f_todos = family_todo_list)


@app.route("/add", methods=["GET","POST"])
@login_required
def add():
    familyID = db.execute("SELECT family_id FROM members WHERE user_id = :current_id", current_id = session["user_id"])
    if request.method=="GET":
        return render_template("add.html", familyID = familyID)
    else:
        if not request.form.get("todo"):
            return redirect("/add")
        if request.form.get("submit_u"):
            todo = (request.form.get("todo")).capitalize()
            db.execute("INSERT INTO u_todo (user_id, task) VALUES(?,?)", session["user_id"], todo)
        elif request.form.get("submit_f"):
            todo = (request.form.get("todo")).capitalize()
            familyID = familyID[0]["family_id"]
            db.execute("INSERT INTO f_todo (task,family_id) VALUES(?,?)", todo, familyID)
        return redirect("/add")


@app.route("/delete/<int:todo_id>")
@login_required
def delete(todo_id):
    today = date.today()
    d1 = today.strftime("%d/%m/%Y")
    todo = db.execute("SELECT task FROM u_todo WHERE id = :todoID", todoID = todo_id)
    todo = todo[0]["task"]
    db.execute("INSERT INTO history VALUES (?,?,?,?)", session["user_id"], "Private", todo, d1)
    db.execute("DELETE FROM u_todo WHERE id = :todo_id", todo_id = todo_id)
    return redirect("/")


@app.route("/deletef/<int:todo_id>")
@login_required
def deletef(todo_id):
    today = date.today()
    d1 = today.strftime("%d/%m/%Y")
    todo = db.execute("SELECT task FROM f_todo WHERE id = :todoID", todoID = todo_id)
    todo = todo[0]["task"]
    db.execute("INSERT INTO history VALUES (?,?,?,?)", session["user_id"], "Family", todo, d1)
    db.execute("DELETE FROM f_todo WHERE id = :todo_id", todo_id = todo_id)
    return redirect("/")

@app.route("/history")
@login_required
def history():
    tasks = db.execute("SELECT type,task,time FROM history WHERE user_id = :current_id", current_id = session["user_id"])
    return render_template("history.html", tasks = tasks)

@app.route("/clear")
@login_required
def clear():
    db.execute("DELETE FROM history WHERE user_id = :current_id", current_id = session["user_id"])
    return redirect("/history")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        rows = db.execute("SELECT username from users WHERE username=?", username)
        user_with_same_name = len(rows)
        if not username:
            return apology("You must provide an username!")
        elif not password:
            return apology("You must provide a password!")
        elif not confirmation:
            return apology("You must confirm your password!")
        elif password != confirmation:
            return apology("The password and the confirmation doesn't match!")
        elif user_with_same_name >= 1:
            return apology("Username already in use!")
        else:
            password = generate_password_hash(password)
            db.execute("INSERT INTO users (username, hash) VALUES(?,?)", username, password)
            return redirect("/")



@app.route("/family", methods = ["GET", "POST"])
@login_required
def family():
    if request.method == "GET":
        rows = db.execute("SELECT family_id FROM members WHERE user_id = :current_id", current_id = session["user_id"])
        if not rows:
            return render_template("no_family.html")
        else:
            familyID = rows[0]["family_id"]
            members = db.execute("SELECT username FROM users JOIN members ON id = user_id WHERE family_id = :familyID", familyID = familyID)
            members_list = []
            for person in members:
                temp = list(person.values())
                members_list.append(temp[0])
            return render_template("yes_family.html", members_list = members_list)
    else:
        rows = db.execute("SELECT family_id FROM members WHERE user_id = :current_id", current_id = session["user_id"])
        familyID = rows[0]["family_id"]
        db.execute("DELETE FROM members WHERE user_id = :current_id", current_id = session["user_id"])
        members = db.execute("SELECT user_id FROM members WHERE family_id = :familyID", familyID = familyID)
        if not members:
            db.execute("DELETE FROM family WHERE id = :familyID", familyID = familyID)
        return redirect("/family")


@app.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "GET":
        return render_template("create.html")
    else:
        family_name = request.form.get("family_name")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        rows = db.execute("SELECT family_name FROM family WHERE family_name = :name", name = family_name)
        same_name = len(rows)
        if not family_name:
            return apology("Missing family name")
        elif not password:
            return apology("You must provide a password!")
        elif not confirmation:
            return apology("You must confirm your password!")
        elif password != confirmation:
            return apology("The password and the confirmation doesn't match!")
        elif same_name >= 1:
            return apology("Family Name already in use!")
        else:
            password = generate_password_hash(password)
            db.execute("INSERT INTO family (family_name, hash) VALUES (?,?)", family_name, password)
            familyID = db.execute("SELECT id FROM family WHERE family_name = :name", name = family_name)
            familyID = familyID[0]["id"]
            db.execute("INSERT INTO members (family_id, user_id) VALUES (?,?)", familyID, session["user_id"])
            return redirect("/family")


@app.route("/enter", methods=["GET","POST"])
@login_required
def enter():
    if request.method == "GET":
        return render_template("enter.html")
    else:
        if not request.form.get("family_name"):
            return apology("must provide family_name")

        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM family WHERE family_name = :name",
                          name=request.form.get("family_name"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password")

        else:
            db.execute("INSERT INTO members VALUES(?,?)", rows[0]["id"], session["user_id"])

        # Redirect user to home page
        return redirect("/family")

@app.route("/password", methods=["GET", "POST"])
def password():

    if request.method == "GET":
        return render_template("password.html")
    else:
         # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        username = request.form.get("username")
        new_password = request.form.get("password")
        new_confirmation = request.form.get("confirmation")

        if new_password != new_confirmation:
            return apology("Password and confirmation must be equal!")

        password = generate_password_hash(new_password)
        db.execute("UPDATE users SET password = :password WHERE username = :current_username", password = password, current_username = username)

        return redirect("/login")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)