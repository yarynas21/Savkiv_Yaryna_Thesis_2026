"""
Service layer — pure business logic.

Modules here know about ``db.repositories`` and ``graph.registry`` but
deliberately have NO FastAPI / HTTP concerns. Routers depend on services,
services never depend on routers.
"""
