"""
This module provides an interface for querying and parsing
information from the spotify api
"""

from spotify_api import SpotifyAPI

class SpotifyAppAPI(SpotifyAPI):

	def get_spotify_id_from_uri(self, uri):
		return uri.split(":")[-1]

	def get_track_by_spotify_uri(self, spotify_uri):
		spotify_id = self.get_spotify_id_from_uri(spotify_uri)
		track_obj = self.get('tracks/{}'.format(spotify_id))
		return self.parse_track_obj(track_obj)

	def parse_track_obj(self, track_obj):
		return dict(
			name=track_obj['name'],
			uri=track_obj['uri'],
			album=self.parse_album_obj(track_obj['album']),
			artists=[self.parse_artist_obj(artist) for artist in track_obj['artists']])

	def parse_album_obj(self, album_obj):
		return dict(
			name=album_obj['name'],
			uri=album_obj['uri'],
			album_type=album_obj['album_type'])

	def parse_artist_obj(self, artist_obj):
		return dict(
			name=artist_obj['name'],
			uri=artist_obj['uri'])



def get_spotify_api():
	from config import Config
	config_dict = Config.__dict__
	api = SpotifyAppAPI(config_dict)
	return api

if __name__ == '__main__':
	api = get_spotify_api()
	print api.get_track_by_spotify_uri('spotify:track:4sI8uN1G3PsoiNizkOqATO')