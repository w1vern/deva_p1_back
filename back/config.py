




from config import settings

SECRET = settings.secret

class Config:
	access_token_lifetime = 60 * 10
	refresh_token_lifetime = 3600 * 24 * 30
	login_gap = 20
	ip_buffer = 10
	ip_buffer_lifetime = 60*60*24
	algorithm = "HS256"
	redis_pubsub_check_time = 0.5
	redis_pubsub_check_timeout = 1