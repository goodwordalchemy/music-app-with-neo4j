from datetime import datetime
import os
import uuid

from passlib.hash import bcrypt
from py2neo import Graph, Node, Relationship, authenticate

from app.common.timestamp import Timestamp
from app.common.spotify_utils import get_spotify_api, SpotifyInvalidRequestError

def get_db_url():
	hostport = os.environ.get('NEO4J_HOSTPORT')
	return "http://{hostport}/db/data/".format(hostport=hostport)

def get_graph():
	hostport = os.environ.get('NEO4J_HOSTPORT')
	username = os.environ.get('NEO4J_USERNAME')
	password = os.environ.get('NEO4J_PASSWORD')
	authenticate(hostport, username, password)
	return Graph(get_db_url())

graph = get_graph()
spotify = get_spotify_api()

class User:
	def __init__(self, username):
		self.uuid = str(uuid.uuid4()),
		self.username = username

	def find(self):
		user = graph.find_one("User", "username", self.username)
		return user

	def register(self, password):
		if not self.find():
			user = Node("User",
				uuid=str(uuid.uuid4()),
				username=self.username, 
				password=bcrypt.encrypt(password))
			graph.create(user)
			return True
		else:
			return False

	def verify_password(self, password):
		user = self.find()
		if user:
			return bcrypt.verify(password, user['password'])
		else:
			return False

	def get_liked_tracks(self):
		user = self.find()
		query = """
		MATCH (user:User)-[:Liked]->(track:Track)
		WHERE user.username = {username}
		RETURN track
		"""
		return graph.cypher.execute(query, username=user['username'])

	def like_track(self, **kwargs):
		"""kwargs in this case would be either a spotify_id or track._id"""
		user = self.find()
		track = Track(**kwargs)
		rel = Relationship(user, "Liked", track.find())
		result = graph.cypher.execute("""
			match (n)-[r:Liked]->(p) 
			where p.uuid = {track_uuid} 
			and n.username={username} return n,r,p;""", 
			username=self.username,
			track_uuid=track.uuid)
		if len(result):
			return False
		else:
			graph.create_unique(rel)
			return True
		


class Track:
	"""
	id: unique identifier string (automatically generated)
	spotify_uri: unique
	"""
	def __init__(self, uuid=None, spotify_uri=None):
		if not spotify_uri and not uuid:
			raise Exception("Must provide either an uuid or a spotify_uri to instantiate a track object")
		self.uuid = uuid
		self.spotify_uri = spotify_uri

	def find(self):
		track = None
		if self.uuid:
			track = graph.find_one("Track", "uuid", self.uuid)
		elif self.spotify_uri:
			track = graph.find_one("Track", 
				"spotify_uri", self.spotify_uri)
		return track

	def create(self, **kwargs):
		track = Node("Track",
			uuid=str(uuid.uuid4()),
			spotify_uri=kwargs['spotify_uri'],
			name=kwargs['name'])
		track, = graph.create(track)
		return track

	def lookup_track_by_spotify_uri(self):
		try:
			return spotify.get_track_by_spotify_uri(self.spotify_uri)
		except SpotifyInvalidRequestError as e:
			return False

	@staticmethod
	def get_all_tracks():
		query = """
		MATCH (track:Track)
		RETURN track
		"""
		return graph.cypher.execute(query)
