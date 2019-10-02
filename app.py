#!E:/GitHub/ccs-log/env/Scripts/python
import sqlite3 ,os
from flask import Flask, flash, redirect, render_template, request, session, abort , g , url_for , jsonify
from passlib.hash import sha256_crypt as sha
from hashlib import md5
from functools import wraps
from datetime import datetime
from flask import send_from_directory
from flask_mail import Mail , Message
import uuid

app = Flask(__name__, static_url_path="", static_folder="static")
mail=Mail(app)

UPLOADS_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'static/uploads')
app.config['UPLOAD_FOLDER'] = UPLOADS_PATH
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 #Limits filesize to 16MB
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'ccslog.apply@gmail.com'
app.config['MAIL_PASSWORD'] = 'ccsthapar'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail=Mail(app)

app.secret_key = os.urandom(12)

Database = 'ccslog.db'
#for hacktoberfest
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
        digest = md5(submission['username'].encode('utf-8')).hexdigest()
        submission["image"] = 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(digest, 256) #here 256 is size in sq pixels


        if submission["pass"]!=submission["conf_pass"]:
            flash("Passwords don't match","danger")
            return render_template("signup.html")

        if query_db("select username from users where username = ?", (submission["username"],))!=[]:
            flash("User already taken","danger")
            return render_template("signup.html")

        password = sha.encrypt(submission["pass"])
        execute_db("insert into users values(?,?,?,?,?,0,?)", (
            submission["username"],
            submission["name"],
            submission["email"],
            password,
            submission["phone"],
            submission["image"],
        ))
        flash("User Created","success")
        return redirect(url_for("login"))
     
@app.route('/members')
@login_required
def profile():
    pcount=query_db("select count(id) from projects where accept=? ",(0,))
    ecount=query_db("select count(id) from events where accept=? ",(0,))
    a=query_db("select admin from users where username =?",(session["username"],))
    admin=a[0][0]
    row=query_db('select * from users')
    return render_template('member.html', un=session["username"], row=row,pcount=pcount,ecount=ecount,admin=admin)

@app.route('/events')
@login_required
def events():
    pcount=query_db("select count(id) from projects where accept=? ",(0,))
    ecount=query_db("select count(id) from events where accept=? ",(0,))
    a=query_db("select admin from users where username =?",(session["username"],))
    admin=a[0][0]
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
    return render_template('events.html', un=session["username"], upcoming=upcoming, logs=logs ,admin=admin,pcount=pcount,ecount=ecount)


@app.route('/projects')
@login_required
def projects():
    pcount=query_db("select count(id) from projects where accept=? ",(0,))
    ecount=query_db("select count(id) from events where accept=? ",(0,))
    row=query_db('select * from projects')
    a=query_db("select admin from users where username =?",(session["username"],))
    admin=a[0][0]
    return render_template('projects.html', un=session["username"], row=row,admin=admin,pcount=pcount,ecount=ecount)

@app.route('/addproject', methods=['GET', 'POST'])
@login_required
def addproject():
    pcount=query_db("select count(id) from projects where accept=? ",(0,))
    ecount=query_db("select count(id) from events where accept=? ",(0,))
    a=query_db("select admin from users where username =?",(session["username"],))
    admin=a[0][0]
    if request.method == "GET":
        return render_template("addproject.html",pcount=pcount,ecount=ecount)
    else:
        submission = {}
        submission["title"] = request.form["title"]
        submission["content"] = request.form["content"]
        file = request.files.get('image')
        if file is None:
            digest = md5(submission['title'].encode('utf-8')).hexdigest()
            submission["images"] = 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(digest, 128) #here 128 is size in sq pixels
        else:
            extension = os.path.splitext(file.filename)[1]
            token = uuid.uuid4().hex+extension 
            f = os.path.join(app.config['UPLOAD_FOLDER'],token)
            file.save(f)
            submission["images"] = url_for('uploaded_file',filename=token)
        if query_db("select title from projects where title = ?", (submission["title"],))!=[]:
            flash("Project Title already exists! Please change the title.")
            return redirect(url_for("addproject"))
        else:
            if admin==0:
                accept=0
            else:
                accept=1 
            execute_db("insert into projects (title, content, images, canapp,accept) values(?,?,?,0,?)", (
                submission["title"],
                submission["content"],
                submission["images"],
                accept,
            ))
        return redirect(url_for("projects"))


