import os
import uuid
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import openai
from supabase import create_client
from github import Github, InputGitTreeElement
import requests

import ast

# =========================
# Constants / System Prompt (ATUALIZADO para streaming iterativo)
# =========================
GENESIS_SYSTEM_PROMPT = """
Core Identity

Você é Genesis, uma IA avançada para gerar projetos full-stack modernos e funcionais, sempre atualizados para Next.js 15 com App Router, Tailwind CSS, shadcn/ui e Lucide Icons.
Você responde em português por padrão, mas pode alternar idiomas se o usuário pedir.

Objetivo

Você trabalhará de forma iterativa, COMETENDO mudanças passo a passo (como um engenheiro criando commits).  
**Regras essenciais** — responda sempre em JSON puro, UM objeto JSON por linha, sem texto explicativo fora das linhas JSON.

Eventos suportados (cada linha é um evento JSON):
1) Thought (pensamento curto)
{"type":"thought","content":"explicação curta do próximo passo"}

2) Patch (alteração em arquivo)
- Pode usar um campo `content` com o conteúdo completo do arquivo (preferível).
- Ou pode usar um campo `diff` com diff unificado (unified diff). O backend tentará aplicar/interpretar.
{"type":"patch","file":"app/page.tsx","content":"<conteúdo completo do arquivo aqui>"}
ou
{"type":"patch","file":"app/page.tsx","diff":"--- a/app/page.tsx\n+++ b/app/page.tsx\n@@ -1,3 +1,6 @@\n- old line\n+ new line"}

3) Commit (encerra um ciclo de alterações)
{"type":"commit"}

Regras de comportamento do modelo:
- Sempre produza primeiro 0+ eventos "thought", depois 1+ "patch" quando for necessário, e finalize o grupo com 1 "commit".
- Nunca envie o projeto inteiro como um único JSON com dezenas de arquivos. Trabalhe incrementalmente.
- Para novos arquivos, prefira enviar `content` com o arquivo completo.
- Para edições pequenas, `diff` em estilo unified diff é aceitável, mas o backend prefere `content` para garantir aplicabilidade.
- Não use Markdown, não inclua explicações fora do JSON.
- Cada evento deve estar em sua própria linha (newline-terminated) para facilitar parsing incremental.

Se o usuário pedir algo ilegal, violento ou antiético, responda:
"I'm sorry. I'm not able to assist with that."

Contexto: Quando chamado para "generate_project", considere que o usuário quer um projeto Next.js mínimo e funcional. Seja conservador com versões e dependências.

Exemplo de sequência aceitável (linha por linha):
{"type":"thought","content":"Vou criar a página inicial com header e footer."}
{"type":"patch","file":"app/layout.tsx","content":"export default function Layout(...) { ... }"}
{"type":"patch","file":"app/page.tsx","content":"export default function Page() { ... }"}
{"type":"commit"}

Pronto para receber a descrição do projeto e emitir eventos iterativos.
"""

def get_system_prompt(context: str = None) -> str:
    # mantém compatibilidade com contexts anteriores (chat, generate_project, etc.)
    if context == "chat":
        return GENESIS_SYSTEM_PROMPT + "\n\nContexto: Chat geral com memória de sessão."
    elif context == "generate_project":
        return GENESIS_SYSTEM_PROMPT + "\n\nContexto: Gere projeto iterativamente (events: thought, patch, commit)."
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
GITHUB_REPO = os.getenv("GITHUB_REPO")  # opcional, usaremos para fallback se quiser
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
VERCEL_TOKEN = os.getenv("VERCEL_TOKEN")
VERCEL_TEAM_ID = os.getenv("VERCEL_TEAM_ID")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
gh = Github(GITHUB_TOKEN) if GITHUB_TOKEN else None
# repo variable will be created dynamically per-user/repo when committing
repo = None

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
# Helpers (Supabase wrappers and file helpers)
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
# Auth Endpoints (sem alteração)
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
# Chat Sessions & History (sem alteração importante)
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
# Utility: naive unified-diff --> try to extract new content (best-effort)
# =========================
def try_extract_content_from_diff(diff_text: str) -> Optional[str]:
    """
    Heuristic attempt to reconstruct the "new file" content from a unified diff.
    This is NOT perfect. Prefer the model sending `content` directly.
    Strategy:
      - If diff contains a section starting with '+++ ' followed by lines, try to collect lines
        that start with '+' (but not '+++') and return them concatenated (without leading +).
      - If that fails, return None.
    """
    try:
        lines = diff_text.splitlines()
        new_lines = []
        collect = False
        for ln in lines:
            if ln.startswith('+++ '):
                collect = True
                continue
            if not collect:
                continue
            # unified diff lines that start with '+' are additions
            if ln.startswith('+') and not ln.startswith('+++'):
                new_lines.append(ln[1:])
            elif ln.startswith(' '):
                # context line — include as-is
                new_lines.append(ln[1:])
            elif ln.startswith('-'):
                # removed line — ignore
                continue
            else:
                # other metadata or next hunk — ignore
                continue
        if new_lines:
            return "\n".join(new_lines)
    except Exception:
        return None
    return None

