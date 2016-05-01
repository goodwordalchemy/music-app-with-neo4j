import requests, base64, datetime, types, time, json, pickle, os
from rauth import OAuth2Service

logfile_name = 'apierrors.log'

class SpotifyException(Exception):
	
	def __init__(self, response):
		try:
			response_json = response.json()
		except ValueError:
			response_json = response
		print 'response', 	response_json
		self.response_json = response_json

	def get_response(self):
		return self.response_json['error']

	def get_status_code(self):
		return str(self.response_json['error']['status'])

	def get_message(self):
		return self.response_json['error']['message']

	def log_to_file(self, api, filename=logfile_name):
		most_recent_request = api.get_most_recent_request_address()
		line = '|'.join([self.get_status_code(), self.get_message(), most_recent_request]) + '\n'
		with open(filename, 'a') as logfile:
			logfile.write(line.encode("UTF-8"))

class SpotifyTimeoutError(SpotifyException):
	
	def __init__(self, response):
		SpotifyException.__init__(self, response)
		self.retry_after = response['headers']['Retry-After']

	def wait(self):
		print "exceeded rate limit.  Trying again in {} seconds...".format(self.retry_after)
		time.sleep(self.retry_after)

class SpotifyAuthenticationError(SpotifyException):
	
	def __init__(self, response):
		print "token timed out.  Getting new authentication token"
		if 'spotify-token.pickle' in os.listdir('.'):
			os.remove('spotify-token.pickle')
		SpotifyException.__init__(self, response)
	
	def authenticate(self):
		return SpotifyAuthAPI()

class SpotifyNotFoundError(SpotifyException):
	pass

class SpotifyInvalidRequestError(SpotifyException):
	pass

class SpotifyInternalServerError(SpotifyException):
	def __init__(self, response):
		SpotifyException.__init__(self, response)
		wait_time = 60
		print "iternal server error.  Going to sleep for {}".format(wait_time)
		time.sleep(wait_time)


def handle_http_errors(f):
	def wrapped_f(*args, **kwargs):
		for i in range(5):
			try:
				response = f(*args, **kwargs)
				return response
			except SpotifyTimeoutError as e:
				retry_after = e.wait()
				time.sleep(retry_after)
			except SpotifyAuthenticationError as e:
				pass
			except (SpotifyNotFoundError, SpotifyInvalidRequestError) as e:
				raise e
		raise SpotifyException(response.json())
	return wrapped_f

class SpotifyAPI(object):

	"""Can be used by email service to get a public playlist's tracks"""
	def __init__(self, config):
		self.config = config
		self.request_epoch = time.time()
		self.time_between_requests = 1
		self.assign_token()
		self.most_recent_request_address = None

	def assign_token(self):
		client_id = self.config['SPOTIFY_CLIENT_ID']
		client_secret = self.config['SPOTIFY_CLIENT_SECRET']
		token = requests.post(
			'https://accounts.spotify.com/api/token', 
			data={'grant_type':'client_credentials'}, 
			headers={'Authorization':'Basic ' + base64.b64encode(client_id + ':' +client_secret)}
		)
		self.token = token.json()['access_token']

	def _get_url_endpoint(self, url, base_url='https://api.spotify.com/v1/'):
		return url[len(base_url):]

	def _get_header(self, header_data=None):
		auth_header = {'Authorization': 'Bearer ' + self.token}
		if header_data is not None:
			auth_header.update(header_data)
		return auth_header

	def _get_url(self, endpoint, version='v1'):
		return u'https://api.spotify.com/{version}/{endpoint}'.format(
			version=version,
			endpoint=endpoint
		)

	def _handle_response(self, response):
		if response.status_code < 400:
			response = response.json()
			if 'limit' in response.keys():
				return self._page_through_response(response)
			else:
				return response
		if response.status_code == 400:
			raise SpotifyInvalidRequestError(response)
		if response.status_code == 401:
			self.assign_token()
			raise SpotifyAuthenticationError(response)
		if response.status_code == 404:
			raise SpotifyNotFoundError(response)
		if response.status_code == 429:
			raise SpotifyTimeoutError(response)
		if response.status_code >= 500:
			raise SpotifyInternalServerError(response)
		raise SpotifyException(response)

	def _page_through_response(self, response, debug=True):
		items = []
		items.extend(response['items'])
		while True:
			next_page = response['next']
			if next_page is None: 
				break
			next_page = self._get_url_endpoint(next_page)	
			response = self.get(next_page)
			if isinstance(response, dict):
				items.extend(response['items'])
			elif isinstance(response, list):
				items.extend(response)
				break
			else:
				print response
				raise Exception("Error while paging through response.  most recent page was not of type dict or list, or if dict it was missing an 'items' field")
		return items

	def _manage_ratelimit(self):
		now = time.time()
		if now - self.request_epoch < self.time_between_requests:
			time.sleep(self.time_between_requests)
		self.request_epoch = now

	def get_most_recent_request_address(self):
		return self.most_recent_request_address

	@handle_http_errors
	def get(self, endpoint, params=None):
		url = self._get_url(endpoint)
		print u"getting from {0}".format( url)
		self._manage_ratelimit()
		self.most_recent_request_address = endpoint
		r = requests.get(
			url,
			headers=self._get_header(),
			params=params)
		return self._handle_response(r)

	@handle_http_errors
	def post(self, endpoint, params=None, data=None):
		url = self._get_url(endpoint)
		print "posting to {}".format(url)
		self._manage_ratelimit()
		self.most_recent_request_address = endpoint
		r = requests.post(
			url,
			headers=self._get_header(),
			params=params,
			data=json.dumps(data))
		return self._handle_response(r)


	@staticmethod
	def parse_datestring(spotify_date):
		return datetime.datetime.strptime(spotify_date, "%Y-%m-%dT%H:%M:%SZ")

class SpotifyAuthAPI(SpotifyAPI):
	scope = " ".join([
		'user-library-read',
		'user-read-birthdate',
		'playlist-read-private',
		'user-read-private',
		'user-read-email',
		'playlist-modify-public',
		'playlist-modify-private',
		'user-follow-read'
	])

	def assign_token(self):
		try:
			self.token = pickle.load(open('spotify-token.pickle','rb'))
		except:
			self.get_token_flow()


	def get_token_flow(self):
		callback_url = self.config['SPOTIFY_CALLBACK_URL']
		client_id = self.config['SPOTIFY_CLIENT_ID']
		client_secret = self.config['SPOTIFY_CLIENT_SECRET']
		self.service = OAuth2Service(
			name='spotify',
			client_id=client_id,
			client_secret=client_secret,
			authorize_url='https://accounts.spotify.com/authorize',
			access_token_url='https://accounts.spotify.com/api/token',
			base_url='https://accounts.spotify.com')

		params = dict(
			scope=self.scope,
			response_type='code',
			redirect_uri=self.callback_url)
		
		url = self.service.get_authorize_url(**params)
		print "visit this link and copy the code parameter:\n{}".format(url)
		auth_code = raw_input("\n:")

		token = self.service.get_access_token(
			data={
				'code':auth_code,
				'grant_type':'authorization_code',
				'redirect_uri':self.callback_url
			},
			method='POST',
			headers={'Authorization': 'Basic ' + base64.b64encode(client_id + ":" + client_secret)},
			decoder=json.loads)
		pickle.dump(token, open('spotify-token.pickle','wb'))
		self.token = token
