from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from analyzer import ExternalAuditEngine

app = FastAPI()

# Permite que o Lovable acesse a API sem bloqueio
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = ExternalAuditEngine()

@app.get("/")
def home():
    return {"status": "Online", "msg": "API de Auditoria Esportiva Pronta"}

@app.post("/api/scan")
async def start_scan(
    youtube_url: str = Form(...),
    client_name: str = Form("Cliente"),
    logo: UploadFile = File(...)
):
    # 1. Salvar Logo Temporariamente
    logo_path = f"temp_files/logo_{logo.filename}"
    with open(logo_path, "wb") as buffer:
        shutil.copyfileobj(logo.file, buffer)
    
    try:
        # 2. Baixar Vídeo e Dados
        video_path, metadata = engine.download_video_data(youtube_url)
        
        # 3. Analisar com IA
        results = engine.scan(video_path, logo_path, metadata)
        
        # 4. Limpar arquivos pesados
        if os.path.exists(video_path):
            os.remove(video_path)
        if os.path.exists(logo_path):
            os.remove(logo_path)

        return results
        
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
