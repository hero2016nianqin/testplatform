from fastapi import FastAPI


def register_routers(app: FastAPI):
    from app.routers.auth import router as auth_router
    from app.routers.station import router as station_router
    from app.routers.test import router as test_router
    from app.routers.version import router as version_router
    from app.routers.log import router as log_router
    from app.routers.init import router as init_router
    from app.routers.ws_router import router as ws_router
    from app.routers.xxl_job import router as xxl_job_router
    from app.routers.metrics import router as metrics_router

    # Import models so SQLAlchemy Base.metadata includes them
    from app.models.user import User
    from app.models.registration import AccountRegistration
    from app.models.permission import UserDomain, AuditLog
    from app.models.metrics import (
        IndicatorDict, TestItemIndicator, TestItemCollection, CollectionTestItem,
        BomConfig, BomIndicator, BomDomainOwner, ParamChangeLog,
    )

    app.include_router(auth_router, prefix="/api/v1/auth")
    app.include_router(station_router, prefix="/api/v1/stations")
    app.include_router(test_router, prefix="/api/v1/tests")
    app.include_router(version_router, prefix="/api/v1/versions")
    app.include_router(log_router, prefix="/api/v1/logs")
    app.include_router(init_router, prefix="/api/v1/init")
    app.include_router(ws_router)
    app.include_router(xxl_job_router, prefix="/api/v1")
    app.include_router(metrics_router, prefix="/api/v1/metrics")

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok"}
