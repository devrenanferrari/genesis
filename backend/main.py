import os
import uuid
import json
import re
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import openai
from supabase import create_client
from github import Github, InputGitTreeElement
import requests

# =========================
# Constants / System Prompt
# =========================
GENESIS_SYSTEM_PROMPT = """
Core Identity

You are Genesis, an advanced AI model designed to help developers build, design, and deploy modern applications.

You are always updated with the latest technologies, frameworks, and best practices.

You communicate em MDX, com suporte a componentes customizados que permitem código interativo, diagramas, e documentação enriquecida.

Instructions

Genesis sempre sugere soluções modernas e produtivas.

Quando o usuário não especifica um framework, Genesis assume Next.js App Router como padrão.

Sempre organiza respostas de forma clara, com passo a passo, exemplos de código e boas práticas.

Responde em português por padrão, mas pode alternar idiomas conforme o usuário solicitar.

Available MDX Components
<CodeProject>

Agrupa arquivos e permite rodar projetos full-stack em React/Next.js.

Um único <CodeProject> por resposta.

Arquivos seguem kebab-case no nome.

Estilo padrão: Tailwind + shadcn/ui + Lucide Icons.

Exemplo:

<CodeProject id="genesis_project">

  tsx file="login-form.tsx"
  import { Button } from "@/components/ui/button"

  export default function LoginForm() {
    return (
      <div className="flex flex-col gap-4">
        <input className="border p-2 rounded" placeholder="Email" />
        <input className="border p-2 rounded" type="password" placeholder="Senha" />
        <Button>Entrar</Button>
      </div>
    )
  }

</CodeProject> 

Diagramas

Usa Mermaid para fluxos, processos e arquiteturas.

Sempre coloca nomes de nós entre aspas.

Usa UTF-8 codes para caracteres especiais.

Exemplo:

graph TD;
A["Usuário"] --> B["Formulário de Login"];
B --> C["API de Autenticação"];
C --> D["Banco de Dados"];

Node.js Executable

Usa js type="nodejs" para scripts backend interativos.

Sempre usa ES6+, import/export, fetch e console.log.

Markdown

Usa md type="markdown" para documentação (README, guias, etc).

Style Rules

Responsivo por padrão.

Evitar azul/índigo, a não ser quando o usuário pedir.

Sempre usar acessibilidade: alt em imagens, roles ARIA, e semantic HTML.

Códigos curtos podem vir inline, longos devem usar blocos de código.

Refusals

Se o usuário pedir algo violento, ilegal, sexual ou antiético, Genesis responde apenas:

I'm sorry. I'm not able to assist with that.

Suggested Actions

Genesis sempre sugere 3–5 próximos passos relevantes, dentro de <Actions> e <Action>.

Exemplo:

<Actions>
  <Action name="Adicionar autenticação" description="Criar fluxo de cadastro e login com Supabase" />
  <Action name="Implementar dark mode" description="Habilitar alternância entre tema claro e escuro" />
  <Action name="Gerar imagem hero" description="Criar imagem chamativa para página inicial" />
</Actions>
"""

def get_system_prompt(context: str = None) -> str:
    if context == "chat":
        return GENESIS_SYSTEM_PROMPT + "\n\nContexto: Chat geral com memória de sessão."
    elif context == "generate_project":
        return GENESIS_SYSTEM_PROMPT + "\n\nContexto: Gere projeto completo. JSON apenas."
    elif context == "regenerate_files":
        return GENESIS_SYSTEM_PROMPT + "\n\nContexto: Regere arquivos do projeto."
    else:
        return GENESIS_SYSTEM_PROMPT

# =========================
# Environment Variables
# =========================
openai.api_key = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
VERCEL_TOKEN = os.getenv("VERCEL_TOKEN")
VERCEL_TEAM_ID = os.getenv("VERCEL_TEAM_ID")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
gh = Github(GITHUB_TOKEN) if GITHUB_TOKEN else None
repo = gh.get_repo(GITHUB_REPO) if gh and GITHUB_REPO else None

# =========================
# FastAPI Setup
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

class StartSessionRequest(BaseModel):
    user_id: str
    name: Optional[str] = "Nova sessão"

class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    prompt: str
    max_history: Optional[int] = 50

class GenRequest(BaseModel):
    user_id: str
    session_id: str
    prompt: str

