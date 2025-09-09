import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import JSONResponse

# =========================
# FastAPI
# =========================
app = FastAPI()

# Aceita requisições de qualquer IP/origem
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # permite qualquer origem
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Models
# =========================
class FileDict(BaseModel):
    __root__: dict[str, str]

class GenerateProjectRequest(BaseModel):
    user_id: str
    project: str
    files: FileDict

# =========================
# Endpoint
# =========================
@app.post("/create_project")
def create_project(req: GenerateProjectRequest):
    try:
        base_path = os.path.join("containers", req.user_id, req.project, "root")
        os.makedirs(base_path, exist_ok=True)

        for filepath, content in req.files.__root__.items():
            full_path = os.path.join(base_path, filepath)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

        return JSONResponse({
            "success": True,
            "message": f"Projeto '{req.project}' criado com sucesso em {base_path}"
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar projeto: {str(e)}")
