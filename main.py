from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
import re
import requests
from analyzer import ExternalAuditEngine

app = FastAPI()

app.add_middleware(
CORSMiddleware,
allow_origins=[""],
allow_methods=[""],
allow_headers=["*"],
)

engine = ExternalAuditEngine()

YOUTUBE_API_KEY = os.getenv("AIzaSyAatUA_kZsJFNhxr2Ie_lpuAErynj7bbzM","")
def extract_video_id(url: str) -> str:
"""
Extrai o ID do vídeo de URLs comuns do YouTube.
Ex: https://www.youtube.com/watch?v=ABC123  -> ABC123
"""
# Padrões comuns
patterns = [
r"v=([^&]+)",               # watch?v=ID
r"youtu.be/([^?&]+)",      # youtu.be/ID
r"youtube.com/embed/([^?&]+)",
]
for p in patterns:
m = re.search(p, url)
if m:
return m.group(1)
return url  # fallback: se já vier só o ID

def parse_iso8601_duration(duration_str: str) -> int:
"""
Converte duração ISO8601 (PT10M15S) para segundos inteiros.
"""
if not duration_str:
return 0

pattern = re.compile(
    r"PT"
    r"(?:(\d+)H)?"
    r"(?:(\d+)M)?"
    r"(?:(\d+)S)?"
)
match = pattern.fullmatch(duration_str)
if not match:
    return 0

hours = int(match.group(1) or 0)
minutes = int(match.group(2) or 0)
seconds = int(match.group(3) or 0)
return hours * 3600 + minutes * 60 + seconds
def fetch_youtube_metadata(youtube_url: str) -> dict:
"""
Usa YouTube Data API v3 para buscar título, canal, views e duração.
"""
if not YOUTUBE_API_KEY:
# Sem chave, devolve metadados mínimos
return {
"title": youtube_url,
"channel": "Desconhecido",
"view_count": 0,
"duration": 0,
}
video_id = extract_video_id(youtube_url)

params = {
    "id": video_id,
    "key": AIzaSyAatUA_kZsJFNhxr2Ie_lpuAErynj7bbzM,
    "part": "snippet,contentDetails,statistics",
}

resp = requests.get("https://www.googleapis.com/youtube/v3/videos", params=params, timeout=10)
if resp.status_code != 200:
    return {
        "title": youtube_url,
        "channel": "Desconhecido",
        "view_count": 0,
        "duration": 0,
    }

data = resp.json()
items = data.get("items", [])
if not items:
    return {
        "title": youtube_url,
        "channel": "Desconhecido",
        "view_count": 0,
        "duration": 0,
    }

item = items[0]
snippet = item.get("snippet", {})
stats = item.get("statistics", {})
content = item.get("contentDetails", {})

title = snippet.get("title")
channel = snippet.get("channelTitle")
view_count = int(stats.get("viewCount", 0))
duration_iso = content.get("duration")
duration_seconds = parse_iso8601_duration(duration_iso)

return {
    "title": title,
    "channel": channel,
    "view_count": view_count,
    "duration": duration_seconds,
}

@app.get("/")
def home():
return {"status": "Online", "msg": "API de Auditoria Esportiva Pronta"}

@app.post("/api/scan")
async def scan_hybrid(
youtube_url: str = Form(...),
client_name: str = Form("Cliente"),
video: UploadFile = File(...),
logo: UploadFile = File(...),
):
os.makedirs("temp_files", exist_ok=True)

video_path = f"temp_files/video_{video.filename}"
logo_path = f"temp_files/logo_{logo.filename}"

with open(video_path, "wb") as buffer:
    shutil.copyfileobj(video.file, buffer)

with open(logo_path, "wb") as buffer:
    shutil.copyfileobj(logo.file, buffer)

try:
    metadata = fetch_youtube_metadata(youtube_url)
    results = engine.scan(video_path, logo_path, metadata)

    if os.path.exists(video_path):
        os.remove(video_path)
    if os.path.exists(logo_path):
        os.remove(logo_path)

    # Adiciona a URL original e cliente para referência
    results["youtube_url"] = youtube_url
    results["client"] = client_name

    return results

except Exception as e:
    return {"error": str(e)}
if name == "main":
import uvicorn
uvicorn.run(app, host="0.0.0.0", port=8000)




