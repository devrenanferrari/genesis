import os
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import openai
from supabase import create_client
import tempfile
import zipfile
import json

# =========================
# Variáveis de ambiente
# =========================
openai.api_key = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

origins = [
    "http://localhost:3000",
    "https://genesis-k2ykslrzq-devrenanferraris-projects.vercel.app",
    "https://genesis-swart-nu.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenRequest(BaseModel):
    user_id: str | None = None
    prompt: str

# =========================
# Endpoint principal
# =========================
@app.post("/generate_project")
def generate_project(req: GenRequest):
    try:
        # Cria usuário demo se não existir
        if not req.user_id:
            req.user_id = str(uuid.uuid4())
            supabase.table("users").insert({
                "id": req.user_id,
                "email": f"demo-{req.user_id}@example.com",
                "plan": "demo"
            }).execute()

        # Solicita ao LLM os arquivos separados do projeto
        system_msg = (
            "Você é um gerador de projetos completos. "
            "Crie os arquivos do projeto separados, indicando o nome de cada arquivo e seu conteúdo em JSON. "
            "Exemplo de resposta JSON: {\"App.js\": \"conteúdo do App.js\", \"index.html\": \"conteúdo do index.html\"} "
            "Inclua também um README.md explicando o projeto."
        )
        response = openai.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": req.prompt}
            ],
            temperature=0.2,
            max_tokens=4000
        )

        # Extrai resposta do LLM
        content = response.choices[0].message.content

        # Tenta converter em JSON
        try:
            files = json.loads(content)
        except Exception:
            # Se falhar, coloca tudo em App.js
            files = {"App.js": content, "README.md": f"# Projeto: {req.prompt}"}

        # Salva no Supabase
        supabase.table("projects").insert({
            "user_id": req.user_id,
            "prompt": req.prompt,
            "llm_output": content
        }).execute()

        # Cria ZIP
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        with zipfile.ZipFile(tmp.name, "w") as zipf:
            for fname, fcontent in files.items():
                zipf.writestr(fname, fcontent)

        return JSONResponse({"user_id": req.user_id, "llm_output": content, "project_zip_url": tmp.name, "files": files})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no backend: {str(e)}")
