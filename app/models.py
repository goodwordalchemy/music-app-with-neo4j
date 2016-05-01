from datetime import datetime
import os
import uuid

from passlib.hash import bcrypt
from py2neo import Graph, Node, Relationship, authenticate

from app.common.timestamp import Timestamp

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

class User:
	def __init__(self, username):
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
		track = Track(**kwargs).find()
		rel = Relationship(user, "Liked", track,
			timestamp=Timestamp().get_as_epoch())
		graph.create(rel)


class Track:
	def __init__(self, _id=None, spotify_uri=None):
		if not spotify_uri and not _id:
			raise Exception("Must provide either an _id or a spotify_uri to instantiate a track object")
		self._id = _id
		self.spotify_uri = spotify_uri

	def find(self):
		track = None
		if self._id:
			track = graph.find_one("Track", "_id", self._id)
		elif self.spotify_uri:
			track = graph.find_one("Track", 
				"spotify_uri", self.spotify_uri)
		return track

	def create_from_spotify_uri(self):
		track = Node("Track",
			_id=str(uuid.uuid4()), 
			spotify_uri=self.spotify_uri)
		track = graph.create(track)[0]
		return track
		

	@staticmethod
	def get_all_tracks():
		query = """
		MATCH (track:Track)
		RETURN track
		"""
		return graph.cypher.execute(query)
