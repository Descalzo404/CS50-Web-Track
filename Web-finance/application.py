import os
import datetime

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

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
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    users_cash = db.execute("SELECT cash FROM users WHERE id = :current_id", current_id = session["user_id"])
    users_cash = float(users_cash[0]["cash"])

    users_stocks = db.execute("SELECT symbol FROM wallet WHERE id = :current_id", current_id = session["user_id"])
    stocks_list = []
    for stock in users_stocks:
        temp = list(stock.values())
        stocks_list.append(temp[0])

    users_shares = db.execute("SELECT shares FROM wallet WHERE id = :current_id", current_id = session["user_id"])
    shares_list = []
    for share in users_shares:
        temp = list(share.values())
        shares_list.append(temp[0])


    company_names = []
    stock_prices = []
    total_value = []
    i = 0
    for stock in stocks_list:
        result = lookup(stock)
        company_names.append(result["name"])
        stock_prices.append(result["price"])
        total_value.append(float(shares_list[i] * result["price"]))
        i += 1
    users_value = (users_cash + sum(total_value))
    #return render_template("test.html", stocks_list = stocks_list, shares_list = shares_list)
    return render_template("index.html", users_value=users_value, stocks_list=stocks_list, shares_list=shares_list, company_names=company_names, stock_prices=stock_prices, total_value=total_value, i=i)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("buy.html")
    else:
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))
        stocks = lookup(symbol)
        users_cash = db.execute("SELECT cash FROM users WHERE id = :current_id", current_id = session["user_id"])
        users_cash = float(users_cash[0]["cash"])
        current_time = datetime.datetime.now()
        if not symbol:
            return apology("You must provide a symbol!")
        if not stocks:
            return apology("Nothing found with this symbol!")

        value_of_purchase = float(shares * (stocks["price"]))
        symbol = symbol.upper()

        if users_cash < value_of_purchase:
            return apology("Not enough cash!")
        else:
            "put this trade in transactions"
            db.execute("INSERT INTO transactions (id, symbol, shares, value, time) VALUES (?,?,?,?,?)", session["user_id"], symbol, shares, stocks["price"], current_time)
            "update the users cash"
            db.execute("UPDATE users SET cash = :cash WHERE id = :current_id", cash = (users_cash - value_of_purchase), current_id = session["user_id"])
            user_stock = db.execute("SELECT symbol FROM wallet WHERE id = :current_id AND symbol = :symbol", current_id = session["user_id"], symbol = symbol)
            if not user_stock:
                db.execute("INSERT INTO wallet (id, symbol, shares) VALUES(?,?,?)", session["user_id"], symbol, shares)
                return redirect("/")
            else:
                current_shares = db.execute("SELECT shares FROM wallet WHERE id = :current_id AND symbol = :symbol", current_id = session["user_id"], symbol = symbol)
                current_shares = current_shares[0]["shares"]
                total_shares = current_shares + shares
                db.execute("UPDATE wallet SET shares = :shares WHERE id = :current_id AND symbol = :symbol", shares = total_shares, current_id = session["user_id"], symbol = symbol)
                return redirect("/")



@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    users_history = db.execute("SELECT * FROM transactions WHERE id = :current_id", current_id = session["user_id"])
    transactions_list = []
    number_of_transactions = 0
    for transactions in users_history:
        temp = list(transactions.values())
        transactions_list.append(temp)
        number_of_transactions += 1
    return render_template("history.html", transactions_list=transactions_list, number_of_transactions=number_of_transactions)



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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("quote.html")
    else:
        symbol = request.form.get("symbol")
        stocks = lookup(symbol)
        if stocks == None:
            return apology("Invalid symbol!")
        else:
            return render_template("quoted.html", stocks=stocks)




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




@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":
        return render_template("sell.html")
    else:
        symbol = request.form.get("symbol")
        shares = int(request.form.get("shares"))
        symbol = symbol.upper()
        if not symbol:
            return apology("Must provide a symbol!")
        if not shares:
            return apology("Must provide a number of shares")
        current_symbol = db.execute("SELECT symbol FROM wallet WHERE id = :current_id AND symbol = :symbol", current_id = session["user_id"], symbol = symbol)
        if not current_symbol:
            return apology("No matching symbol found in your portfolio!")
        current_shares = db.execute("SELECT shares FROM wallet WHERE id = :current_id AND symbol = :symbol", current_id = session["user_id"], symbol = symbol)
        current_shares = int(current_shares[0]["shares"])
        if shares > current_shares:
            return apology("You don't have that many shares!")

        users_cash = db.execute("SELECT cash FROM users WHERE id = :current_id", current_id = session["user_id"])
        users_cash = float(users_cash[0]["cash"])
        stock = lookup(symbol)
        total_value = float(shares*stock["price"])
        current_time = datetime.datetime.now()
        db.execute("INSERT INTO transactions (id, symbol, shares, value, time) VALUES (?,?,?,?, ?)", session["user_id"], symbol, (-shares), stock["price"], current_time)
        db.execute("UPDATE users SET cash = :cash WHERE id = :current_id", cash = (users_cash + total_value), current_id = session["user_id"])
        if shares == current_shares:
            db.execute("DELETE FROM wallet WHERE id = :current_id AND symbol = :symbol", current_id = session["user_id"], symbol = symbol)
            return redirect("/")
        else:
            db.execute("UPDATE wallet SET shares = :shares WHERE id = :current_id AND symbol = :symbol", shares = (current_shares - shares), current_id = session["user_id"], symbol = symbol)
            return redirect("/")


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
