




from config import settings

SECRET = settings.secret

class Config:
	access_token_lifetime = 60 * 10
	refresh_token_lifetime = 3600 * 24 * 30
	login_gap = 20
	ip_buffer = 10
	ip_buffer_lifetime = 60*60*24
	algorithm = "HS256"
	websocket_polling_interval = 1
	websocket_max_iterations = 60 * 60 / websocket_polling_interval
	redis_task_status_lifetime = 60 * 10
	minio_url_live_time = 10*60