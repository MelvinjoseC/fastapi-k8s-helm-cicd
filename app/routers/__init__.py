"""FastAPI routers for modular request handling."""
from routers.health import router as health_router
from routers.tasks import router as tasks_router

__all__ = ["health_router", "tasks_router"]
