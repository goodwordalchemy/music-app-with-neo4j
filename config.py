import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
	SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)
	SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
	SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
	SPOTIFY_CALLBACK_URI = "http://localhost:8000/callback/spotify"

def get_config_dict():
	return Config.__dict__