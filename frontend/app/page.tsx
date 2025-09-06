"use client";
import { useState, useEffect } from "react";
import Editor from "@monaco-editor/react";

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);

  // Ao carregar a página, verifica se já existe user_id no localStorage
  useEffect(() => {
    const storedId = localStorage.getItem("user_id");
    if (storedId) setUserId(storedId);
  }, []);

  async function handleGenerate() {
    if (!prompt.trim()) return; // evita enviar prompt vazio
    setLoading(true);

    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt,
        ...(userId ? { user_id: userId } : {}) // envia user_id somente se existir
      })
    });

    if (!res.ok) {
      const err = await res.json();
      setOutput(`Erro no backend: ${JSON.stringify(err)}`);
      setLoading(false);
      return;
    }

    const data = await res.json();
    setOutput(data.llm_output);

    // Salva user_id retornado para futuras requisições
    if (!userId && data.user_id) {
      localStorage.setItem("user_id", data.user_id);
      setUserId(data.user_id);
    }

    setLoading(false);
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">Gerador de Projetos IA</h1>
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Descreva o que quer..."
        className="w-full h-32 p-2 border"
      />
      <button
        onClick={handleGenerate}
        disabled={loading}
        className="mt-2 px-4 py-2 bg-blue-600 text-white rounded"
      >
        {loading ? "Gerando..." : "Gerar Projeto"}
      </button>

      <div className="mt-6">
        <h2 className="font-semibold">Saída do LLM</h2>
        <Editor
          height="60vh"
          defaultLanguage="text"
          value={output}
          options={{ readOnly: true }}
        />
      </div>
    </div>
  );
}
