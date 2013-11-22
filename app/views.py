from flask import render_template, flash, redirect, session, url_for, request, g
from flask.ext.login import login_user, logout_user, current_user, login_required
from app import app, db, lm, oid
from forms import LoginForm, EditForm, PostForm, SearchForm
from models import User, ROLE_USER, ROLE_ADMIN, Post
from datetime import datetime
from emails import follower_notification
from config import POSTS_PER_PAGE 
import random
from config import WHOOSH_ENABLED

def randomImage():
    x = random.randint(0, 10)
    if x == 1:
        return '/static/pics/OeLvray.jpg'
    elif x == 2:
        return '/static/pics/6nMCK8w.jpg'
    elif x == 3:
        return '/static/pics/blackoutny.jpg'
    elif x == 4:
        return '/static/pics/hMPG6Na.jpg'
    elif x == 5:
        return '/static/pics/I4RoX0j.jpg'
    elif x == 6:
        return '/static/pics/plantagon-ed001.jpg'
    elif x == 7:
        return '/static/pics/pumpkin.jpg'
    elif x == 8:
        return '/static/pics/zrZfxWi.jpg'
    elif x == 9:
        return '/static/pics/zY2Kadi.jpg'
    else:   
        return '/static/pics/LrEK3o8.jpg'

#imageList = ['/static/pics/OeLvray.jpg', '/static/pics/6nMCK8w.jpg', '/static/pics/blackoutny.jpg', '/static/pics/hMPG6Na.jpg', '/static/pics/I4RoX0j.jpg', '/static/pics/plantagon-ed001.jpg', '/static/pics/pumpkin.jpg', '/static/pics/zrZfxWi.jpg', '/static/pics/zY2Kadi.jpg', '/static/pics/LrEK3o8.jpg']

imageList = ['/static/pics/OeLvray.jpg', '/static/pics/OeLvray.jpg',  '/static/pics/6nMCK8w.jpg', '/static/pics/6nMCK8w.jpg', '/static/pics/6nMCK8w.jpg', '/static/pics/blackoutny.jpg', '/static/pics/blackoutny.jpg', '/static/pics/hMPG6Na.jpg',  '/static/pics/hMPG6Na.jpg', '/static/pics/I4RoX0j.jpg',  '/static/pics/I4RoX0j.jpg', '/static/pics/plantagon-ed001.jpg', '/static/pics/plantagon-ed001.jpg', '/static/pics/pumpkin.jpg',  '/static/pics/pumpkin.jpg', '/static/pics/zrZfxWi.jpg',  '/static/pics/zrZfxWi.jpg',  '/static/pics/zY2Kadi.jpg', '/static/pics/zY2Kadi.jpg',  '/static/pics/LrEK3o8.jpg',  '/static/pics/LrEK3o8.jpg']



@lm.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.before_request
def before_request():
    g.user = current_user
    if g.user.is_authenticated():
        g.user.last_seen = datetime.utcnow()
        db.session.add(g.user)
        db.session.commit()
        g.search_form = SearchForm()
    g.search_enabled = WHOOSH_ENABLED



@app.errorhandler(404)
def internal_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

@app.route('/', methods = ['GET', 'POST'])
@app.route('/index', methods = ['GET', 'POST'])
@app.route('/index/<int:page>', methods = ['GET', 'POST'])
@login_required
def index(page = 1):
    form = PostForm()
    if form.validate_on_submit():
        post = Post(body = form.post.data, timestamp = datetime.utcnow(), author = g.user)
        db.session.add(post)
        db.session.commit()
        flash('Your post is now live!')
        logged = User.query.all() 
        userNumber = logged.index(g.user)
        logged.pop(userNumber)
        def userTimes(userList):
             a = []
             for x in userList:
                a.append(x.last_seen)
             return a
        times = userTimes(logged)
        def ago(times):
             a = []
             for x in times:
                 a.append(datetime.utcnow()-x)
             return a
        ago = ago(times)
        latest = logged[ago.index(min(ago))]
        reply = latest.posts.all()
        reply = reply[-1].body
        if reply == post.body:
           flash("Match")
           match = "Match"
#        return redirect(url_for('index'))
        
    posts = g.user.followed_posts().all
#   pic = randomImage()
    pic = imageList.pop()
    imageList.insert(0, pic)
    logged = User.query.all() 
    userNumber = logged.index(g.user)
    logged.pop(userNumber)
