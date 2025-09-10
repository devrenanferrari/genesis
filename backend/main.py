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
GITHUB_REPO = os.getenv("GITHUB_REPO")  # ex: username/genesis-projects
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
VERCEL_TOKEN = os.getenv("VERCEL_TOKEN")

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
class FileInput(BaseModel):
    user_id: str
    project: str
    files: dict  # {"App.ts": "codigo", "pastatal/arquivo.ts": "codigo"}

class DeployInput(BaseModel):
    user_id: str
    project: str

# =========================
# Endpoint criar arquivos e subir GitHub
# =========================
@app.post("/create_project_files")
def create_project_files(data: FileInput):
    try:
        # Cria arquivos localmente
        base_path = Path("containers") / data.user_id / data.project / "root"
        base_path.mkdir(parents=True, exist_ok=True)
        for file_path, content in data.files.items():
            full_path = base_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

        # GitHub commit
        tree_elements = []
        for file_path, content in data.files.items():
            git_path = f"containers/{data.user_id}/{data.project}/{file_path}"
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
            "path": str(base_path),
            "files_created": list(data.files.keys()),
            "github_commit_url": f"https://github.com/{GITHUB_REPO}/commit/{commit.sha}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar arquivos: {str(e)}")

# =========================
# Endpoint para deploy na Vercel
# =========================
@app.post("/deploy_project")
def deploy_project(data: DeployInput):
    try:
        deploy_url = "https://api.vercel.com/v13/deployments"
        headers = {
            "Authorization": f"Bearer {VERCEL_TOKEN}",
            "Content-Type": "application/json"
        }

        body = {
            "name": f"{data.project}-{data.user_id[:6]}",  # nome único
            "gitSource": {
                "type": "github",
                "repo": GITHUB_REPO,
                "ref": GITHUB_BRANCH,
                "path": f"containers/{data.user_id}/{data.project}"
            }
        }

        response = requests.post(deploy_url, headers=headers, json=body)

        if response.status_code != 200:
            raise HTTPException(status_code=500, detail=f"Erro Vercel: {response.text}")

        result = response.json()
        preview_url = f"https://{result['url']}"

        # Salva no Supabase (opcional)
        supabase.table("projects").insert({
            "user_id": data.user_id,
            "project": data.project,
            "vercel_url": preview_url
        }).execute()

        return {
            "success": True,
            "vercel_preview_url": preview_url,
            "deployment_id": result["id"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no deploy: {str(e)}")
