




from config import settings

SECRET = settings.secret

class Config:
	access_token_lifetime = 60 * 10
	refresh_token_lifetime = 3600 * 24 * 30
	login_gap = 20
	ip_buffer = 10
	ip_buffer_lifetime = 60*60*24
	algorithm = "HS256"
	redis_task_polling_time = 1
	redis_task_status_lifetime = 60 * 10
	minio_url_live_time = 10*60