# =========================
# Main: /generate_project (STREAMING style v0)
# =========================
@app.post("/generate_project")
def generate_project(request: Request, req: GenRequest):

    def event_stream():
        latest_file_contents: Dict[str, str] = {}
        github_repo_url = None
        vercel_url = None
        project_uuid = None
        buffer = ""

        try:
            # Buscar histórico e preparar mensagens
            history = supabase_select("chat_history", filters=[("eq", "session_id", req.session_id)], order_by="created_at") or []
            messages_for_model = [{"role": "system", "content": get_system_prompt("generate_project")}] + \
                                 [{"role": h["role"], "content": h["content"]} for h in history] + \
                                 [{"role": "user", "content": req.prompt}]
            
            # Iniciar stream OpenAI
            stream_resp = openai.chat.completions.create(
                model="gpt-4o",
                messages=messages_for_model,
                stream=True,
                temperature=0.2,
                max_tokens=4000
            )

            # Iterar chunks
            for chunk in stream_resp:
                text_piece = getattr(chunk.choices[0], "delta", {}).get("content", "")
                if not text_piece:
                    continue

                yield f"data: {json.dumps({'delta': text_piece})}\n\n"
                buffer += text_piece
                lines = buffer.split("\n")
                complete_lines, buffer = lines[:-1], lines[-1]

                for ln in complete_lines:
                    ln = ln.strip()
                    if not ln:
                        continue
                    try:
                        parsed = json.loads(ln)
                    except:
                        parsed = None
                    if not parsed or not isinstance(parsed, dict):
                        continue

                    event_type = parsed.get("type")
                    now = datetime.utcnow().isoformat()

                    if event_type == "patch":
                        file_path = parsed.get("file")
                        content = parsed.get("content")
                        diff = parsed.get("diff")
                        saved_content = content or try_extract_content_from_diff(diff) or ""
                        latest_file_contents[file_path] = saved_content
                        # Persistir no Supabase
                        try:
                            supabase_insert("project_files", [{
                                "session_id": req.session_id,
                                "user_id": req.user_id,
                                "file_path": file_path,
                                "content": saved_content,
                                "diff": diff or "",
                                "created_at": now
                            }])
                        except:
                            pass

                    elif event_type == "commit":
                        # Criar project_uuid se ainda não existir
                        if not project_uuid:
                            project_uuid = str(uuid.uuid4())
                        # Salvar arquivos localmente
                        save_files_to_disk(project_uuid, req.user_id, req.session_id, latest_file_contents)

                        # GitHub commit (opcional)
                        if gh:
                            try:
                                user = gh.get_user()
                                created_repo = user.create_repo(name=project_uuid, private=True, auto_init=True)
                                for path, content in latest_file_contents.items():
                                    created_repo.create_file(path, f"Add {path}", content, branch=GITHUB_BRANCH)
                                github_repo_url = f"https://github.com/{user.login}/{project_uuid}.git"
                            except:
                                github_repo_url = None

                        # Vercel deploy (opcional)
                        if VERCEL_TOKEN:
                            try:
                                headers = {"Authorization": f"Bearer {VERCEL_TOKEN}", "Content-Type": "application/json"}
                                payload = {"name": project_uuid, "framework": "nextjs", "installCommand": "npm install",
                                           "buildCommand": "npm run build", "outputDirectory": ".next"}
                                if github_repo_url:
                                    repo_path = github_repo_url.split("https://github.com/")[-1].replace(".git", "")
                                    payload["gitRepository"] = {"type": "github", "repo": repo_path}
                                    payload["skipGitConnectDuringLink"] = True
                                r = requests.post("https://api.vercel.com/v11/projects", headers=headers, json=payload, timeout=30)
                                r.raise_for_status()
                                vercel_url = f"https://{project_uuid}.vercel.app"
                            except:
                                vercel_url = None

                        # Persistir projeto no Supabase
                        try:
                            supabase_insert("projects", [{
                                "id": project_uuid,
                                "user_id": req.user_id,
                                "project_id": req.session_id,
                                "uuid": project_uuid,
                                "prompt": req.prompt,
                                "llm_output": json.dumps(list(latest_file_contents.keys())),
                                "github_commit_url": github_repo_url or "",
                                "vercel_url": vercel_url or "",
                                "status": "deployed" if vercel_url else "created",
                                "created_at": datetime.utcnow().isoformat()
                            }])
                        except:
                            pass

                        # Notificar cliente commit ok
                        yield f"event: commit\ndata: {json.dumps({'status':'ok','project_uuid': project_uuid,'github': github_repo_url,'vercel': vercel_url})}\n\n"

            # ===== FIM DO STREAM =====
            # Enviar JSON final com todos os arquivos e URLs
            final_payload = {
                "status": "done",
                "project_uuid": project_uuid,
                "files": latest_file_contents,
                "github_commit_url": github_repo_url,
                "vercel_url": vercel_url
            }
            yield f"data: {json.dumps(final_payload)}\n\n"

        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")



# =========================
# (Opcional) endpoint de utilidade para reconstruir arquivos do session_id
# =========================
@app.get("/projects/reconstruct/{session_id}")
def reconstruct_files(session_id: str):
    """
    Tenta reconstruir os arquivos salvos em 'project_files' para uma resposta JSON com file_path->content.
    """
    try:
        pf_rows = supabase_select("project_files", filters=[("eq", "session_id", session_id)])
        files: Dict[str, str] = {}
        # Tomamos o último registro por file_path contendo content preferencialmente
        by_file: Dict[str, Dict[str, Any]] = {}
        for r in pf_rows:
            fp = r.get("file_path")
            if not fp:
                continue
            # Prefer content não vazio
            if r.get("content"):
                by_file[fp] = r
            else:
                # se não há content, mantenha a primeira occurrence if none
                if fp not in by_file:
                    by_file[fp] = r

        for fp, r in by_file.items():
            files[fp] = r.get("content") or r.get("diff") or ""

        return {"success": True, "files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
