"use client"

import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Sparkles, FolderOpen, Settings, LogOut, Plus, User } from "lucide-react"

interface SidebarProps {
  user: {
    email: string
    plan: string
  }
  onNewProject: () => void
  onLogout: () => void
  activeView: "chat" | "projects" | "settings"
  onViewChange: (view: "chat" | "projects" | "settings") => void
}

export function Sidebar({ user, onNewProject, onLogout, activeView, onViewChange }: SidebarProps) {
  const menuItems = [
    { id: "chat" as const, label: "New Project", icon: Plus },
    { id: "projects" as const, label: "My Projects", icon: FolderOpen },
    { id: "settings" as const, label: "Settings", icon: Settings },
  ]

  return (
    <div className="w-64 bg-sidebar border-r border-sidebar-border flex flex-col h-full">
      {/* Header */}
      <div className="p-6 border-b border-sidebar-border">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 bg-sidebar-primary rounded-lg">
            <Sparkles className="w-5 h-5 text-sidebar-primary-foreground" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-sidebar-foreground font-heading">Genesis</h1>
            <p className="text-xs text-muted-foreground">AI Code Generator</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex-1 p-4 space-y-2">
        {menuItems.map((item) => (
          <Button
            key={item.id}
            variant={activeView === item.id ? "default" : "ghost"}
            className={`w-full justify-start gap-3 h-10 ${
              activeView === item.id
                ? "bg-sidebar-primary text-sidebar-primary-foreground"
                : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
            }`}
            onClick={() => onViewChange(item.id)}
          >
            <item.icon className="w-4 h-4" />
            {item.label}
          </Button>
        ))}
      </div>

      <Separator className="bg-sidebar-border" />

      {/* User section */}
      <div className="p-4 space-y-3">
        <div className="flex items-center gap-3 p-3 rounded-lg bg-sidebar-accent/10">
          <div className="flex items-center justify-center w-8 h-8 bg-sidebar-accent rounded-full">
            <User className="w-4 h-4 text-sidebar-accent-foreground" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-sidebar-foreground truncate">{user.email}</p>
            <p className="text-xs text-muted-foreground capitalize">{user.plan} plan</p>
          </div>
        </div>

        <Button
          variant="ghost"
          className="w-full justify-start gap-3 h-10 text-sidebar-foreground hover:bg-destructive hover:text-destructive-foreground"
          onClick={onLogout}
        >
          <LogOut className="w-4 h-4" />
          Sign out
        </Button>
      </div>
    </div>
  )
}
