"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { FileText, Calendar, Trash2, ExternalLink, Code2 } from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import { ptBR } from "date-fns/locale"

interface ProjectCardProps {
  project: {
    id: string
    prompt: string
    created_at: string
    llm_output: string
  }
  onDelete: (id: string) => void
  onView: (project: any) => void
}

export function ProjectCard({ project, onDelete, onView }: ProjectCardProps) {
  const createdAt = new Date(project.created_at)
  const timeAgo = formatDistanceToNow(createdAt, { addSuffix: true, locale: ptBR })

  // Extract file count from llm_output
  let fileCount = 0
  try {
    const files = JSON.parse(project.llm_output)
    fileCount = Object.keys(files).length
  } catch {
    fileCount = 1
  }

  return (
    <Card className="group hover:shadow-lg transition-all duration-200 border-border/50 bg-card/80 backdrop-blur-sm hover:bg-card">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <div className="flex items-center justify-center w-8 h-8 bg-primary/10 rounded-lg">
              <Code2 className="w-4 h-4 text-primary" />
            </div>
            <div>
              <CardTitle className="text-base font-heading line-clamp-1">
                {project.prompt.length > 50 ? `${project.prompt.substring(0, 50)}...` : project.prompt}
              </CardTitle>
              <CardDescription className="flex items-center gap-2 mt-1">
                <Calendar className="w-3 h-3" />
                {timeAgo}
              </CardDescription>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(project.id)}
            className="opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="text-xs">
              <FileText className="w-3 h-3 mr-1" />
              {fileCount} {fileCount === 1 ? "arquivo" : "arquivos"}
            </Badge>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => onView(project)}
            className="gap-2 bg-transparent hover:bg-accent hover:text-accent-foreground"
          >
            <ExternalLink className="w-3 h-3" />
            Ver projeto
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
