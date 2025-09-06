"use client";
import { useState } from "react";

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [files, setFiles] = useState<Record<string, string>>({});
  const [zipUrl, setZipUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleGenerate() {
    setFiles({});
    setZipUrl(null);
    setLoading(true);

    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/generate_project`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt })
    });

    if (!res.ok) {
      alert("Erro no backend");
      setLoading(false);
      return;
    }

    const data = await res.json();
    setFiles(data.files);
    setZipUrl(data.project_zip_url);
    setLoading(false);
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">Gerador de Projetos IA - v0 Lovable</h1>

      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Descreva o projeto que deseja..."
        className="w-full h-32 p-2 border"
      />

      <button onClick={handleGenerate} disabled={loading} className="mt-2 px-4 py-2 bg-blue-600 text-white rounded">
        {loading ? "Gerando..." : "Gerar Projeto"}
      </button>

      <div className="mt-6">
        <h2 className="font-semibold">Arquivos Gerados</h2>
        {Object.entries(files).map(([fname, content]) => (
          <div key={fname} className="my-2">
            <h3 className="font-medium">{fname}</h3>
            <pre className="p-2 bg-gray-100 rounded overflow-x-auto">{content}</pre>
          </div>
        ))}
      </div>

      {zipUrl && (
        <div className="mt-4">
          <a href={zipUrl} download="project.zip" className="px-4 py-2 bg-green-600 text-white rounded">
            Baixar Projeto Completo
          </a>
        </div>
      )}
    </div>
  );
}
