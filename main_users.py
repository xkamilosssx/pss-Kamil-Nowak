import os
import json
import threading
from typing import List
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# ===== Load .env =====
load_dotenv()
API_KEY = os.getenv("API_KEY", "defaultsecret")

# ===== Plik bazy danych =====
USERS_FILE = os.path.join(os.path.dirname(__file__), "data_users.json")
LOCK_USERS = threading.Lock()

# ===== Funkcje bazy danych =====
def load_users_db():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({"users": [], "next_id": 1}, f, indent=2)
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users_db(db):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)

# ===== Modele danych =====
class UserIn(BaseModel):
    name: str
    email: str
    roles: List[str] = []

class UserOut(UserIn):
    id: int

# ===== FastAPI app =====
app = FastAPI(
    title="LAB02 - FastAPI /users CRUD",
    description="Prosty CRUD /users z data_users.json i zabezpieczeniem API-Key",
    version="0.1.0"
)

# ===== Middleware dla API-Key =====
@app.middleware("http")
async def api_key_guard(request: Request, call_next):
    if request.url.path.startswith("/users"):
        provided = request.headers.get("X-API-Key")
        if provided != API_KEY:
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized (missing/invalid X-API-Key)"}
            )
    return await call_next(request)

# ===== Endpointy CRUD =====
@app.get("/users", response_model=List[UserOut])
def list_users():
    db = load_users_db()
    return db["users"]

@app.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int):
    db = load_users_db()
    for u in db["users"]:
        if u["id"] == user_id:
            return u
    raise HTTPException(status_code=404, detail="User not found")

@app.post("/users", response_model=UserOut, status_code=200)
def create_user(user: UserIn):
    with LOCK_USERS:
        db = load_users_db()
        new_id = db.get("next_id", 1)
        rec = {"id": new_id, **user.dict()}
        db["users"].append(rec)
        db["next_id"] = new_id + 1
        save_users_db(db)
        return rec

@app.put("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, user: UserIn):
    with LOCK_USERS:
        db = load_users_db()
        for i, u in enumerate(db["users"]):
            if u["id"] == user_id:
                updated = {"id": user_id, **user.dict()}
                db["users"][i] = updated
                save_users_db(db)
                return updated
    raise HTTPException(status_code=404, detail="User not found")

@app.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int):
    with LOCK_USERS:
        db = load_users_db()
        for i, u in enumerate(db["users"]):
            if u["id"] == user_id:
                db["users"].pop(i)
                save_users_db(db)
                return
    raise HTTPException(status_code=404, detail="User not found")
