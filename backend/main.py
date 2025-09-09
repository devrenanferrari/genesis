import os
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pathlib import Path
import json

app = FastAPI()

# =========================
# CORS aberto para qualquer IP
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Models
# =========================
class FileInput(BaseModel):
    user_id: str
    project: str
    files: dict  # {"App.ts": "codigo", "pastatal/arquivo.ts": "codigo"}

# =========================
# Endpoint para criar arquivos
# =========================
@app.post("/create_project_files")
def create_project_files(data: FileInput):
    try:
        user_uuid = data.user_id
        project_name = data.project

        # Caminho base
        base_path = Path("containers") / user_uuid / project_name / "root"
        base_path.mkdir(parents=True, exist_ok=True)

        # Cria arquivos
        for file_path, content in data.files.items():
            full_path = base_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)  # cria pastas necessárias
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

        return {"success": True, "path": str(base_path), "files_created": list(data.files.keys())}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar arquivos: {str(e)}")

# =========================
# Endpoint de teste simples
# =========================
@app.get("/")
def root():
    return {"message": "API rodando!"}
