import sqlite3 ,os
from flask import Flask, flash, redirect, render_template, request, session, abort , g , url_for , jsonify
from passlib.hash import sha256_crypt as sha


app = Flask(__name__, static_url_path="", static_folder="static") #sets static folder which tells the url_for() in the html files where to look

Database = 'ccslog.db'

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
def home():
    return "Hello World"

@app.route('/login',methods=['POST','GET'])
def login():
    if request.method == "GET":
        return render_template("login.html")
    else:
        username=request.form["username"]
        password=request.form["password"]
        phash = query_db("select password from users where username = ?", (username, ))
        if phash==[]:
            return "Username doesnt exist"

        if sha.verify(password, phash[0][0]):
            return "Suc"
        else:
            return "Fil"


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    submission = {}
    submission["username"] = request.form["username"]
    submission["name"] = request.form["name"]
    submission["email"] = request.form["email"]
    submission["phone"] = request.form["ph"]
    submission["pass"] = request.form["password"]
    submission["conf_pass"] = request.form["conf_pass"]


    if submission["pass"]!=submission["conf_pass"]:
        return "Wrong password"

    if query_db("select username from users where username = ?", (submission["username"],))!=[]:
        return "Username already taken" 

    password = sha.encrypt(submission["pass"])
    execute_db("insert into users values(?,?,?,?,?,0)", (
        submission["username"],
        submission["name"],
        submission["email"],
        password,
        submission["phone"],
    ))

    return redirect(url_for("login"))

if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    app.run(host = "0.0.0.0",debug=True, port=8080)
