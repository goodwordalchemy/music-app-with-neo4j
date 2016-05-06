from flask import Flask, request, session, redirect
from flask import url_for, render_template, flash

from app.models import User, Track, Liked
from app.common.timestamp import Timestamp

app = Flask(__name__)
app.config.from_object('config.Config')

def _show_like_button(le):
	session_username = session.get('username')
	if not session_username:
		return False
	like_event_username = le['user']['username']
	tf_show_like_button = like_event_username != session_username
	tf_show_like_button &= session_username != like_event_username
	return tf_show_like_button

@app.route('/')
def index():
	"""shows all like_events"""
	like_events = Liked.get_all_like_events(show_like_button=_show_like_button)
	print like_events

	return render_template('index.html', like_events=like_events)

@app.route('/profile/<username>')
def profile(username):
	logged_in_username = session.get('username') # in case we want special logic for editing a profile etc.
	user_being_viewed_username = username
	user_being_viewed = User(user_being_viewed_username)

	like_events = user_being_viewed.get_all_like_events(show_like_button=_show_like_button)
	
	return render_template(
		'profile.html',
		username=username,
		like_events=like_events)

@app.route('/track/<track_uuid>')
def track(track_uuid):
	"""
	this page will show all of the like events for a track.
	"""
	track = Track(uuid=track_uuid)
	db_track = track.find()
	like_events = track.get_all_like_events(show_like_button=lambda _: False)
	return render_template(
		'track.html',
		name=db_track['name'],
		like_events=like_events)


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
		track_info = track_obj.lookup_track_by_spotify_uri()
		if not track_info:
			flash("could not find a track with that id")
			return redirect(url_for('index'))
		track = track_obj.create(**track_info)
	return redirect(url_for('like_track', track_id=track['uuid']))
	

@app.route('/like_track/<track_id>')
def like_track(track_id):
	username = session.get('username')

	if not username:
		flash('You must be logged in to like a post.')
		return redirect(url_for('login'))

	tf_liked_track = User(username).like_track(uuid=track_id)
	if tf_liked_track:
		flash("Liked track.")
	else:
		flash("Cannot like track that you already like")
	return redirect(request.referrer)


@app.route('/logout', methods=['GET'])
def logout():
	session.pop('username', None)
	flash("Logged out.")
	return redirect(url_for('index'))

