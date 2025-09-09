import os
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from github import Github, InputGitTreeElement

# =========================
# Variáveis de ambiente
# =========================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")  # ex: "username/genesis-projects"
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

if not GITHUB_TOKEN or not GITHUB_REPO:
    raise Exception("GITHUB_TOKEN e GITHUB_REPO precisam estar definidos como variáveis de ambiente")

gh = Github(GITHUB_TOKEN)
repo = gh.get_repo(GITHUB_REPO)

# =========================
# FastAPI setup
# =========================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # permite qualquer IP
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
# Endpoint principal
# =========================
@app.post("/create_project_files")
def create_project_files(data: FileInput):
    try:
        user_uuid = data.user_id
        project_name = data.project

        # Caminho local temporário
        base_path = Path("containers") / user_uuid / project_name / "root"
        base_path.mkdir(parents=True, exist_ok=True)

        # Cria arquivos localmente
        for file_path, content in data.files.items():
            full_path = base_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

        # =========================
        # Subindo para GitHub
        # =========================
        tree_elements = []
        for file_path, content in data.files.items():
            git_path = f"{user_uuid}/{project_name}/root/{file_path}"
            tree_elements.append(InputGitTreeElement(git_path, "100644", "blob", content))

        # Pega último commit
        master_ref = repo.get_branch(GITHUB_BRANCH)
        base_tree = repo.get_git_tree(master_ref.commit.sha)
        tree = repo.create_git_tree(tree_elements, base_tree)
        parent = repo.get_git_commit(master_ref.commit.sha)
        commit_message = f"Add project {project_name} for user {user_uuid}"
        commit = repo.create_git_commit(commit_message, tree, [parent])
        master_ref.edit(commit.sha)

        return {
            "success": True,
            "path": str(base_path),
            "files_created": list(data.files.keys()),
            "github_commit_url": f"https://github.com/{GITHUB_REPO}/commit/{commit.sha}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar arquivos: {str(e)}")
