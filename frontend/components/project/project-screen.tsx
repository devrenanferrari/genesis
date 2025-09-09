"use client"
import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { ArrowLeft, Loader2, FileText, Copy, Check, LogOut } from "lucide-react"
import { User } from "lucide-react" // Import User component

interface ProjectScreenProps {
  user: { id: string; email: string }
  prompt: string
  onBack: () => void
  onLogout: () => void
}

export default function ProjectScreen({ user, prompt, onBack, onLogout }: ProjectScreenProps) {
  const [files, setFiles] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [copiedFile, setCopiedFile] = useState<string | null>(null)

  useEffect(() => {
    generateProject()
  }, [])

  const generateProject = async () => {
    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: user.id,
          prompt,
        }),
      })

      if (!res.ok) {
        throw new Error("Failed to generate project")
      }

      const data = await res.json()
      setFiles(data.files)
    } catch (error) {
      console.error("Error:", error)
      alert("Error generating project. Please try again.")
    } finally {
      setLoading(false)
    }
  }

  const copyToClipboard = async (filename: string, content: string) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopiedFile(filename)
      setTimeout(() => setCopiedFile(null), 2000)
    } catch (error) {
      console.error("Failed to copy:", error)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <header className="border-b border-slate-700 bg-slate-800/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={onBack}
                className="text-slate-400 hover:text-white hover:bg-slate-700"
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
              <div>
                <h1 className="text-xl font-bold text-white">Project Generation</h1>
                <p className="text-sm text-slate-400 truncate max-w-md">{prompt}</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-slate-300">
                <User className="w-4 h-4" /> {/* User component used here */}
                <span className="text-sm">{user.email}</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={onLogout}
                className="text-slate-400 hover:text-white hover:bg-slate-700"
              >
                <LogOut className="w-4 h-4 mr-2" />
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 max-w-6xl">
        <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-white">
                  <FileText className="w-5 h-5 text-cyan-400" />
                  Generated Files
                </CardTitle>
                <CardDescription className="text-slate-400">
                  {loading
                    ? "Generating your project files..."
                    : `${Object.keys(files).length} files created successfully`}
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center justify-center py-20">
                <div className="text-center space-y-4">
                  <Loader2 className="w-12 h-12 animate-spin text-cyan-400 mx-auto" />
                  <div className="space-y-2">
                    <p className="text-white font-medium">Generating your project...</p>
                    <p className="text-slate-400 text-sm">This may take a few moments</p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                {Object.entries(files).map(([filename, content]) => (
                  <Card key={filename} className="bg-slate-700/30 border-slate-600">
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-base font-mono text-cyan-400">{filename}</CardTitle>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => copyToClipboard(filename, content)}
                          className="text-slate-400 hover:text-white hover:bg-slate-600"
                        >
                          {copiedFile === filename ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                        </Button>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <pre className="text-sm bg-slate-900/50 p-4 rounded-lg overflow-x-auto border border-slate-600 font-mono leading-relaxed text-slate-200 max-h-96 overflow-y-auto">
                        {content}
                      </pre>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
