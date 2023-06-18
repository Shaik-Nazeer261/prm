from flask import Flask,render_template,url_for,request,flash,redirect,abort\
,session
from flask_session import Session
from key import secret_key,salt1,salt2
from stoken import token
from cmail import sendmail
import mysql.connector
from itsdangerous import URLSafeTimedSerializer
mydb=mysql.connector.connect(host='localhost',user='root',password='sgnk@143',db='prm')
app=Flask(__name__)
app.secret_key=secret_key
app.config['SESSION_TYPE']='filesystem'
Session(app)
@app.route('/')
def index():
    return render_template('title.html')
@app.route('/login',methods=['GET','POST'])
def login():
    if session.get('user'):
        return redirect(url_for('home'))
    if  request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from users where username=%s',[username])
        count=cursor.fetchone()[0]
        if count==1:
            cursor.execute('select count(*) from users where username=%s and password=%s',(username,password))           
            p_count=cursor.fetchone()[0]
            if p_count==1:
                session['user']=username
                cursor.execute('select email_status from users where username=%s',[username])
                status=cursor.fetchone()[0]
                cursor.close()
                if status!='confirmed':
                    return redirect(url_for('inactive'))
                else:
                    return redirect(url_for('home'))
            else:
                cursor.close()
                flash('invalid password')
                return render_template('login.html')
        else:
            cursor.close()
            flash('invalid username')
            return render_template('login.html')
    return render_template('login.html')
@app.route('/logout')
def logout():
    if session.get('user'):
        session.pop('user')
        return redirect(url_for('login'))
    else:
        return redirect(url_for('login'))
@app.route('/inactive')
def inactive():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from users where username=%s',[username])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            return redirect(url_for('home'))
        else:
            return render_template('inactive.html')
    else:
        return redirect(url_for('login'))
@app.route('/resendconfirmaton')
def resend():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from users where username=%s',[username])
        status=cursor.fetchone()[0]
        cursor.execute('select email from users where username=%s',[username] )
        email=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            flash('email already confirmed')
            return render_template(url_for('home'))
        else:
            subject='Email Confirmation'
            confirm_link=url_for('confirm',token=token(email,salt1),_external=True)
            body=f"please confirm your mail-\n\n{confirm_link}"
            sendmail(to=email,body=body,subject=subject)
            flash('Confirmation link sent check your email')
            return redirect(url_for('inactive'))
    else:
        return redirect(url_for('login'))   
@app.route('/homepage')
def home():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from users where username=%s',[username])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            return render_template('homepage.html')
        else:
            return redirect(url_for('inactive'))
    else:
        return redirect(url_for('login'))
@app.route('/registration',methods=['GET','POST'])
def registration():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        try:
            cursor.execute('insert into users(username,password,email) values(%s,%s,%s)',(username,password,email))
        except mysql.connector.IntegrityError:
            flash('username or email is already in use')
            return render_template('registration.html')
        else:
            mydb.commit()
            cursor.close()
            subject='Email Confirmation'
            confirm_link=url_for('confirm',token=token(email,salt1),_external=True)
            body=f"Thanks for signing up.follow this link-\n\n{confirm_link}"
            sendmail(to=email,body=body,subject=subject)
            flash('Confirmation link sent check your email')
            return render_template('registration.html')
    return render_template('registration.html')   
@app.route('/confirm/<token>')
def confirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        email=serializer.loads(token,salt=salt1,max_age=600)
    except Exception as e:
        print(e)
        abort(404,'link expired')
    else:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from users where email=%s',[email])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            flash('email already confirmed')
            return redirect(url_for('login'))
        else:
            cursor=mydb.cursor(buffered=True)
            cursor.execute("update users set email_status='confirmed' where email=%s",[email])
            mydb.commit()
            flash('mail confirmation success')
            return redirect(url_for('login'))
@app.route('/forgot',methods=['GET','POST'])
def forgot():
    if request.method=='POST':
        email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from users where email=%s',[email])
        count=cursor.fetchone()[0]
        cursor.close()
        if count==1:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select email_status from users where email=%s',[email])
            status=cursor.fetchone()[0]
            cursor.close()
            if status!='confirmed':
                flash('please confirm your mail first')
                return render_template('forgot.html')
            else:
                subject='Forgot Password'
                confirm_link=url_for('reset',token=token(email,salt2),_external=True)
                body=f"Use the below link to reset passsword -\n\n{confirm_link}"
                sendmail(to=email,body=body,subject=subject)
                flash('reset password link has been sent to your mail')
                return redirect(url_for('login'))
        else:
            flash('inavlid email ID')
            return render_template('forgot.html')
    return render_template('forgot.html')
@app.route('/reset/<token>',methods=['GET','POST'])
def reset(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        email=serializer.loads(token,salt=salt2,max_age=120)
    except:
        abort(404,'link expired')
    else:
        if request.method=='POST':
            newpassword=request.form['npassword']
            confirmpassword=request.form['cpassword']
            if newpassword==confirmpassword:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update users set password=%s where email=%s',(newpassword,email))
                mydb.commit()
                cursor.close()
                flash('reset succesful')
                return redirect(url_for('login'))      
            else:
                flash('passwords mismatched')
                return render_template('newpassword.html')
        return render_template('newpassword.html')
@app.route('/addnotes',methods=['GET','POST'])
def addnotes():
    if session.get('user'):
        if request.method==('POST'):
            title=request.form['title']
            content=request.form['content']
            username=session.get('user')
            cursor=mydb.cursor(buffered=True)
            cursor.execute('insert into notes(nid,title,content,added_by) values(UUID_TO_BIN(UUID()),%s,%s,%s)',(title,content,username))
            mydb.commit()
            cursor.close()
            flash('notes added successfully')
            return redirect(url_for('viewnotes'))
        return render_template('addnotes.html')
    else:
        return redirect(url_for('login'))
@app.route('/viewnotes')
def viewnotes():
    if session.get('user'):
        username=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select bin_to_uuid(nid)  as nid,title,date from notes where added_by=%s order by date desc',[username])
        data=cursor.fetchall()
        cursor.close()
        return render_template('table.html',data=data)
    else:
        return redirect(url_for('login'))
@app.route('/nid/<uid>')
def vnid(uid):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select bin_to_uuid(nid),title,content,date from notes where bin_to_uuid(nid)=%s ',[uid])
    uid,title,content,date=cursor.fetchone()
    return render_template('viewnotes.html',title=title,content=content,date=date)
@app.route('/delete/<uid>')
def delete(uid):
    cursor=mydb.cursor(buffered=True)
    cursor.execute('delete from notes where bin_to_uuid(nid)=%s',[uid])
    mydb.commit()
    cursor.close()
    flash('succesfully deleted the notes')
    return redirect(url_for('viewnotes'))
@app.route('/update/<uid>')
def update(uid):
    if request.method==('POST'):
        title=request.form['title']
        content=request.form['content']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('update notes set title=%s,content=%s where bin_to_uuid(nid)=%s',[uid])
        mydb.commit()
        cursor.close()
        return render_template('update.html',title=title,content=content)
    else:
        return redirect(url_for('viewnotes'))

app.run(use_reloader=True,debug=True)