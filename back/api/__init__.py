

from fastapi import APIRouter

from .auth import AuthController
from .file import FileController
from .project import ProjectController
from .task import TaskController

router = APIRouter(prefix="/api")
router.include_router(AuthController.create_router())
router.include_router(TaskController.create_router())
router.include_router(FileController.create_router())
router.include_router(ProjectController.create_router())