@app.route('/addevents', methods=['GET', 'POST'])
@login_required
def addevents():
    pcount=query_db("select count(id) from projects where accept=? ",(0,))
    ecount=query_db("select count(id) from events where accept=? ",(0,))
    a=query_db("select admin from users where username =?",(session["username"],))
    admin=a[0][0]
    if request.method == "GET":
        return render_template("addevent.html",pcount=pcount,ecount=ecount,admin=admin)
    else:
        submission = {}
        submission["title"] = request.form["title"]
        submission["content"] = request.form["content"]
        submission["date"] = request.form["date"] + " " +request.form["time"]
        file = request.files.get('image')
        if not(file):
            digest = md5(submission['title'].encode('utf-8')).hexdigest()
            submission["images"] = 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(digest, 256) #here 256 is size in sq pixels
        else:
            extension = os.path.splitext(file.filename)[1]
            token = uuid.uuid4().hex+extension
            f = os.path.join(app.config['UPLOAD_FOLDER'],token)
            file.save(f)
            submission["images"] = url_for('uploaded_file',filename=token)
        if query_db("select title from events where title = ?", (submission["title"],))!=[]:
            flash("Events Title already exists! Please change the title.") 
            return redirect(url_for("addevents"))
        else:
            if admin==0:
                accept=0
            else:
                accept=1
            execute_db("insert into events (title, content, date , images) values(?,?,?,?,?)", (
                submission["title"],
                submission["content"],
                submission["date"],
                submission["images"],
                accept,
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
        password = request.form["old_password"]
        old_password = query_db("select password from users where username = ?", (session["username"],))
        if sha.verify(password, old_password[0][0]):
            submission = {}
            submission["pass"] = request.form["password"]
            submission["conf_pass"] = request.form["conf_pass"]
            
            if submission["pass"]!=submission["conf_pass"]:
                flash("Password doesnt match","danger")
                return redirect(url_for("edit_profile"))
            
            password = sha.encrypt(submission["pass"])
            
            execute_db("update users set password = ? where username = ?", (
            password,
            session["username"],))
            return redirect(url_for("login"))
        else:
            flash("Wrong Password","danger")
            return redirect(url_for("edit_profile"))


@app.route('/delete_event/<event_id>')
@login_required
def delete_event(event_id):
    execute_db('delete from events where id=?',(event_id,))
    return redirect(url_for("events"))


@app.route('/edit_event/<event_id>' , methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    pcount=query_db("select count(id) from projects where accept=? ",(0,))
    ecount=query_db("select count(id) from events where accept=? ",(0,))
    a=query_db("select admin from users where username =?",(session["username"],))
    admin=a[0][0]
    if request.method == "GET":
        event=query_db("select * from events where id=?",(event_id,))
        return render_template("edit_event1.html",id=event_id ,event=event,pcount=pcount,ecount=ecount,admin=admin)

    else:

        submission={}
        submission["title"]=request.form["title"]
        submission["date"] = request.form["date"] + " " +request.form["time"]
        submission["content"]=request.form["content"]
        file = request.files.get('image')
        if not(file):
            digest = md5(submission["title"].encode('utf-8')).hexdigest()
            submission["images"] = 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(digest, 128) #here 128 is size in sq pixels
        else:
            extension = os.path.splitext(file.filename)[1]
            token = uuid.uuid4().hex+extension
            f = os.path.join(app.config['UPLOAD_FOLDER'],token)
            file.save(f)
            submission["images"] = url_for('uploaded_file',filename=token)

        
        if query_db("select title from events where title = ? and id!=?", (submission["title"],event_id,))!=[] :
            flash("Events Title already exists! Please change the title.") 
            return redirect(url_for('edit_event',event_id=event_id))
        else:
            execute_db("update events set title=? , content=? , date=? , images=? where id=?",(submission["title"],submission["content"],submission["date"],submission["images"],event_id,))
            return redirect(url_for("events"))
 

@app.route('/delete_project/<project_id>')
@login_required
def delete_project(project_id):
    execute_db('delete from projects where id=?',(project_id,))
    return redirect(url_for("projects"))           

@app.route('/edit_project/<project_id>' , methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    pcount=query_db("select count(id) from projects where accept=? ",(0,))
    ecount=query_db("select count(id) from events where accept=? ",(0,))
    a=query_db("select admin from users where username =?",(session["username"],))
    admin=a[0][0]
    if request.method == "GET":
        project=query_db("select * from projects where id=?",(project_id,))
        return render_template("edit_project1.html",id=project_id ,project=project,pcount=pcount,ecount=ecount,admin=admin)

    else:

        submission={}
        submission["title"]=request.form["title"]
        submission["content"]=request.form["content"]
        file = request.files.get('image')
        if not(file):
            digest = md5(submission["title"].encode('utf-8')).hexdigest()
            submission["images"] = 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(digest, 128) #here 128 is size in sq pixels
        else:
            extension = os.path.splitext(file.filename)[1]
            token = uuid.uuid4().hex+extension
            f = os.path.join(app.config['UPLOAD_FOLDER'],token)
            file.save(f)
            submission["images"] = url_for('uploaded_file',filename=token)
        
        
        if  query_db("select title from projects where title = ? and id!=?", (submission["title"],project_id,))!=[]:
            flash("Project Title already exists! Please change the title.") 
            return redirect(url_for('edit_project',project_id=project_id)) 
        else:
            execute_db("update projects set title=? , content=?  , images=? where id=?",(submission["title"],submission["content"],submission["images"],project_id,))
            return redirect(url_for("projects"))
  
@app.route('/apply/<title>')
@login_required
def apply(title):
    email=query_db("select email from users where username=?",(session['username'],))
    msg = Message("Apply",
                  sender="ccslog.apply@gmail.com",
                  recipients=["ccslog.apply@gmail.com"])
    msg.body="%s wants to apply in project titled %s \nconfirm at email %s" % (session['username'],title,email[0][0]) 

    mail.send(msg)
    flash("mail has been sent to admin for confirmation")
    notice_by=session["username"]
    notice_for="admin"
    execute_db("insert into notifications (for,by,project) values (?,?,?) ",(notice_for,notice_by,title,))

    return redirect(url_for("projects"))


@app.route('/edit_profile' , methods=['GET','POST'])
@login_required 
def edit_profile():
    ecount=query_db("select count(id) from events where accept=? ",(0,))
    pcount=query_db("select count(id) from projects where accept=? ",(0,))
    a=query_db("select admin from users where username =?",(session["username"],))
    admin=a[0][0]
    data=query_db("select * from users where username=?",(session['username'],))
    if request.method=='GET':
        return render_template("edit_profile.html",data=data,pcount=pcount,ecount=ecount,admin=admin)   
    else:
        submission={}
        submission["name"]=request.form["name"]
        submission["username"]=request.form["username"]
        submission["phone"]=request.form["phone"]
        submission["email"]=request.form["email"]
        if query_db("select username from users where username = ? and name != ?", (submission["username"],data[0][1],))!=[]:
            flash("Username already taken","danger")
            return render_template("edit_profile.html",data=data)
        else:
            execute_db("update users set name=? , phoneno=? ,username=?, email=? where username=?",(submission["name"],submission["phone"],submission["username"],submission["email"],session["username"],))
            data1=query_db("select * from users where username=?",(session['username'],))
            flash("Profile updated !")
            return render_template("edit_profile.html",data=data1,pcount=pcount,ecount=ecount,admin=admin)

@app.route('/accept_project/<project_id>')
@login_required
def accept_project(project_id):
    execute_db("update projects set accept=? where id=?",(1,project_id,))
    return redirect(url_for("projects"))   

@app.route('/accept_event/<event_id>')
@login_required
def accept_event(event_id):
    execute_db("update events set accept=? where id=?",(1,event_id,))
    return redirect(url_for("events"))           

@app.route('/notifications')
@login_required
def notifications():
    ecount=query_db("select count(id) from events where accept=? ",(0,))
    pcount=query_db("select count(id) from projects where accept=? ",(0,))
    a=query_db("select admin from users where username =?",(session["username"],))
    admin=a[0][0]
    row=query_db("select * from notifications where for=?",(session["username"],))
    row1=query_db("select * from notifications where for=?",("admin",))    

    return render_template("notifications.html",admin=admin,row=row,row1=row1,pcount=pcount,ecount=ecount)    

@app.route('/accept_apply/<id>')
@login_required
def accept_apply(id):
    r=query_db("select * from notifications where id=?",(id,))
    notice_for=r[0][1]
    title=r[0][2]
    notice_by="admin"
    execute_db("insert into notifications (for,by,project) values (?,?,?) ",(notice_for,notice_by,title,))
    execute_db("delete from notifications where id=?",(id,))
    return redirect(url_for("notifications"))
     
         

@app.route('/delete_notice/<notice_id>')
@login_required
def delete_notice(notice_id):
    execute_db('delete from notifications where id=?',(notice_id,))
    return redirect(url_for("notifications"))             


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],filename)

if __name__ == "__main__":
    
    app.run(host = "0.0.0.0",debug=True, port=8080)
