import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
from supabase import create_client

# =========================
# Variáveis de ambiente
# =========================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Validação
if not OPENAI_API_KEY:
    raise Exception("OPENAI_API_KEY não está definida!")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("SUPABASE_URL ou SUPABASE_KEY não estão definidas!")

openai.api_key = OPENAI_API_KEY
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
    user_id: str
    prompt: str

# =========================
# Endpoint /generate
# =========================
@app.post("/generate")
def generate(req: GenRequest):
    # Valida prompt
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt não pode estar vazio")

    try:
        # Chamada nova API OpenAI
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

        # Salva no Supabase
        supabase.table("projects").insert({
            "user_id": req.user_id,
            "prompt": req.prompt,
            "llm_output": llm_output
        }).execute()

        return {"llm_output": llm_output}

    except openai.error.OpenAIError as e:
        raise HTTPException(status_code=500, detail=f"Erro OpenAI: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")
