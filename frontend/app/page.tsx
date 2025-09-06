"use client";
import { useState } from "react";
import Editor from "@monaco-editor/react";

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleGenerate() {
    setLoading(true);
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: "demo", prompt })
    });
    const data = await res.json();
    setOutput(data.llm_output);
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
      <button onClick={handleGenerate} disabled={loading} className="mt-2 px-4 py-2 bg-blue-600 text-white rounded">
        {loading ? "Gerando..." : "Gerar Projeto"}
      </button>

      <div className="mt-6">
        <h2 className="font-semibold">Saída do LLM</h2>
        <Editor height="60vh" defaultLanguage="text" value={output} />
      </div>
    </div>
  );
}
