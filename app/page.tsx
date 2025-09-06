"use client"
import { useState, useEffect } from "react"
import LoginScreen from "@/components/auth/login-screen"
import HomeScreen from "@/components/home/home-screen"
import ProjectScreen from "@/components/project/project-screen"

type Screen = "login" | "home" | "project"

interface User {
  id: string
  email: string
}

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<Screen>("login")
  const [user, setUser] = useState<User | null>(null)
  const [currentPrompt, setCurrentPrompt] = useState("")

  // Check if user is logged in on mount
  useEffect(() => {
    const savedUser = localStorage.getItem("genesis_user")
    if (savedUser) {
      setUser(JSON.parse(savedUser))
      setCurrentScreen("home")
    }
  }, [])

  const handleLogin = (userData: User) => {
    setUser(userData)
    localStorage.setItem("genesis_user", JSON.stringify(userData))
    setCurrentScreen("home")
  }

  const handleLogout = () => {
    setUser(null)
    localStorage.removeItem("genesis_user")
    setCurrentScreen("login")
  }

  const handleStartProject = (prompt: string) => {
    setCurrentPrompt(prompt)
    setCurrentScreen("project")
  }

  const handleBackToHome = () => {
    setCurrentScreen("home")
    setCurrentPrompt("")
  }

  if (currentScreen === "login") {
    return <LoginScreen onLogin={handleLogin} />
  }

  if (currentScreen === "home") {
    return <HomeScreen user={user!} onLogout={handleLogout} onStartProject={handleStartProject} />
  }

  if (currentScreen === "project") {
    return <ProjectScreen user={user!} prompt={currentPrompt} onBack={handleBackToHome} onLogout={handleLogout} />
  }

  return null
}
