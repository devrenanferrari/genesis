"use client"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Loader2, Sparkles, Code2, Download, FileText, Zap } from "lucide-react"

export default function Home() {
  const [prompt, setPrompt] = useState("")
  const [files, setFiles] = useState<Record<string, string>>({})
  const [zipUrl, setZipUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleGenerate() {
    if (!prompt.trim()) return

    setFiles({})
    setZipUrl(null)
    setLoading(true)

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/generate_project`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      })

      if (!res.ok) {
        throw new Error("Erro na geração do projeto")
      }

      const data = await res.json()
      setFiles(data.files)
      setZipUrl(data.project_zip_url)
    } catch (error) {
      console.error("Erro:", error)
      alert("Erro ao gerar projeto. Tente novamente.")
    } finally {
      setLoading(false)
    }
  }

  const examplePrompts = [
    "Uma landing page moderna para uma startup de IA",
    "Sistema de gerenciamento de tarefas com React",
    "API REST para e-commerce com autenticação",
    "Dashboard administrativo com gráficos",
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-card to-background">
      {/* Header */}
      <header className="border-b border-border bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 bg-primary rounded-lg">
              <Sparkles className="w-6 h-6 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">Genesis AI</h1>
              <p className="text-sm text-muted-foreground">Gerador de Projetos Inteligente</p>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-6xl">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 bg-secondary text-secondary-foreground px-4 py-2 rounded-full text-sm font-medium mb-6">
            <Zap className="w-4 h-4" />
            Powered by OpenAI GPT-4
          </div>
          <h2 className="text-4xl md:text-5xl font-bold text-balance mb-4 bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent">
            Transforme suas ideias em código funcional
          </h2>
          <p className="text-xl text-muted-foreground text-balance max-w-2xl mx-auto">
            Descreva seu projeto e nossa IA criará todos os arquivos necessários, prontos para uso.
          </p>
        </div>

        {/* Input Section */}
        <Card className="mb-8 shadow-lg border-0 bg-card/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Code2 className="w-5 h-5 text-primary" />
              Descreva seu projeto
            </CardTitle>
            <CardDescription>Seja específico sobre as funcionalidades, tecnologias e estilo que deseja</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Ex: Crie uma landing page moderna para uma empresa de tecnologia com seções hero, sobre, serviços e contato. Use React, Tailwind CSS e inclua animações suaves..."
              className="min-h-[120px] resize-none border-0 bg-input/50 focus:bg-input text-base"
              disabled={loading}
            />

            {/* Example Prompts */}
            <div className="space-y-2">
              <p className="text-sm font-medium text-muted-foreground">Exemplos populares:</p>
              <div className="flex flex-wrap gap-2">
                {examplePrompts.map((example, index) => (
                  <Badge
                    key={index}
                    variant="secondary"
                    className="cursor-pointer hover:bg-accent hover:text-accent-foreground transition-colors"
                    onClick={() => setPrompt(example)}
                  >
                    {example}
                  </Badge>
                ))}
              </div>
            </div>

            <Button
              onClick={handleGenerate}
              disabled={loading || !prompt.trim()}
              className="w-full h-12 text-base font-semibold"
              size="lg"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                  Gerando projeto...
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5 mr-2" />
                  Gerar Projeto
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Results Section */}
        {(Object.keys(files).length > 0 || loading) && (
          <Card className="shadow-lg border-0 bg-card/50 backdrop-blur-sm">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="w-5 h-5 text-primary" />
                    Arquivos Gerados
                  </CardTitle>
                  <CardDescription>
                    {Object.keys(files).length > 0
                      ? `${Object.keys(files).length} arquivos criados com sucesso`
                      : "Gerando arquivos do projeto..."}
                  </CardDescription>
                </div>
                {zipUrl && (
                  <Button asChild variant="outline" className="gap-2 bg-transparent">
                    <a href={zipUrl} download="project.zip">
                      <Download className="w-4 h-4" />
                      Baixar ZIP
                    </a>
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="text-center space-y-4">
                    <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto" />
                    <p className="text-muted-foreground">Processando com IA...</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {Object.entries(files).map(([filename, content]) => (
                    <Card key={filename} className="border border-border/50">
                      <CardHeader className="pb-3">
                        <CardTitle className="text-base font-mono">{filename}</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <pre className="text-sm bg-muted/50 p-4 rounded-lg overflow-x-auto border border-border/30 font-mono leading-relaxed">
                          {content}
                        </pre>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-card/30 mt-16">
        <div className="container mx-auto px-4 py-8 text-center">
          <p className="text-muted-foreground">Desenvolvido com ❤️ usando Next.js, OpenAI e Supabase</p>
        </div>
      </footer>
    </div>
  )
}
