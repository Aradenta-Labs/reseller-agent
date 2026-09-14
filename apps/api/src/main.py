from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.routes.health import router as health_router
from src.routes.parser import router as parser_router
from src.routes.scout import router as scout_router

app = FastAPI(
    title="Reseller AI Assistant API",
    description="Backend services for item parsing, market research, and agent orchestration.",
    version="0.1.0",
)

# CORS configuration allowing Next.js frontend on localhost:3000
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include API routers
app.include_router(health_router)
app.include_router(parser_router)
app.include_router(scout_router)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Custom exception handler for validation value errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc)},
    )
