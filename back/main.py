from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth
from app.api import conversations
from app.api import user
from app.api import analyze  

from app.core.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Existing routes =====
app.include_router(auth.router)
app.include_router(conversations.router)
app.include_router(user.router)

# ===== NEW analyze route =====
app.include_router(analyze.router)

@app.get("/")
def health():
    return {"status": "ok"}
