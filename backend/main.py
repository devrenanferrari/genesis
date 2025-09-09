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

class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    email: str
    password: str

class GenRequest(BaseModel):
    user_id: str | None = None
    prompt: str

@app.post("/auth/login")
def login(req: LoginRequest):
    try:
        response = supabase.auth.sign_in_with_password({
            "email": req.email,
            "password": req.password
        })
        
        if response.user:
            return JSONResponse({
                "success": True,
                "user": {
                    "id": response.user.id,
                    "email": response.user.email
                },
                "session": response.session.access_token if response.session else None
            })
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
            
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Login failed: {str(e)}")

@app.post("/auth/signup")
def signup(req: SignupRequest):
    try:
        response = supabase.auth.sign_up({
            "email": req.email,
            "password": req.password
        })
        
        if response.user:
            # Insert user into our users table
            supabase.table("users").insert({
                "id": response.user.id,
                "email": req.email,
                "plan": "free"
            }).execute()
            
            return JSONResponse({
                "success": True,
                "user": {
                    "id": response.user.id,
                    "email": response.user.email
                }
            })
        else:
            raise HTTPException(status_code=400, detail="Signup failed")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Signup failed: {str(e)}")

@app.get("/auth/user/{user_id}")
def get_user(user_id: str):
    try:
        response = supabase.table("users").select("*").eq("id", user_id).execute()
        if response.data:
            return JSONResponse({"user": response.data[0]})
        else:
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user: {str(e)}")

@app.get("/projects/{user_id}")
def get_user_projects(user_id: str):
    try:
        response = supabase.table("projects").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        return JSONResponse({"projects": response.data})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching projects: {str(e)}")

# =========================
# Endpoint principal
# =========================
@app.post("/generate_project")
def generate_project(req: GenRequest):
    try:
        if not req.user_id:
            raise HTTPException(status_code=401, detail="User ID required")

        # Solicita ao LLM os arquivos separados do projeto
        system_msg = (
            "Você é um gerador de projetos completos. "
            "Crie os arquivos do projeto separados, indicando o nome de cada arquivo e seu conteúdo em JSON. "
            "Exemplo de resposta JSON: {\"App.js\": \"conteúdo do App.js\", \"index.html\": \"conteúdo do index.html\"} "
            "Inclua também um README.md explicando o projeto."
        )
        response = openai.chat.completions.create(
            model="gpt-4o",
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
