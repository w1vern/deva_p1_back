
from deva_p1_db.database import DatabaseSessionManager, get_db_url

from config import settings

session_manager = DatabaseSessionManager(get_db_url(settings.db_user,
                                                    settings.db_password,
                                                    settings.db_ip,
                                                    settings.db_port,
                                                    settings.db_name),
                                         {"echo": False})
