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

@app.get("/")
def root():
    return {"message": "Genesis API is running", "status": "ok"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "openai_configured": bool(openai.api_key), "supabase_configured": bool(SUPABASE_URL and SUPABASE_KEY)}

@app.post("/auth/login")
def login(req: LoginRequest):
    try:
        response = supabase.auth.sign_in_with_password(
            email=req.email,
            password=req.password
        )
        
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
        print(f"Login error: {str(e)}")  # Added debug logging
        raise HTTPException(status_code=401, detail=f"Login failed: {str(e)}")

@app.post("/auth/signup")
def signup(req: SignupRequest):
    try:
        response = supabase.auth.sign_up(
            email=req.email,
            password=req.password
        )
        
        if response.user:
            try:
                supabase.table("users").insert({
                    "id": response.user.id,
                    "email": req.email,
                    "plan": "free"
                }).execute()
            except Exception as db_error:
                print(f"Database insert error: {str(db_error)}")
                # Continue even if user table insert fails
            
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
        print(f"Signup error: {str(e)}")  # Added debug logging
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
        print(f"[DEBUG] Received request: user_id={req.user_id}, prompt={req.prompt[:50]}...")  # Added debug logging
        
        if not req.user_id:
            raise HTTPException(status_code=401, detail="User ID required")

        if not openai.api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")

        # Solicita ao LLM os arquivos separados do projeto
        system_msg = (
            "Você é um gerador de projetos completos. "
            "Crie os arquivos do projeto separados, indicando o nome de cada arquivo e seu conteúdo em JSON. "
            "Exemplo de resposta JSON: {\"App.js\": \"conteúdo do App.js\", \"index.html\": \"conteúdo do index.html\"} "
            "Inclua também um README.md explicando o projeto."
        )
        
        print("[DEBUG] Calling OpenAI API...")  # Added debug logging
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
        print(f"[DEBUG] OpenAI response received, length: {len(content)}")  # Added debug logging

        # Tenta converter em JSON
        try:
            files = json.loads(content)
            print(f"[DEBUG] Successfully parsed JSON with {len(files)} files")  # Added debug logging
        except Exception as json_error:
            print(f"[DEBUG] JSON parsing failed: {json_error}")  # Added debug logging
            # Se falhar, coloca tudo em App.js
            files = {"App.js": content, "README.md": f"# Projeto: {req.prompt}"}

        try:
            print("[DEBUG] Saving to Supabase...")
            supabase.table("projects").insert({
                "user_id": req.user_id,
                "prompt": req.prompt,
                "llm_output": content
            }).execute()
            print("[DEBUG] Successfully saved to Supabase")
        except Exception as db_error:
            print(f"[DEBUG] Supabase error: {db_error}")
            # Continue even if database save fails

        # Cria ZIP
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        with zipfile.ZipFile(tmp.name, "w") as zipf:
            for fname, fcontent in files.items():
                zipf.writestr(fname, fcontent)

        print(f"[DEBUG] Successfully generated project with {len(files)} files")  # Added debug logging
        return JSONResponse({"user_id": req.user_id, "llm_output": content, "project_zip_url": tmp.name, "files": files})

    except Exception as e:
        print(f"[ERROR] generate_project failed: {str(e)}")  # Added error logging
        raise HTTPException(status_code=500, detail=f"Erro no backend: {str(e)}")

@app.post("/generate")
def generate(req: GenRequest):
    return generate_project(req)
