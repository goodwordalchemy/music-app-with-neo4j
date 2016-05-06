from datetime import datetime
import os
import uuid

from passlib.hash import bcrypt
from py2neo import Graph, Node, Relationship, authenticate

from cosmogasm.common.timestamp import Timestamp
from cosmogasm.common.spotify_utils import get_spotify_api, SpotifyInvalidRequestError

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

	def get_all_like_events(self, **kwargs):
		query = """
		match (user)-[like_event:Liked]->(entity)
		where user.username = "{}"
		return user, like_event, entity;
		""".format(self.username)
		return Liked.run_like_events_query(query, **kwargs)


	def get_liked_tracks(self):
		user = self.find()
		query = """
		MATCH (user:User)-[:Liked]->(track:Track)
		WHERE user.username = {username}
		RETURN track
		"""
		return graph.run(query, username=user['username'])

	def like_track(self, **kwargs):
		"""kwargs in this case would be either a spotify_id or track._id"""
		user = self.find()
		track = Track(**kwargs)
		rel = Relationship(user, "Liked", track.find())
		if graph.exists(rel):
			return False
		else:
			rel['timestamp'] = Timestamp().as_epoch()
			graph.create(rel)
			return True

class Liked(Relationship):
	def __init__(self, start_node, end_node):
		super(Liked, self).__init__(
			self, 
			start_node, 
			self.__class__.__name__,
			end_node)

	@classmethod
	def like_event_to_dict_func(cls, **kwargs):
		"""
		kwargs should be of the form :

			{key: func that takes le as argument}

		"""
		def _make_dict(le):
			thedict = dict(
				username=le['user']['username'],
				entity_name=le['entity']['name'],
				# album=
				# artists=
				timestamp=Timestamp(le['like_event']['timestamp']).as_str(),
				entity_uuid=le['entity']['uuid'])
			for kw, func in kwargs.iteritems():
				thedict.update({kw:func(le)})
			return thedict
		return _make_dict

	@classmethod
	def get_all_like_events(cls, **kwargs):
		query = """
		match (user)-[like_event:Liked]->(entity)
		return user, like_event, entity;
		"""
		return cls.run_like_events_query(query, **kwargs)

	@classmethod
	def run_like_events_query(cls, query, **kwargs):
		to_like_event = cls.like_event_to_dict_func(**kwargs)
		like_events = graph.run(query)
		like_events = [to_like_event(le) for le in like_events]
		return like_events


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
			name=kwargs['name'],
			# album=kwargs['album'],
			# artists=kwargs['artists']
			)
		track, = graph.create(track)
		return track

	def get_all_like_events(self, **kwargs):
		query = """
		match (user)-[like_event:Liked]->(entity)
		where entity.uuid = "{}"
		return user, like_event, entity;
		""".format(self.uuid)
		return Liked.run_like_events_query(query, **kwargs)

	def lookup_track_by_spotify_uri(self):
		try:
			return spotify.get_track_by_spotify_uri(self.spotify_uri)
		except SpotifyInvalidRequestError as e:
			return False

	@staticmethod
	def get_all_tracks():
		query = """
		match (user)-[like_event:Liked]->(entity)
		return user, like_event, entity;
		"""
		return graph.run(query)
