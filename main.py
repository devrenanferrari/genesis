# backend/main.py
from fastapi import FastAPI
from pydantic import BaseModel
import os
import openai
from supabase import create_client

# Variáveis de ambiente
openai.api_key = os.getenv("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")
SUPABASE_URL = os.getenv("https://qoriipqcqmmrrqkeztwo.supabase.co")
SUPABASE_KEY = os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFvcmlpcHFjcW1tcnJxa2V6dHdvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTcxMTY1OTgsImV4cCI6MjA3MjY5MjU5OH0._TIjiv91FvJonj190S6TLN2s8XfLOf2iAEufOrwgyfk")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

class GenRequest(BaseModel):
    user_id: str
    prompt: str

@app.post("/generate")
def generate(req: GenRequest):
    # 1) Chamar LLM
    response = openai.ChatCompletion.create(
        model="gpt-4.1",
        messages=[
            {"role":"system","content":"Você é um gerador de código confiável."},
            {"role":"user","content": req.prompt}
        ],
        temperature=0.2,
        max_tokens=2000
    )
    llm_output = response.choices[0].message.content

    # 2) Salvar no Supabase
    supabase.table("projects").insert({
        "user_id": req.user_id,
        "prompt": req.prompt,
        "llm_output": llm_output
    }).execute()

    return {"llm_output": llm_output}
