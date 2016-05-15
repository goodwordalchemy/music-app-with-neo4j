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

def relationship_exists(rel):
	result = len(list(graph.match(
		start_node=rel.start_node(), 
		end_node=rel.end_node(),
		rel_type=rel.type())))
	print "relationship exists: ", result
	return result

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
		optional match (entity)-[:AppearsOn]->(album)
		optional match (entity)-[:PerformedBy]->(artists)
		
		return user, like_event, entity, album, collect(artists) as artists;
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
		rel = Liked(user, track.find())
		
		if relationship_exists(rel):
			return False
		else:
			rel['timestamp'] = Timestamp().as_epoch()
			tx = graph.begin()
			tx.create(rel)
			tx.commit()
			return True

class Liked(Relationship):

	def __init__(self, start_node, end_node):
		Relationship.__init__(
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
				album=le['album'],
				artists=le['artists'],
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
		optional match (entity)-[:AppearsOn]->(album)
		optional match (entity)-[:PerformedBy]->(artists)
		return user, like_event, entity, album, collect(artists) as artists;
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
		tx = graph.begin()

		track = Node("Track",
			uuid=str(uuid.uuid4()),
			spotify_uri=kwargs['spotify_uri'],
			name=kwargs['name'])
		tx.create(track)

		artists = kwargs['artists']
		artists = [Artist(**artists[i]) for i in range(len(artists))]
		artists = [a.find() or a for a in artists]

		for a in artists:
			tx.merge(a)

		track_performed_by = [PerformedBy(track, a) for a in artists]
		for tpb in track_performed_by:
			tx.merge(tpb)

		album = Album(**kwargs['album'])
		tx.merge(album)
		appears_on = AppearsOn(track, album)
		tx.merge(appears_on)
		album_performed_by = [PerformedBy(album, a) for a in artists]
		for apb in album_performed_by:
			tx.merge(apb)
		
		tx.commit()

		return track

	def get_all_like_events(self, **kwargs):
		query = """
		match (user)-[like_event:Liked]->(entity)
		where entity.uuid = "{}"
		optional match (entity)-[:AppearsOn]->(album)
		optional match (entity)-[:PerformedBy]->(artists)
		
		return user, like_event, entity, album, collect(artists) as artists;
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

class Artist(Node):
	def __init__(self, *otherlabels, **kwargs):
		Node.__init__(self, 
			self.__class__.__name__, 
			*otherlabels, **kwargs)
		if not 'uuid' in kwargs.keys():
			self['uuid'] = str(uuid.uuid4())
	
	def find(self):
		artist = None
		if self['uuid']:
			artist = graph.find_one("Artist", 
				"uuid", self['uuid'])
		elif self['spotify_uri']:
			artist = graph.find_one("Artist", 
				"spotify_uri", self.spotify_uri)
		return artist

	def get_all_like_events(self, **kwargs):
		query = """
		match (user)-[like_event:Liked]->(entity)
		optional match (entity)-[:AppearsOn]->(album)
		optional match (entity)-[:PerformedBy]->(artist)
		where artist.uuid = "{}"
		return user, like_event, entity, album, collect(artist) as artists;
		""".format(self['uuid'])
		return Liked.run_like_events_query(query, **kwargs)



class Album(Node):
	def __init__(self, *otherlabels, **kwargs):
		Node.__init__(self, 
			self.__class__.__name__, 
			*otherlabels, **kwargs)
		if 'uuid' not in kwargs.keys():
			self['uuid']=str(uuid.uuid4())

	def find(self):
		album = None
		if self['uuid']:
			album = graph.find_one("Album", 
				"uuid", self['uuid'])
		elif self['spotify_uri']:
			album = graph.find_one("Album", 
				"spotify_uri", self.spotify_uri)
		return album

	def get_all_like_events(self, **kwargs):
		query = """
		match (user)-[like_event:Liked]->(entity)
		optional match (entity)-[:AppearsOn]->(album)
		optional match (entity)-[:PerformedBy]->(artist)
		where album.uuid = "{}"
		return user, like_event, entity, album, collect(artist) as artists;
		""".format(self['uuid'])
		return Liked.run_like_events_query(query, **kwargs)

class AppearsOn(Relationship):
	def __init__(self, start_node, end_node):
		Relationship.__init__(
			self, 
			start_node, 
			self.__class__.__name__,
			end_node)

class PerformedBy(Relationship):
	def __init__(self, start_node, end_node):
		Relationship.__init__(
			self, 
			start_node, 
			self.__class__.__name__,
			end_node)