class FileInput(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    project: str
    files: dict

class DeployRequest(BaseModel):
    user_id: str
    project: str
    repo: str

class EditMessageRequest(BaseModel):
    message_id: str
    new_content: str

class EditFileRequest(BaseModel):
    file_id: str
    new_content: str

# =========================
# Helpers
# =========================
def normalize_project_name(name: str) -> str:
    name = name.lower()
    name = re.sub(r"[^a-z0-9_.-]", "_", name)
    return re.sub(r"_+", "_", name)[:100]

def save_files_to_disk(project_uuid: str, user_id: str, project_name: str, files: dict) -> str:
    base_path = Path("containers") / project_uuid / user_id / normalize_project_name(project_name)
    base_path.mkdir(parents=True, exist_ok=True)
    for fname, fcontent in files.items():
        fpath = base_path / fname
        fpath.parent.mkdir(parents=True, exist_ok=True)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(fcontent)
    return str(base_path)

def supabase_insert(table: str, rows):
    if not supabase:
        raise RuntimeError("Supabase client not initialized")
    res = supabase.table(table).insert(rows).execute()
    if hasattr(res, "error") and res.error:
        raise Exception(res.error.message if hasattr(res.error, "message") else str(res.error))
    return getattr(res, "data", res)

def supabase_select(table: str, filters: List[tuple] = None, order_by: Optional[str] = None, limit: Optional[int] = None):
    if not supabase:
        raise RuntimeError("Supabase client not initialized")
    q = supabase.table(table).select("*")
    if filters:
        for op, key, value in filters:
            q = getattr(q, op)(key, value)
    if order_by:
        q = q.order(order_by)
    if limit:
        q = q.limit(limit)
    res = q.execute()
    if hasattr(res, "error") and res.error:
        raise Exception(res.error.message if hasattr(res.error, "message") else str(res.error))
    return getattr(res, "data", res)

def supabase_update(table: str, changes: dict, filters: List[tuple]):
    if not supabase:
        raise RuntimeError("Supabase client not initialized")
    q = supabase.table(table).update(changes)
    for op, key, value in filters:
        q = getattr(q, op)(key, value)
    res = q.execute()
    if hasattr(res, "error") and res.error:
        raise Exception(res.error.message if hasattr(res.error, "message") else str(res.error))
    return getattr(res, "data", res)

def supabase_delete(table: str, filters: List[tuple]):
    if not supabase:
        raise RuntimeError("Supabase client not initialized")
    q = supabase.table(table).delete()
    for op, key, value in filters:
        q = getattr(q, op)(key, value)
    res = q.execute()
    if hasattr(res, "error") and res.error:
        raise Exception(res.error.message if hasattr(res.error, "message") else str(res.error))
    return getattr(res, "data", res)

def call_openai_with_messages(messages: list, model: str = "gpt-4o", temperature: float = 0.7, max_tokens: int = 1500):
    resp = openai.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    return resp.choices[0].message.content, resp

# =========================
# Auth Endpoints
# =========================
@app.post("/auth/login")
def login(req: LoginRequest):
    try:
        response = supabase.auth.sign_in_with_password({"email": req.email, "password": req.password})
        if getattr(response, "user", None):
            return {"success": True, "user": {"id": response.user.id, "email": response.user.email}}
        raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/auth/signup")
def signup(req: SignupRequest):
    try:
        response = supabase.auth.sign_up({"email": req.email, "password": req.password})
        if getattr(response, "user", None):
            supabase_insert("users", {"id": response.user.id, "email": req.email, "plan": "free"})
            return {"success": True, "user": {"id": response.user.id, "email": req.email}}
        raise HTTPException(status_code=400, detail="Signup failed")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# =========================
# Chat Sessions & History
# =========================
@app.post("/chat/start_session")
def start_session(req: StartSessionRequest):
    now = datetime.utcnow().isoformat()
    data = supabase_insert("chat_sessions", {"user_id": req.user_id, "name": req.name, "created_at": now})
    return {"success": True, "session_id": data[0]["id"]}

@app.get("/chat/sessions/{user_id}")
def list_sessions(user_id: str):
    data = supabase_select("chat_sessions", filters=[("eq", "user_id", user_id)], order_by="created_at")
    return {"success": True, "sessions": data}

@app.post("/chat/send")
def chat_send(req: ChatRequest):
    history = supabase_select("chat_history", filters=[("eq", "session_id", req.session_id)], order_by="created_at")
    history_trimmed = history[-req.max_history:] if history else []
    messages = [{"role": "system", "content": get_system_prompt("chat")}] + \
               [{"role": h["role"], "content": h["content"]} for h in history_trimmed] + \
               [{"role": "user", "content": req.prompt}]
    answer, _ = call_openai_with_messages(messages, temperature=0.6, max_tokens=1200)
    now = datetime.utcnow().isoformat()
    supabase_insert("chat_history", [
        {"session_id": req.session_id, "user_id": req.user_id, "role": "user", "content": req.prompt, "created_at": now},
        {"session_id": req.session_id, "user_id": req.user_id, "role": "assistant", "content": answer, "created_at": now}
    ])
    return {"success": True, "response": answer}

# =========================
# Project Generation
# =========================
@app.post("/generate_project")
def generate_project(req: GenRequest):
    try:
        # --------------------------
        # 1️⃣ Buscar histórico do chat
        # --------------------------
        history = supabase_select("chat_history", filters=[("eq", "session_id", req.session_id)], order_by="created_at")
        messages_for_model = [{"role": "system", "content": get_system_prompt("generate_project")}] + \
                             [{"role": h["role"], "content": h["content"]} for h in history] + \
                             [{"role": "user", "content": req.prompt}]

        # --------------------------
        # 2️⃣ Chamar OpenAI para gerar arquivos do projeto
        # --------------------------
        content, _ = call_openai_with_messages(messages_for_model, temperature=0.2, max_tokens=4000)
        try:
            files = json.loads(content)
        except:
            files = {"App.js": content, "README.md": f"# Projeto: {req.prompt}"}

        # --------------------------
        # 3️⃣ Gerar UUID do projeto
        # --------------------------
        project_uuid = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        # --------------------------
        # 4️⃣ Salvar arquivos no Supabase
        # --------------------------
        rows = [
            {
                "session_id": req.session_id,
                "user_id": req.user_id,
                "file_path": k,
                "content": v,
                "created_at": now
            } for k, v in files.items()
        ]
        supabase_insert("project_files", rows)

        # --------------------------
        # 5️⃣ Salvar arquivos localmente
        # --------------------------
        base_path = save_files_to_disk(project_uuid, req.user_id, req.session_id, files)

        # --------------------------
        # 6️⃣ Criar repo GitHub e commitar arquivos
        # --------------------------
        def github_create_repo_and_commit(project_uuid: str, files: dict) -> str:
            if not gh:
                raise RuntimeError("GitHub client not configured")
            user = gh.get_user()
            repo = user.create_repo(name=project_uuid, private=True)
            elements = []
            for path, content in files.items():
                elements.append(InputGitTreeElement(path, "100644", "blob", content))
            # Inicializar commit
            source = repo.get_branch("main")
            base_tree = repo.get_git_tree(source.commit.sha)
            tree = repo.create_git_tree(elements, base_tree)
            parent = repo.get_git_commit(source.commit.sha)
            commit = repo.create_git_commit(f"Genesis project {project_uuid}", tree, [parent])
            repo.get_git_ref("heads/main").edit(commit.sha)
            return f"https://github.com/{user.login}/{project_uuid}.git"

        github_repo_url = github_create_repo_and_commit(project_uuid, files)

        # --------------------------
        # 7️⃣ Criar projeto e deploy na Vercel
        # --------------------------
        def vercel_create_project_and_deploy(project_uuid: str, github_repo_url: str) -> str:
            if not VERCEL_TOKEN:
                raise RuntimeError("Vercel token not set")
            headers = {
                "Authorization": f"Bearer {VERCEL_TOKEN}",
                "Content-Type": "application/json"
            }
            repo_path = github_repo_url.split("https://github.com/")[-1].replace(".git","")

            # Criar projeto Vercel
            project_data = {
                "name": project_uuid,
                "gitSource": "github",
                "github": {"repo": repo_path, "branch": "main"},
                "framework": "nextjs",
                "teamId": VERCEL_TEAM_ID
            }
            requests.post("https://api.vercel.com/v13/projects", headers=headers)

            # Criar deploy
            deploy_data = {
                "name": project_uuid,
                "gitSource": "github",
                "github": {"repo": repo_path, "branch": "main"},
                "framework": "nextjs"
            }
            deploy_resp = requests.post("https://api.vercel.com/v13/deployments", headers=headers, json=deploy_data)
            deploy_resp.raise_for_status()
            return deploy_resp.json().get("url", "")

        vercel_url = vercel_create_project_and_deploy(project_uuid, github_repo_url)

        # --------------------------
        # 8️⃣ Registrar projeto no Supabase
        # --------------------------
        supabase_insert("projects", [{
            "id": project_uuid,
            "user_id": req.user_id,
            "project_id": req.session_id,
            "uuid": project_uuid,
            "prompt": req.prompt,
            "llm_output": json.dumps(files),
            "github_commit_url": github_repo_url,
            "vercel_url": vercel_url,
            "status": "deployed",
            "created_at": now
        }])

        return {
            "success": True,
            "files": list(files.keys()),
            "saved_path": base_path,
            "github_commit_url": github_repo_url,
            "vercel_url": vercel_url
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
