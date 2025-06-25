from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import time
import os

app = FastAPI()

# Foydalanuvchilar uchun oddiy login ma'lumotlari (hardcoded)
USERS = {
    "umidjon": "dinu",
    "dilnavoz": "dinu"
}

# Oxirgi faollikni saqlash (user: timestamp)
last_active = {
    "umidjon": None,
    "dilnavoz": None
}

# WebSocket orqali ulangan mijozlar
connections = {}

# Rasm yuklash papkasi
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Login uchun oddiy API
@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    if username.lower() in USERS and USERS[username.lower()] == password:
        return {"success": True, "username": username.lower()}
    raise HTTPException(status_code=400, detail="Login yoki parol noto‘g‘ri")

# Rasm upload qilish endpointi
@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    filename = f"{int(time.time())}_{file.filename}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)
    return {"filename": filename, "url": f"/uploads/{filename}"}

# Static fayllar uchun
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")


chat_history = []
CHAT_HISTORY_FILE = "chat_history.txt"

def load_chat_history():
    if os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    msg = eval(line.strip())
                    chat_history.append(msg)
                except:
                    continue

def append_to_history_file(msg):
    with open(CHAT_HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(repr(msg) + "\n")

load_chat_history()

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await websocket.accept()
    connections[username] = websocket
    last_active[username] = True

    # Send chat history to new connection
    for msg in chat_history:
        await websocket.send_json(msg)

    try:
        while True:
            data = await websocket.receive_json()
            last_active[username] = True

            user_label = "Umidjon" if username == "umidjon" else "Dilnavoz"

            msg = {
                "from": user_label,
                "type": data.get("type"),
                "content": data.get("content"),
                "timestamp": int(time.time()),
                "last_active": last_active
            }

            # Append to history and limit size
            chat_history.append(msg)
            append_to_history_file(msg)
            if len(chat_history) > 100:
                chat_history.pop(0)

            # Broadcast message to all connections
            for user, conn in connections.items():
                await conn.send_json(msg)
    except WebSocketDisconnect:
        del connections[username]
        last_active[username] = time.time()

# Frontendni taqdim etish
FRONTEND_PATH = "./index.html"

@app.get("/")
async def get_index():
    return FileResponse(FRONTEND_PATH)