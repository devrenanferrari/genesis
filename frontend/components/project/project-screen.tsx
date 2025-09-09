"use client"

import { useState } from "react"
import { useUser } from "@supabase/auth-helpers-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"

export default function ProjectScreen() {
  const user = useUser()
  const [prompt, setPrompt] = useState("")
  const [files, setFiles] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  const generateProject = async () => {
    if (!user) {
      alert("Você precisa estar logado para gerar um projeto.")
      return
    }

    setLoading(true)

    try {
      const res = await fetch(
        "https://genesis-production-389e.up.railway.app/generate_project",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: user.id,
            prompt,
          }),
        }
      )

      if (!res.ok) {
        throw new Error(`Erro na API: ${res.statusText}`)
      }

      const data = await res.json()
      setFiles(data.files || [])
    } catch (err) {
      console.error(err)
      alert("Erro ao gerar projeto.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <Card className="shadow-lg rounded-2xl border border-gray-700 bg-gray-900 text-white">
        <CardContent className="p-6 space-y-4">
          <h1 className="text-2xl font-bold text-center">Gerar Projeto</h1>

          <Input
            placeholder="Descreva seu projeto..."
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="bg-gray-800 border-gray-600 text-white"
          />

          <Button
            onClick={generateProject}
            disabled={loading}
            className="w-full"
          >
            {loading ? "Gerando..." : "Gerar"}
          </Button>

          {files.length > 0 && (
            <div className="mt-6 space-y-2">
              <h2 className="text-lg font-semibold">Arquivos gerados:</h2>
              <ul className="list-disc list-inside space-y-1 text-sm">
                {files.map((file, idx) => (
                  <li key={idx}>{file.filename}</li>
                ))}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
