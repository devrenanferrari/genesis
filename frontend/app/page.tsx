"use client";
import { useState, useEffect } from "react";
import Editor from "@monaco-editor/react";

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);

  // Ao carregar a página, tenta recuperar o userId do localStorage
  useEffect(() => {
    const storedId = localStorage.getItem("user_id");
    if (storedId) setUserId(storedId);
  }, []);

  async function handleGenerate() {
    setLoading(true);

    // Monta o corpo da requisição
    const body: any = { prompt };
    if (userId) body.user_id = userId;

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(errorText);
      }

      const data = await res.json();

      // Salva user_id no localStorage se for novo
      if (!userId && data.user_id) {
        localStorage.setItem("user_id", data.user_id);
        setUserId(data.user_id);
      }

      setOutput(data.llm_output);
    } catch (err: any) {
      console.error("Erro no backend:", err.message);
      setOutput(`Erro no backend: ${err.message}`);
    } finally {
      setLoading(false);
    }
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
        disabled={loading || !prompt.trim()}
        className="mt-2 px-4 py-2 bg-blue-600 text-white rounded"
      >
        {loading ? "Gerando..." : "Gerar Projeto"}
      </button>

      <div className="mt-6">
        <h2 className="font-semibold">Saída do LLM</h2>
        <Editor height="60vh" defaultLanguage="text" value={output} />
      </div>
    </div>
  );
}
