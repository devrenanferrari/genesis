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

import ast
from pathlib import Path

# =========================
# Constants / System Prompt
# =========================
GENESIS_SYSTEM_PROMPT = """
Core Identity

Você é Genesis, uma IA avançada para gerar projetos full-stack modernos e funcionais, sempre atualizados para Next.js 15 com App Router, Tailwind CSS, shadcn/ui e Lucide Icons.  
Você responde em português por padrão, mas pode alternar idiomas se o usuário pedir.

Objetivo

Quando gerar projetos, você **sempre deve retornar apenas JSON válido**, com arquivos completos prontos para build no Next.js 15 e deploy automático no Vercel.  
Evite qualquer conflito de dependências e garanta que `npm install` e `vercel build` rodem sem erros.

Formato de saída esperado:

{
  "package.json": "{...conteúdo do package.json...}",
  "tsconfig.json": "{...conteúdo do tsconfig.json...}",
  "next.config.js": "{...conteúdo do next.config.js...}",
  "tailwind.config.ts": "{...conteúdo do tailwind.config.ts...}",
  "app/layout.tsx": "{...conteúdo do layout.tsx...}",
  "app/page.tsx": "{...conteúdo do page.tsx...}",
  "components/Header.tsx": "{...conteúdo do Header...}",
  "components/Footer.tsx": "{...conteúdo do Footer...}",
  "styles/globals.css": "{...conteúdo do globals.css...}",
  "public/": "se necessário"
}

Regras de geração

1. Todos os nomes de arquivos devem usar **kebab-case**, exceto componentes React que devem ser **PascalCase** (`Header.tsx`, `Footer.tsx`).
2. Cada página (`page.tsx`) deve ter obrigatoriamente um layout pai (`layout.tsx`) compatível com Next.js 15.
3. Importe apenas ícones específicos do `lucide-react` (ex: `import { Home } from 'lucide-react'`) para evitar erros de build.
4. Inclua Tailwind, shadcn/ui e Lucide Icons corretamente, sem usar importações genéricas.
5. JSON gerado deve ser **perfeitamente válido**.
6. Estrutura mínima funcional:
   - `package.json` com React e ReactDOM **na mesma versão estável** (ex: 18.2.0)
   - `tsconfig.json` compatível com Next.js 15 e TypeScript
   - `next.config.js` com `reactStrictMode: true` e `swcMinify: true`
   - `tailwind.config.ts` com cores hardcoded e compatível com shadcn/ui
   - app/layout.tsx, app/page.tsx
   - components/ (Header.tsx, Footer.tsx)
   - styles/globals.css
   - public/ se necessário
7. Sempre inclua **3–5 ações futuras** dentro de `<Actions>` ao final, mas fora do JSON.
8. Nunca inclua explicações ou instruções fora do JSON.
9. Garanta compatibilidade total com `npm install` e build automático em Vercel, evitando conflitos de versões.
10. Use versões exatas de dependências sempre que possível.
11. Para imagens placeholders, use: `/placeholder.svg?height={height}&width={width}&query={query}`.
12. Sempre utilize semantic HTML, acessibilidade (ARIA roles, alt text, `sr-only`) e design responsivo.

Recusas

Se o usuário pedir algo violento, ilegal, sexual ou antiético, responda apenas:

I'm sorry. I'm not able to assist with that.

### Exemplos de Ações Futuras

<Actions>
  <Action name="Adicionar autenticação" description="Implementar login e cadastro com Supabase ou NextAuth" />
  <Action name="Criar seção hero" description="Adicionar seção principal visualmente destacada na landing page" />
  <Action name="Adicionar modo escuro" description="Implementar dark mode para toda a aplicação" />
  <Action name="Gerar imagens hero" description="Gerar imagens para o hero da página" />
  <Action name="Implementar formulário de contato" description="Adicionar formulário de contato funcional" />
</Actions>
"""


