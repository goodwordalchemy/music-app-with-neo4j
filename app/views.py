from .models import User, Track
from flask import Flask, request, session, redirect
from flask import url_for, render_template, flash

app = Flask(__name__)

@app.route('/')
def index():
	tracks = Track.get_all_tracks()
	return render_template('index.html', tracks=tracks)


@app.route('/register', methods=['GET','POST'])
def register():
	if request.method == 'POST':
		username = request.form['username']
		password = request.form['password']

		if len(username) < 1:
			flash('Your username must be at least 1 character')
		elif len(password) < 5:
			flash('Your username must be at least 5 characters')
		elif not User(username).register(password):
			flash('A user with that username already exists')
		else:
			session['username'] = username
			flash("Logged in.")
			return redirect(url_for('index'))
	return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
	if request.method == 'POST':
		username = request.form['username']
		password = request.form['password']

		if not User(username).verify_password(password):
			flash("Invalid login.")
		else:
			session['username'] = username
			flash('Logged in.')
			return redirect(url_for('index'))
	return render_template('login.html')


@app.route('/search_track', methods=['POST'])
def search_track():
	print "in search track"
	spotify_uri = request.form['spotify_uri']
	
	if not spotify_uri:
		flash("You must provide a spotify id for your track")
		return redirect(url_for('index'))

	track_obj = Track(spotify_uri=spotify_uri)
	track = track_obj.find()
	if not track:
		track = track_obj.create_from_spotify_uri()
	return redirect(url_for('like_track', track_id=track['_id']))
	

@app.route('/like_track/<track_id>')
def like_track(track_id):
	username = session.get('username')

	if not username:
		flash('You must be logged in to like a post.')
		return redirect(url_for('login'))

	User(username).like_track(_id=track_id)
	flash("Liked track.")
	return redirect(request.referrer)

@app.route('/profile/<username>')
def profile(username):
	logged_in_username = session.get('username')
	user_being_viewed_username = username

	user_being_viewed = User(user_being_viewed_username)
	tracks = user_being_viewed.get_liked_tracks()

	return render_template(
		'profile.html',
		username=username,
		tracks=tracks)


@app.route('/logout', methods=['GET'])
def logout():
	session.pop('username', None)
	flash("Logged out.")
	return redirect(url_for('index'))
