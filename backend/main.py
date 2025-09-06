import os
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
from supabase import create_client, Client

# =========================
# Variáveis de ambiente
# =========================
openai.api_key = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not openai.api_key:
    raise Exception("OPENAI_API_KEY não está definida!")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("SUPABASE_URL ou SUPABASE_KEY não estão definidas!")

# =========================
# Cliente Supabase
# =========================
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# FastAPI app
# =========================
app = FastAPI()

# =========================
# CORS Middleware
# =========================
origins = [
    "http://localhost:3000",
    "https://genesis-k2ykslrzq-devrenanferraris-projects.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Modelos Pydantic
# =========================
class GenRequest(BaseModel):
    user_id: str | None = None
    prompt: str

# =========================
# Endpoint /generate
# =========================
@app.post("/generate")
def generate(req: GenRequest):
    # Gera UUID se user_id não for fornecido
    user_id = req.user_id
    try:
        if not user_id:
            user_id = str(uuid.uuid4())
        else:
            uuid.UUID(user_id)  # valida UUID enviado
    except ValueError:
        user_id = str(uuid.uuid4())

    # Chamada OpenAI
    try:
        response = openai.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "Você é um gerador de código confiável."},
                {"role": "user", "content": req.prompt}
            ],
            temperature=0.2,
            max_tokens=2000
        )
        llm_output = response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro OpenAI: {e}")

    # Salva no Supabase
    try:
        supabase.table("projects").insert({
            "user_id": user_id,
            "prompt": req.prompt,
            "llm_output": llm_output
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro Supabase: {e}")

    return {"llm_output": llm_output, "user_id": user_id}
