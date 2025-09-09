// src/lib/api.ts
const API_URL = "https://genesis-production-389e.up.railway.app"

export async function generateProject(prompt: string, user_id: string) {
  const res = await fetch(`${API_URL}/generate_project`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ prompt, user_id }),
  })
  if (!res.ok) throw new Error("Erro ao gerar projeto")
  return res.json()
}

export async function signup(email: string, password: string) {
  const res = await fetch(`${API_URL}/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  })
  return res.json()
}

export async function login(email: string, password: string) {
  const res = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  })
  return res.json()
}
