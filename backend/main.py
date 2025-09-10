import os
import uuid
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
from supabase import create_client
from github import Github, InputGitTreeElement
import requests

# =========================
# Variáveis de ambiente
# =========================
openai.api_key = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")  # ex: devrenanferrari/genesis
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
VERCEL_TOKEN = os.getenv("VERCEL_TOKEN")
VERCEL_TEAM_ID = os.getenv("VERCEL_TEAM_ID")  # ex: team_xxxxxxxx

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
gh = Github(GITHUB_TOKEN)
repo = gh.get_repo(GITHUB_REPO)

# =========================
# FastAPI setup
# =========================
app = FastAPI()
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
class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    email: str
    password: str

class GenRequest(BaseModel):
    user_id: str
    prompt: str

class FileInput(BaseModel):
    user_id: str
    project: str
    files: dict

class DeployRequest(BaseModel):
    user_id: str
    project: str
    repo: str  # ex: "devrenanferrari/genesis"

# =========================
# Endpoints Supabase
# =========================
@app.post("/auth/login")
def login(req: LoginRequest):
    try:
        response = supabase.auth.sign_in_with_password({
            "email": req.email,
            "password": req.password
        })
        if response.user:
            return {"success": True, "user": {"id": response.user.id, "email": response.user.email}}
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/auth/signup")
def signup(req: SignupRequest):
    try:
        response = supabase.auth.sign_up({"email": req.email, "password": req.password})
        if response.user:
            supabase.table("users").insert({
                "id": response.user.id,
                "email": req.email,
                "plan": "free"
            }).execute()
            return {"success": True, "user": {"id": response.user.id, "email": req.email}}
        else:
            raise HTTPException(status_code=400, detail="Signup failed")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =========================
# Endpoint gerar projeto via OpenAI
# =========================
@app.post("/generate_project")
def generate_project(req: GenRequest):
    try:
        system_msg = (
            "Você é um gerador de projetos completos. "
            "Crie arquivos separados, em JSON, incluindo README.md."
        )
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role":"system","content":system_msg},{"role":"user","content":req.prompt}],
            temperature=0.2,
            max_tokens=4000
        )
        content = response.choices[0].message.content
        try:
            files = json.loads(content)
        except:
            files = {"App.js": content, "README.md": f"# Projeto: {req.prompt}"}

        project_uuid = str(uuid.uuid4())
        base_path = Path("containers") / project_uuid / req.user_id / req.prompt
        base_path.mkdir(parents=True, exist_ok=True)

        for fname, fcontent in files.items():
            fpath = base_path / fname
            fpath.parent.mkdir(parents=True, exist_ok=True)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(fcontent)

        return {"success": True, "files": list(files.keys()), "path": str(base_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# Endpoint criar arquivos e subir GitHub
# =========================
@app.post("/create_project_files")
def create_project_files(data: FileInput):
    try:
        project_uuid = str(uuid.uuid4())
        base_path = Path("containers") / project_uuid / data.project
        base_path.mkdir(parents=True, exist_ok=True)

        for file_path, content in data.files.items():
            full_path = base_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

        tree_elements = []
        for file_path, content in data.files.items():
            git_path = f"{data.project}/{file_path}"
            tree_elements.append(InputGitTreeElement(git_path, "100644", "blob", content))

        ref = repo.get_git_ref(f"heads/{GITHUB_BRANCH}")
        base_tree = repo.get_git_tree(ref.object.sha)
        tree = repo.create_git_tree(tree_elements, base_tree)
        parent = repo.get_git_commit(ref.object.sha)
        commit = repo.create_git_commit(
            f"Add project {data.project} for user {data.user_id}", tree, [parent]
        )
        ref.edit(commit.sha)

        return {
            "success": True,
            "uuid": project_uuid,
            "path": str(base_path),
            "files_created": list(data.files.keys()),
            "github_commit_url": f"https://github.com/{GITHUB_REPO}/commit/{commit.sha}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar arquivos: {str(e)}")

# =========================
# Endpoint deploy na Vercel
# =========================
@app.post("/deploy_project")
def deploy_project(data: DeployRequest):
    try:
        url = "https://api.vercel.com/v13/deployments"
        if VERCEL_TEAM_ID:
            url += f"?teamId={VERCEL_TEAM_ID}"

        headers = {"Authorization": f"Bearer {VERCEL_TOKEN}", "Content-Type": "application/json"}
        
        payload = {
            "name": data.project,
            "gitSource": {
                "type": "github",
                "org": data.repo.split("/")[0],
                "repo": data.repo.split("/")[1],
                "ref": GITHUB_BRANCH
            }
        }

        r = requests.post(url, headers=headers, data=json.dumps(payload))
        if r.status_code not in (200, 201):
            raise HTTPException(status_code=r.status_code, detail=r.text)

        return {"success": True, "vercel_response": r.json()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