#    def subtractYou(logged):
#        for x in range(0, len(logged)-1):
#            if logged[x] == g.user:
#                logged.pop(x) 
#    subtractYou(logged)
    def userTimes(userList):
        a = []
        for x in userList:
            a.append(x.last_seen)
        return a
    times = userTimes(logged)
    def ago(times):
        a = []
        for x in times:
            a.append(datetime.utcnow()-x)
        return a
    ago = ago(times)
    latest = logged[ago.index(min(ago))]
    reply = latest.posts.all()
    reply = reply[-1].body
    match = ""
#    if reply == post:
#        match = "Match"
#    player1 = logged.pop(latest)
#        player1 = player1)
    return render_template('index.html',
        title = 'Home',
        form = form,
        posts = posts,
        pic = pic,
        logged = logged,
        times = times,
        ago = ago,
        latest = latest,
        reply = reply,
        match = match)

@app.route('/login', methods = ['GET', 'POST'])
@oid.loginhandler
def login():
    if g.user is not None and g.user.is_authenticated():
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        session['remember_me'] = form.remember_me.data
        return oid.try_login(form.openid.data, ask_for = ['nickname', 'email'])
    return render_template('login.html', 
        title = 'Sign In',
        form = form,
        providers = app.config['OPENID_PROVIDERS'])

@oid.after_login
def after_login(resp):
    if resp.email is None or resp.email == "":
        flash('Invalid login. Please try again.')
        return redirect(url_for('login'))
    user = User.query.filter_by(email = resp.email).first()
    if user is None:
        nickname = resp.nickname
        if nickname is None or nickname == "":
            nickname = resp.email.split('@')[0]
        nickname = User.make_unique_nickname(nickname)
        user = User(nickname = nickname, email = resp.email, role = ROLE_USER)
        db.session.add(user)
        db.session.commit()
        # make the user follow him/herself
        db.session.add(user.follow(user))
        db.session.commit()
    remember_me = False
    if 'remember_me' in session:
        remember_me = session['remember_me']
        session.pop('remember_me', None)
    login_user(user, remember = remember_me)
    return redirect(request.args.get('next') or url_for('index'))

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))
    
@app.route('/user/<nickname>')
@app.route('/user/<nickname>/<int:page>')
@login_required
def user(nickname, page = 1):
    user = User.query.filter_by(nickname = nickname).first()
    if user == None:
        flash('User ' + nickname + ' not found.')
        return redirect(url_for('index'))
    posts = user.posts.paginate(page, POSTS_PER_PAGE, False)
    return render_template('user.html',
        user = user,
        posts = posts)

@app.route('/edit', methods = ['GET', 'POST'])
@login_required
def edit():
    form = EditForm(g.user.nickname)
    if form.validate_on_submit():
        g.user.nickname = form.nickname.data
        g.user.about_me = form.about_me.data
        db.session.add(g.user)
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit'))
    elif request.method != "POST":
        form.nickname.data = g.user.nickname
        form.about_me.data = g.user.about_me
    return render_template('edit.html',
        form = form)

@app.route('/follow/<nickname>')
@login_required
def follow(nickname):
    user = User.query.filter_by(nickname = nickname).first()
    if user == None:
        flash('User ' + nickname + ' not found.')
        return redirect(url_for('index'))
    if user == g.user:
        flash('You can\'t follow yourself!')
        return redirect(url_for('user', nickname = nickname))
    u = g.user.follow(user)
    if u is None:
        flash('Cannot follow ' + nickname + '.')
        return redirect(url_for('user', nickname = nickname))
    db.session.add(u)
    db.session.commit()
    flash('You are now following ' + nickname + '!')
    follower_notification(user, g.user)
    return redirect(url_for('user', nickname = nickname))

@app.route('/unfollow/<nickname>')
@login_required
def unfollow(nickname):
    user = User.query.filter_by(nickname = nickname).first()
    if user == None:
        flash('User ' + nickname + ' not found.')
        return redirect(url_for('index'))
    if user == g.user:
        flash('You can\'t unfollow yourself!')
        return redirect(url_for('user', nickname = nickname))
    u = g.user.unfollow(user)
    if u is None:
        flash('Cannot unfollow ' + nickname + '.')
        return redirect(url_for('user', nickname = nickname))
    db.session.add(u)
    db.session.commit()
    flash('You have stopped following ' + nickname + '.')
    return redirect(url_for('user', nickname = nickname))

@app.route('/search', methods = ['POST'])
@login_required
def search():
    if not g.search_form.validate_on_submit():
        return redirect(url_for('index'))
    return redirect(url_for('search_results', query = g.search_form.search.data))

@app.route('/search_results/<query>')
@login_required
def search_results(query):
    results = Post.query.whoosh_search(query, MAX_SEARCH_RESULTS).all()
    return render_template('search_results.html',
        query = query,
        results = results)

