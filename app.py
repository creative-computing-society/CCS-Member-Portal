#!/usr/bin/env python3
import sqlite3 ,os
from flask import Flask, flash, redirect, render_template, request, session, abort , g , url_for , jsonify
from passlib.hash import sha256_crypt as sha
from functools import wraps
from datetime import datetime


app = Flask(__name__, static_url_path="", static_folder="static") #sets static folder which tells the url_for() in the html files where to look

Database = 'ccslog.db'

if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("username") is None:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(Database)
    return db

def query_db(query, args=(), one=False): #used to retrive values from the table
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query , args=()): #executes a sql command like alter table and insert
    conn = get_db()
    cur = conn.cursor()
    cur.execute(query , args)
    conn.commit()
    cur.close()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
@login_required
def home():
    redirect(url_for("profile",username=session['username']))


@app.route('/login',methods=['POST','GET'])
def login():
    if request.method == "GET":
        return render_template("login.html")
    else:
        error = None
        username=request.form["username"]
        password=request.form["password"]
        phash = query_db("select password from users where username = ?", (username, ))
        if phash==[]:
            flash("User does not exist","danger")
            return render_template("login.html")

        if sha.verify(password, phash[0][0]):
            session["username"] = username
            return redirect(url_for('profile'))
        else:
            flash("Incorrect Password","danger")
            return render_template("login.html")


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == "GET":
        return render_template("signup.html")
    else:
        submission = {}
        submission["username"] = request.form["username"]
        submission["name"] = request.form["name"]
        submission["email"] = request.form["email"]
        submission["phone"] = request.form["ph"]
        submission["pass"] = request.form["password"]
        submission["conf_pass"] = request.form["conf_pass"]


        if submission["pass"]!=submission["conf_pass"]:
            flash("Passwords don't match","danger")
            return render_template("signup.html")

        if query_db("select username from users where username = ?", (submission["username"],))!=[]:
            flash("User already taken","danger")
            return render_template("signup.html")

        password = sha.encrypt(submission["pass"])
        execute_db("insert into users values(?,?,?,?,?,0)", (
            submission["username"],
            submission["name"],
            submission["email"],
            password,
            submission["phone"],
        ))
        flash("User Created","success")
        return redirect(url_for("login"))

@app.route('/members')
@login_required
def profile():
    row=query_db('select * from users')
    return render_template('member.html', un=session["username"], row=row)

@app.route('/events')
@login_required
def events():
    events=query_db('select * from events')
    upcoming=[]
    logs=[]
    current_time = datetime.now()
    for x in events:
        temp_time = datetime.strptime(x[3],'%Y/%m/%d %H:%M')
        temp_list = list(x)
        temp_list[3] = (temp_time.strftime('%d, %b %Y at %H:%M'))
        if(current_time>temp_time):
            logs.append(temp_list)
        else:
            upcoming.append(temp_list)
    return render_template('events.html', un=session["username"], upcoming=upcoming, logs=logs)

@app.route('/projects')
@login_required
def projects():
    row=query_db('select * from projects')
    return render_template('projects.html', un=session["username"], row=row)

@app.route('/addproject', methods=['GET', 'POST'])
@login_required
def addproject():
    if request.method == "GET":
        return render_template("addproject.html")
    else:
        submission = {}
        submission["title"] = request.form["title"]
        submission["content"] = request.form["content"]
        submission["images"] = request.form["images"]

        if query_db("select title from projects where title = ?", (submission["title"],))!=[]:
            error = "Project Title already exists! Please change the title." 
        else:
            execute_db("insert into projects (title, content, images, canapp) values(?,?,?,0)", (
                submission["title"],
                submission["content"],
                submission["images"],
            ))
        return redirect(url_for("projects"))


@app.route('/addevents', methods=['GET', 'POST'])
@login_required
def addevents():
    if request.method == "GET":
        return render_template("addevent.html")
    else:
        submission = {}
        submission["title"] = request.form["title"]
        submission["content"] = request.form["content"]
        submission["date"] = request.form["date"] + " " +request.form["time"]
        submission["images"] = request.form["images"]


        if query_db("select title from events where title = ?", (submission["title"],))!=[]:
            error = "Events Title already exists! Please change the title." 
        else:
            execute_db("insert into events (title, content, date , images) values(?,?,?,?)", (
                submission["title"],
                submission["content"],
                submission["date"],
                submission["images"],
            ))
        return redirect(url_for("events"))

@app.route("/logout")
def logout():
    session.clear()
    flash("Logout success","success")
    return redirect(url_for("login"))

@app.route("/change", methods=["GET", "POST"])
@login_required
def change():
    if request.method == "GET":
        render_template("change.html")
    else:
        password = request.form["old_password"]
        old_password = query_db("select password from users where username = ?", (session["username"],))
        if sha.verify(password, old_password[0][0]):
            submission = {}
            submission["pass"] = request.form["password"]
            submission["conf_pass"] = request.form["conf_pass"]
            
            if submission["pass"]!=submission["conf_pass"]:
                flash("Password doesnt match","danger")
                return redirect(url_for("change"))
            
            password = sha.encrypt(submission["pass"])
            
            execute_db("update users set password = ? where username = ?", (
            password,
            session["username"],))
            return redirect(url_for("login"))
        else:
            flash("Wrong Password","danger")
            return redirect(url_for("change"))

if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    app.run(host = "0.0.0.0",debug=True, port=8080)