def get_system_prompt(context: str = None) -> str:
    if context == "chat":
        return GENESIS_SYSTEM_PROMPT + "\n\nContexto: Chat geral com memória de sessão."
    elif context == "generate_project":
        return GENESIS_SYSTEM_PROMPT + "\n\nContexto: Gere projeto completo. **Apenas JSON válido com arquivos funcionais.**"
    elif context == "regenerate_files":
        return GENESIS_SYSTEM_PROMPT + "\n\nContexto: Regere arquivos do projeto. Apenas JSON."
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

@app.post("/generate_project")
def generate_project(req: GenRequest):
    try:
        # --------------------------
        # 1️⃣ Buscar histórico do chat
        # --------------------------
        history = supabase_select(
            "chat_history",
            filters=[("eq", "session_id", req.session_id)],
            order_by="created_at"
        )
        messages_for_model = [{"role": "system", "content": get_system_prompt("generate_project")}] + \
                             [{"role": h["role"], "content": h["content"]} for h in history] + \
                             [{"role": "user", "content": req.prompt}]

        # --------------------------
        # 2️⃣ Chamar OpenAI para gerar arquivos do projeto
        # --------------------------
        content, _ = call_openai_with_messages(messages_for_model, temperature=0.2, max_tokens=12000)

        # 🔹 Fallback seguro para JSON inválido
        files = {}
        try:
            files = json.loads(content)
        except json.JSONDecodeError:
            try:
                files = ast.literal_eval(content)
            except:
                files = {"app/page.tsx": content}

        files = {str(Path(k)): v for k, v in files.items()}

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
        # 6️⃣ Criar repo GitHub com nome = UUID e commit inicial
        # --------------------------
        if not gh:
            raise RuntimeError("GitHub client not configured")

        user = gh.get_user("devrenanferrari")  # força apontar para seu usuário
        repo = user.create_repo(name=project_uuid, private=True, auto_init=True)

        elements = [
            InputGitTreeElement(path, "100644", "blob", content)
            for path, content in files.items()
        ]
        source = repo.get_branch("main")
        base_tree = repo.get_git_tree(source.commit.sha)
        tree = repo.create_git_tree(elements, base_tree)
        parent = repo.get_git_commit(source.commit.sha)
        commit = repo.create_git_commit(f"Genesis project {project_uuid}", tree, [parent])
        repo.get_git_ref("heads/main").edit(commit.sha)
        github_repo_url = f"https://github.com/devrenanferrari/{project_uuid}.git"

        # --------------------------
        # 7️⃣ Criar projeto na Vercel
        # --------------------------
        if not VERCEL_TOKEN:
            raise RuntimeError("Vercel token not set")
        headers = {
            "Authorization": f"Bearer {VERCEL_TOKEN}",
            "Content-Type": "application/json"
        }
        repo_path = f"devrenanferrari/{project_uuid}"

        project_resp = requests.post(
            "https://api.vercel.com/v11/projects",
            headers=headers,
            json={
                "name": project_uuid,
                "gitRepository": {"type": "github", "repo": repo_path},
                "framework": "nextjs",
                "rootDirectory": None,
                "skipGitConnectDuringLink": True,
                "installCommand": "npm install",
                "buildCommand": "npm run build",
                "outputDirectory": ".next",
                "enablePreviewFeedback": True,
                "enableProductionFeedback": True
            }
        )
        project_resp.raise_for_status()

        # --------------------------
        # 8️⃣ Commit fake para disparar deploy
        # --------------------------
        repo.create_file(".vercel_trigger", "Trigger Vercel Deploy", "Deploy trigger", branch="main")

        # --------------------------
        # 9️⃣ Registrar projeto no Supabase
        # --------------------------
        supabase_insert("projects", [{
            "id": project_uuid,
            "user_id": req.user_id,
            "project_id": req.session_id,
            "uuid": project_uuid,
            "prompt": req.prompt,
            "llm_output": json.dumps(files),
            "github_commit_url": github_repo_url,
            "vercel_url": f"https://{project_uuid}.vercel.app",
            "status": "deployed",
            "created_at": now
        }])

        return {
            "success": True,
            "files": list(files.keys()),
            "saved_path": base_path,
            "github_commit_url": github_repo_url,
            "vercel_url": f"https://{project_uuid}.vercel.app"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
