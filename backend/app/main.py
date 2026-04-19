import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import cameras, config, enrollment, faces, production_recognition, recognition
from app.core.database import init_db
from app.services.camera_service import stop_camera_runtime
from app.services.detection_loop import detection_loop
from app.services.hls_gateway_service import stop_all_hls_sessions
from app.services.network_camera_pool_service import stop_network_camera_pool


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    detection_loop.start()
    try:
        yield
    finally:
        detection_loop.stop()
        stop_camera_runtime()
        stop_network_camera_pool()
        stop_all_hls_sessions()


def create_app() -> FastAPI:
    app = FastAPI(title="Face Recognition API", lifespan=lifespan)

    frontend_origins = os.getenv("FRONTEND_ORIGINS")
    if not frontend_origins:
        legacy_frontend_origin = os.getenv("FRONTEND_ORIGIN")
        if legacy_frontend_origin:
            frontend_origins = legacy_frontend_origin
        else:
            frontend_origins = "http://localhost:5173,http://127.0.0.1:5173"
    allow_origins = [origin.strip() for origin in frontend_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["content-type", "authorization", "x-api-key", "x-admin-api-key"],
    )


    app.include_router(config.router, prefix="/api")
    app.include_router(faces.router, prefix="/api")
    app.include_router(enrollment.router, prefix="/api")
    app.include_router(recognition.router, prefix="/api")
    app.include_router(production_recognition.router, prefix="/api")
    app.include_router(cameras.router, prefix="/api")

    # Ajout du router admin batch logs
    from app.api.routes import admin_batch_logs
    app.include_router(admin_batch_logs.router, prefix="/api")

    from app.api.routes import auth
    app.include_router(auth.router, prefix="/api")
    # Affiche un avertissement si le serveur écoute sur 0.0.0.0 en dehors du dev
    if not os.getenv("DEV_MODE") and ("--host" not in sys.argv or "0.0.0.0" in sys.argv):
        print("[SECURITE] Pour la production, lancez FastAPI avec --host 127.0.0.1 ou placez un reverse proxy devant.")
    return app


app = create_app()
