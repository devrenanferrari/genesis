import os
from fastapi import FastAPI
from pydantic import BaseModel
import openai
from supabase import create_client

# Variáveis de ambiente corretas
openai.api_key = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Checa se estão definidas
if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Supabase URL ou KEY não estão definidas!")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

class GenRequest(BaseModel):
    user_id: str
    prompt: str

@app.post("/generate")
def generate(req: GenRequest):
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

    supabase.table("projects").insert({
        "user_id": req.user_id,
        "prompt": req.prompt,
        "llm_output": llm_output
    }).execute()

    return {"llm_output": llm_output}
