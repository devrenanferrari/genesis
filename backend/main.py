import os
import uuid
import json
import re
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
from supabase import create_client
from github import Github, InputGitTreeElement
import requests
from datetime import datetime

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

  ```tsx file="login-form.tsx"
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

</CodeProject> ```

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
    """
    Retorna o prompt base da Genesis + instruções adicionais dependendo do contexto.
    """
    if context == "chat":
        return GENESIS_SYSTEM_PROMPT + "\n\nContexto: Você está em um chat geral com o usuário. Seja conciso e mantenha a memória da sessão."
    elif context == "generate_project":
        return GENESIS_SYSTEM_PROMPT + "\n\nContexto: Gere um projeto completo. Responda **somente** com um JSON no formato {\"<path>\": \"<content>\"}."
    elif context == "regenerate_files":
        return GENESIS_SYSTEM_PROMPT + "\n\nContexto: Regere os arquivos do projeto com base no histórico da sessão. Saída deve ser JSON válido no formato {\"<path>\": \"<content>\"}."
    else:
        return GENESIS_SYSTEM_PROMPT


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
VERCEL_TEAM_ID = os.getenv("VERCEL_TEAM_ID")  # opcional

if not all([openai.api_key, SUPABASE_URL, SUPABASE_KEY]):
    # não trava a importação, mas avisa no log
    print("Warning: OPENAI_API_KEY or SUPABASE env vars may not be set.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
gh = Github(GITHUB_TOKEN) if GITHUB_TOKEN else None
repo = gh.get_repo(GITHUB_REPO) if gh and GITHUB_REPO else None

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

class StartSessionRequest(BaseModel):
    user_id: str
    name: Optional[str] = "Nova sessão"

class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    prompt: str
    max_history: Optional[int] = 50  # quantas mensagens trazer (limitar o prompt)

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
    repo: str  # ex: "devrenanferrari/genesis"

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
    name = re.sub(r"_{2,}", "_", name)
    return name[:100]

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
    # supabase-py returns an object with .data on success. Propagar erro se não tiver data.
    if hasattr(res, "error") and res.error:
        raise Exception(res.error.message if hasattr(res.error, "message") else str(res.error))
    return getattr(res, "data", res)

def supabase_select(table: str, filters: List[tuple] = None, order_by: Optional[str] = None, limit: Optional[int] = None):
    if not supabase:
        raise RuntimeError("Supabase client not initialized")
    q = supabase.table(table).select("*")
    if filters:
        for (op, key, value) in filters:
            # op: eq, neq, like, ilike, etc.
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
    for (op, key, value) in filters:
        q = getattr(q, op)(key, value)
    res = q.execute()
    if hasattr(res, "error") and res.error:
        raise Exception(res.error.message if hasattr(res.error, "message") else str(res.error))
    return getattr(res, "data", res)

def supabase_delete(table: str, filters: List[tuple]):
    if not supabase:
        raise RuntimeError("Supabase client not initialized")
    q = supabase.table(table).delete()
    for (op, key, value) in filters:
        q = getattr(q, op)(key, value)
    res = q.execute()
    if hasattr(res, "error") and res.error:
        raise Exception(res.error.message if hasattr(res.error, "message") else str(res.error))
    return getattr(res, "data", res)

def call_openai_with_messages(messages: list, model: str = "gpt-4o", temperature: float = 0.7, max_tokens: int = 1500):
    # wrapper para chamada ao OpenAI Chat Completions
    try:
        resp = openai.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        content = resp.choices[0].message.content
        return content, resp
    except Exception as e:
        raise

# =========================
# Endpoints Auth (Supabase)
# =========================
@app.post("/auth/login")
def login(req: LoginRequest):
    try:
        response = supabase.auth.sign_in_with_password({
            "email": req.email,
            "password": req.password
        })
        if getattr(response, "user", None):
            return {"success": True, "user": {"id": response.user.id, "email": response.user.email}}
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/auth/signup")
def signup(req: SignupRequest):
    try:
        response = supabase.auth.sign_up({"email": req.email, "password": req.password})
        if getattr(response, "user", None):
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
# Sessões e Histórico
# =========================
@app.post("/chat/start_session")
def start_session(req: StartSessionRequest):
    try:
        row = {
            "user_id": req.user_id,
            "name": req.name
        }
        data = supabase_insert("chat_sessions", row)
        session_id = data[0]["id"] if isinstance(data, list) else data[0]["id"]
        return {"success": True, "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/sessions/{user_id}")
def list_sessions(user_id: str):
    try:
        data = supabase_select("chat_sessions", filters=[("eq", "user_id", user_id)], order_by="created_at")
        return {"success": True, "sessions": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# Enviar mensagem / chat com memória
# =========================
@app.post("/chat/send")
def chat_send(req: ChatRequest):
    try:
        # pegar histórico da sessão (limitando por max_history * 2 mensagens se quiser)
        history = supabase_select(
            "chat_history",
            filters=[("eq", "session_id", req.session_id)],
            order_by="created_at"
        )
        # limitar histórico para as últimas N mensagens (transformar em list)
        history = history if isinstance(history, list) else list(history)
        limit = req.max_history
        history_trimmed = history[-limit:] if limit and len(history) > limit else history

        messages = [{"role": h["role"], "content": h["content"]} for h in history_trimmed]

        messages_for_model = [{"role": "system", "content": get_system_prompt("chat")}] + messages + [{"role": "user", "content": req.prompt}]

        # chamada ao modelo
        answer, raw = call_openai_with_messages(messages_for_model, temperature=0.6, max_tokens=1200)

        # salva user e assistant no histórico
        now = datetime.utcnow().isoformat()
        supabase_insert("chat_history", [
            {"session_id": req.session_id, "user_id": req.user_id, "role": "user", "content": req.prompt, "created_at": now},
            {"session_id": req.session_id, "user_id": req.user_id, "role": "assistant", "content": answer, "created_at": now}
        ])

        return {"success": True, "response": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# Editar / deletar mensagens
# =========================
@app.post("/chat/edit_message")
def edit_message(req: EditMessageRequest):
    try:
        supabase_update("chat_history", {"content": req.new_content}, filters=[("eq", "id", req.message_id)])
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/chat/delete_message/{message_id}")
def delete_message(message_id: str):
    try:
        supabase_delete("chat_history", filters=[("eq", "id", message_id)])
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# Geração de projetos (vinculado à session_id) - salva em supabase project_files
# =========================
@app.post("/generate_project")
def generate_project(req: GenRequest):
    try:
        # monta mensagens a partir do histórico da sessão
        history = supabase_select("chat_history", filters=[("eq", "session_id", req.session_id)], order_by="created_at")
        messages = [{"role": h["role"], "content": h["content"]} for h in history] if history else []

        messages_for_model = [{"role": "system", "content": get_system_prompt("generate_project")}] + messages + [{"role": "user", "content": req.prompt}]

        content, raw = call_openai_with_messages(messages_for_model, temperature=0.2, max_tokens=4000)
        try:
            files = json.loads(content)
            if not isinstance(files, dict):
                raise ValueError("Esperava um dict/JSON de arquivos")
        except Exception:
            # se não for JSON válido, guarda um único arquivo com a saída
            files = {"App.js": content, "README.md": f"# Projeto: {req.prompt}"}

        # salva arquivos na tabela project_files
        rows = []
        now = datetime.utcnow().isoformat()
        for fname, fcontent in files.items():
            rows.append({
                "session_id": req.session_id,
                "user_id": req.user_id,
                "file_path": fname,
                "content": fcontent,
                "created_at": now
            })
        supabase_insert("project_files", rows)

        # salva no histórico que gerou arquivos
        supabase_insert("chat_history", [
            {"session_id": req.session_id, "user_id": req.user_id, "role": "user", "content": req.prompt, "created_at": now},
            {"session_id": req.session_id, "user_id": req.user_id, "role": "assistant", "content": "[Arquivos gerados]", "created_at": now}
        ])

        # opcional: também escrever em disco (para debug / deploy local)
        project_uuid = str(uuid.uuid4())
        base_path = save_files_to_disk(project_uuid, req.user_id, req.session_id, files)

        return {"success": True, "files": list(files.keys()), "saved_path": base_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# Endpoints para arquivos - listar / editar / deletar
# =========================
@app.get("/files/{session_id}")
def list_files(session_id: str):
    try:
        data = supabase_select("project_files", filters=[("eq", "session_id", session_id)], order_by="created_at")
        return {"success": True, "files": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/files/edit")
def edit_file(req: EditFileRequest):
    try:
        supabase_update("project_files", {"content": req.new_content}, filters=[("eq", "id", req.file_id)])
        # opcional: registrar no histórico que arquivo foi editado
        file_row = supabase_select("project_files", filters=[("eq", "id", req.file_id)])
        if file_row:
            file_row = file_row[0]
            supabase_insert("chat_history", [{"session_id": file_row["session_id"], "user_id": file_row["user_id"], "role": "assistant", "content": f"[Arquivo {file_row['file_path']} editado]"}])
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/files/delete/{file_id}")
def delete_file(file_id: str):
    try:
        # pegar info antes de deletar pra registrar no histórico
        row = supabase_select("project_files", filters=[("eq", "id", file_id)])
        if row and len(row) > 0:
            r = row[0]
            supabase_delete("project_files", filters=[("eq", "id", file_id)])
            supabase_insert("chat_history", [{"session_id": r["session_id"], "user_id": r["user_id"], "role": "assistant", "content": f"[Arquivo {r['file_path']} removido]"}])
            return {"success": True}
        return {"success": False, "detail": "Arquivo não encontrado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# Criar arquivos e commitar no GitHub (vinculado à sessão se informado)
# =========================
@app.post("/create_project_files")
def create_project_files(data: FileInput):
    try:
        project_uuid = str(uuid.uuid4())
        normalized_project = normalize_project_name(data.project)
        base_path = Path("containers") / project_uuid / normalized_project
        base_path.mkdir(parents=True, exist_ok=True)

        # escreve arquivos no disco
        for file_path, content in data.files.items():
            full_path = base_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

        # salva no supabase project_files (se session_id fornecida)
        now = datetime.utcnow().isoformat()
        rows = []
        for file_path, content in data.files.items():
            row = {
                "session_id": data.session_id,
                "user_id": data.user_id,
                "file_path": file_path,
                "content": content,
                "created_at": now
            }
            rows.append(row)
        if data.session_id:
            supabase_insert("project_files", rows)

            # registrar no histórico
            supabase_insert("chat_history", [
                {"session_id": data.session_id, "user_id": data.user_id, "role": "assistant", "content": f"[Arquivos adicionados: {', '.join(list(data.files.keys()))}]", "created_at": now}
            ])

        # commit no GitHub (se configurado)
        github_commit_url = None
        if repo:
            tree_elements = []
            for file_path, content in data.files.items():
                git_path = f"{normalized_project}/{file_path}"
                tree_elements.append(InputGitTreeElement(git_path, "100644", "blob", content))

            ref = repo.get_git_ref(f"heads/{GITHUB_BRANCH}")
            base_tree = repo.get_git_tree(ref.object.sha)
            tree = repo.create_git_tree(tree_elements, base_tree)
            parent = repo.get_git_commit(ref.object.sha)
            commit = repo.create_git_commit(
                f"Add project {normalized_project} for user {data.user_id}", tree, [parent]
            )
            ref.edit(commit.sha)
            github_commit_url = f"https://github.com/{GITHUB_REPO}/commit/{commit.sha}"

        return {
            "success": True,
            "uuid": project_uuid,
            "path": str(base_path),
            "files_created": list(data.files.keys()),
            "github_commit_url": github_commit_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar arquivos: {str(e)}")

# =========================
# Deploy na Vercel (mesma lógica que antes)
# =========================
@app.post("/deploy_project")
def deploy_project(data: DeployRequest):
    try:
        url = "https://api.vercel.com/v13/deployments"
        if VERCEL_TEAM_ID:
            url += f"?teamId={VERCEL_TEAM_ID}"

        headers = {"Authorization": f"Bearer {VERCEL_TOKEN}", "Content-Type": "application/json"}
        
        project_name = re.sub(r'[^a-z0-9._-]', '_', data.project.lower())
        project_name = re.sub(r'_+', '_', project_name)[:100]

        payload = {
            "name": project_name,
            "gitSource": {
                "type": "github",
                "org": data.repo.split("/")[0],
                "repo": data.repo.split("/")[1],
                "ref": GITHUB_BRANCH
            },
            "projectSettings": {
                "framework": "nextjs",
                "installCommand": "npm install",
                "buildCommand": "npm run build",
                "devCommand": "npm run dev",
                "outputDirectory": "."
            }
        }

        r = requests.post(url, headers=headers, json=payload)
        if r.status_code not in (200, 201):
            raise HTTPException(status_code=r.status_code, detail=r.text)

        return {"success": True, "vercel_response": r.json()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# Endpoint utilitário: regenerar arquivos com base no histórico (ex: quando usuário edita prompt)
# =========================
@app.post("/generate/regenerate_session_files")
def regenerate_session_files(req: GenRequest):
    try:
        # Pega histórico completo da sessão
        history = supabase_select("chat_history", filters=[("eq", "session_id", req.session_id)], order_by="created_at")
        messages = [{"role": h["role"], "content": h["content"]} for h in history] if history else []
        messages_for_model = [{"role": "system", "content": get_system_prompt("regenerate_files")}] + messages + [{"role": "user", "content": req.prompt}]
        content, raw = call_openai_with_messages(messages_for_model, temperature=0.2, max_tokens=4000)
        try:
            files = json.loads(content)
        except:
            files = {"App.js": content}

        # atualiza project_files: strategy = upsert (deleta arquivos antigos com mesmo file_path e session_id e insere)
        existing = supabase_select("project_files", filters=[("eq", "session_id", req.session_id)])
        existing_paths = {r["file_path"]: r for r in existing} if existing else {}

        now = datetime.utcnow().isoformat()
        to_delete_ids = []
        to_upsert = []
        for fname, fcontent in files.items():
            if fname in existing_paths:
                # update existing
                supabase_update("project_files", {"content": fcontent, "created_at": now}, filters=[("eq", "session_id", req.session_id), ("eq", "file_path", fname)])
            else:
                to_upsert.append({"session_id": req.session_id, "user_id": req.user_id, "file_path": fname, "content": fcontent, "created_at": now})
        if to_upsert:
            supabase_insert("project_files", to_upsert)

        # registra no histórico
        supabase_insert("chat_history", [
            {"session_id": req.session_id, "user_id": req.user_id, "role": "assistant", "content": "[Arquivos regenerados]", "created_at": now}
        ])

        return {"success": True, "files": list(files.keys())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
