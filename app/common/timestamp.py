from datetime import datetime
class Timestamp(object):
	def __init__(self):
		self.epoch_timestamp = self.epoch_from_datetime(datetime.now())
	
	def epoch_from_datetime(self, datetime_obj):
		"""converts datetime object to epoch"""
		epoch = datetime.utcfromtimestamp(0)
		delta = datetime_obj - epoch
		return delta.total_seconds()

	def get_as_epoch(self):
		return self.epoch_timestamp

	def get_as_datetime(self):
		return datetime.utcfromtimestamp(self.epoch_timestamp)

	def get_as_str(self, pattern='%Y-%m-%d'):
		return self.get_as_datetime().strftime(pattern)
