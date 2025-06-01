

from fastapi import APIRouter

from .auth import router as auth_router
from .file import router as file_router
from .note import router as note_router
from .project import router as project_router
from .task import router as task_router

router = APIRouter(prefix="/api")
router.include_router(auth_router)
router.include_router(file_router)
router.include_router(note_router)
router.include_router(project_router)
router.include_router(task_router)
