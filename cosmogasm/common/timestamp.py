from datetime import datetime

class TimestampError(Exception):
	pass

class Timestamp(object):
	def __init__(self, datetime_arg=None):
		if isinstance(datetime_arg, datetime):
			self.epoch_timestamp = self.epoch_from_datetime(datetime_arg)
		elif isinstance(datetime_arg, float):
			self.epoch_timestamp = datetime_arg
		elif datetime_arg is None:
			self.epoch_timestamp = self.epoch_from_datetime(datetime.now())
		else:
			raise TimestampError("Could not coerce argument {} to timestamp epoch".format(datetime_arg))
	
	@staticmethod
	def epoch_from_datetime(datetime_obj):
		"""converts datetime object to epoch"""
		epoch = datetime.utcfromtimestamp(0)
		delta = datetime_obj - epoch
		return delta.total_seconds()

	def as_epoch(self):
		return self.epoch_timestamp

	@staticmethod
	def from_epoch(epoch):
		return Timestamp(datetime.utcfromtimestamp(epoch))

	def as_datetime(self):
		return datetime.utcfromtimestamp(self.epoch_timestamp)

	def as_str(self, pattern='%Y-%m-%d'):
		return self.as_datetime().strftime(pattern)

	
