"use client";
import { useState, useEffect } from "react";
import Editor from "@monaco-editor/react";
import { v4 as uuidv4 } from "uuid";

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);
  const [userId, setUserId] = useState("");

  // =========================
  // Pega ou cria user_id no localStorage
  // =========================
  useEffect(() => {
    let storedId = localStorage.getItem("user_id");
    if (!storedId) {
      storedId = uuidv4();
      localStorage.setItem("user_id", storedId);
    }
    setUserId(storedId);
  }, []);

  async function handleGenerate() {
    setLoading(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, prompt })
      });
      const data = await res.json();
      setOutput(data.llm_output);
    } catch (err) {
      console.error("Erro ao gerar projeto:", err);
      setOutput("Erro ao gerar projeto. Veja o console para detalhes.");
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
        <Editor height="60vh" defaultLanguage="text" value={output} />
      </div>
    </div>
  );
}
