# backend/main.py
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
from supabase import create_client
import logging

# =========================
# Logging
# =========================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================
# Variáveis de ambiente
# =========================
openai.api_key = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Validação de variáveis de ambiente
if not openai.api_key:
    logger.error("OPENAI_API_KEY não está definida!")
    raise Exception("OPENAI_API_KEY não está definida!")
if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("SUPABASE_URL ou SUPABASE_KEY não estão definidas!")
    raise Exception("SUPABASE_URL ou SUPABASE_KEY não estão definidas!")

# =========================
# Cliente Supabase
# =========================
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# FastAPI app
# =========================
app = FastAPI(title="Genesis Project Generator API", version="1.0")

# =========================
# CORS Middleware
# =========================
origins = [
    "http://localhost:3000",  # Para testes locais
    "https://genesis-k2ykslrzq-devrenanferraris-projects.vercel.app",  # Frontend Vercel
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Permite GET, POST, OPTIONS
    allow_headers=["*"],
)

# =========================
# Modelos Pydantic
# =========================
class GenRequest(BaseModel):
    user_id: str
    prompt: str

# =========================
# Endpoint /generate
# =========================
@app.post("/generate")
def generate(req: GenRequest):
    try:
        logger.info(f"Recebido /generate do usuário: {req.user_id}")

        # Chamada OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "Você é um gerador de código confiável."},
                {"role": "user", "content": req.prompt}
            ],
            temperature=0.2,
            max_tokens=2000
        )

        llm_output = response.choices[0].message.content
        logger.info(f"Resposta do OpenAI recebida, {len(llm_output)} caracteres.")

        # Salva no Supabase
        supabase.table("projects").insert({
            "user_id": req.user_id,
            "prompt": req.prompt,
            "llm_output": llm_output
        }).execute()
        logger.info("Dados salvos no Supabase com sucesso.")

        return {"llm_output": llm_output}

    except openai.error.OpenAIError as e:
        logger.error(f"Erro OpenAI: {e}")
        raise HTTPException(status_code=502, detail="Erro ao gerar código via OpenAI.")
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        raise HTTPException(status_code=500, detail="Erro interno no servidor.")
