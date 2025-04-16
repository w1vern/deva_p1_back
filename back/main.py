from typing import Annotated
from fastapi import Depends, FastAPI

from back.api import router
from back.broker import router as faststream_router

from deva_p1_db.database import DatabaseSessionManager, get_db_url
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings

session_manager = DatabaseSessionManager(get_db_url(settings.db_user,
                                                    settings.db_password,
                                                    settings.db_ip,
                                                    settings.db_port,
                                                    settings.db_name),
                                         {"echo": False})

Session = Annotated[AsyncSession, Depends(session_manager.session)]

app = FastAPI(docs_url="/api/docs", redoc_url="/api/redoc",
              openapi_url="/api/openapi.json")
app.include_router(router)
app.include_router(faststream_router)
