

from fastapi import APIRouter

from .auth import AuthController
from .sse import SseController
from .task import TaskController
from .file import FileController
from .project import ProjectController



router = APIRouter(prefix="/api")
router.include_router(AuthController.create_router())
router.include_router(SseController.create_router())
router.include_router(TaskController.create_router())
