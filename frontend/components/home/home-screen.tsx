"use client"
import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Sparkles, LogOut, History, Zap, Code2 } from "lucide-react"

interface Project {
  id: string
  prompt: string
  created_at: string
}

interface HomeScreenProps {
  user: any
  onLogout: () => void
  onStartProject: (prompt: string) => void
}

export default function HomeScreen({ user, onLogout, onStartProject }: HomeScreenProps) {
  const [prompt, setPrompt] = useState("")
  const [recentProjects, setRecentProjects] = useState<Project[]>([])

  useEffect(() => {
    fetchRecentProjects()
  }, [])

  const fetchRecentProjects = async () => {
    try {
      const res = await fetch(`https://genesis-backend-production.up.railway.app/projects/${user.id}`)
      if (res.ok) {
        const data = await res.json()
        setRecentProjects(data.projects.slice(0, 5))
      }
    } catch (error) {
      console.error("Error fetching projects:", error)
    }
  }

  const handleGenerate = () => {
    if (!prompt.trim()) return
    onStartProject(prompt)
  }

  const examplePrompts = [
    "Uma landing page moderna para uma startup de IA",
    "Sistema de gerenciamento de tarefas com React",
    "API REST para e-commerce com autenticação",
    "Dashboard administrativo com gráficos",
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <header className="border-b border-slate-700 bg-slate-800/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 bg-cyan-500 rounded-lg">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">Genesis</h1>
                <p className="text-sm text-slate-400">AI Code Generator</p>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-slate-300">
                <Code2 className="w-4 h-4" />
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

      <main className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Hero Section */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 bg-cyan-500/10 text-cyan-400 px-4 py-2 rounded-full text-sm font-medium mb-6 border border-cyan-500/20">
            <Zap className="w-4 h-4" />
            Powered by OpenAI GPT-4
          </div>
          <h2 className="text-4xl md:text-5xl font-bold text-balance mb-4 text-white">What will you build today?</h2>
          <p className="text-xl text-slate-400 text-balance max-w-2xl mx-auto">
            Describe your project and our AI will create all the files you need, ready to use.
          </p>
        </div>

        {/* Input Section */}
        <Card className="mb-8 bg-slate-800/50 border-slate-700 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-white">
              <Code2 className="w-5 h-5 text-cyan-400" />
              Describe your project
            </CardTitle>
            <CardDescription className="text-slate-400">
              Be specific about features, technologies, and style you want
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Ex: Create a modern landing page for a tech company with hero, about, services and contact sections. Use React, Tailwind CSS and include smooth animations..."
              className="min-h-[120px] resize-none bg-slate-700/50 border-slate-600 text-white placeholder:text-slate-400 focus:border-cyan-500"
            />

            {/* Example Prompts */}
            <div className="space-y-2">
              <p className="text-sm font-medium text-slate-400">Popular examples:</p>
              <div className="flex flex-wrap gap-2">
                {examplePrompts.map((example, index) => (
                  <Badge
                    key={index}
                    variant="secondary"
                    className="cursor-pointer bg-slate-700/50 text-slate-300 hover:bg-slate-600 hover:text-white transition-colors border-slate-600"
                    onClick={() => setPrompt(example)}
                  >
                    {example}
                  </Badge>
                ))}
              </div>
            </div>

            <Button
              onClick={handleGenerate}
              disabled={!prompt.trim()}
              className="w-full h-12 text-base font-semibold bg-cyan-500 hover:bg-cyan-600 text-white"
              size="lg"
            >
              <Sparkles className="w-5 h-5 mr-2" />
              Generate Project
            </Button>
          </CardContent>
        </Card>

        {/* Recent Projects */}
        {recentProjects.length > 0 && (
          <Card className="bg-slate-800/50 border-slate-700 backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-white">
                <History className="w-5 h-5 text-cyan-400" />
                Recent Projects
              </CardTitle>
              <CardDescription className="text-slate-400">Your latest generated projects</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {recentProjects.map((project) => (
                  <div
                    key={project.id}
                    className="p-4 bg-slate-700/30 rounded-lg border border-slate-600 cursor-pointer hover:bg-slate-700/50 transition-colors"
                    onClick={() => onStartProject(project.prompt)}
                  >
                    <p className="text-white text-sm font-medium mb-1">{project.prompt}</p>
                    <p className="text-slate-400 text-xs">{new Date(project.created_at).toLocaleDateString()}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  )
}
