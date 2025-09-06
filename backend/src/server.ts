import express from "express"
import cors from "cors"
import dotenv from "dotenv"
import { createClient } from "@supabase/supabase-js"
import OpenAI from "openai"

dotenv.config()

const app = express()
const PORT = process.env.PORT || 8000

// Environment variables
const OPENAI_API_KEY = process.env.OPENAI_API_KEY
const SUPABASE_URL = process.env.SUPABASE_URL
const SUPABASE_KEY = process.env.SUPABASE_KEY

if (!OPENAI_API_KEY || !SUPABASE_URL || !SUPABASE_KEY) {
  console.error("Missing required environment variables")
  process.exit(1)
}

// Initialize clients
const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)
const openai = new OpenAI({ apiKey: OPENAI_API_KEY })

// CORS configuration
const origins = [
  "http://localhost:3000",
  "https://genesis-k2ykslrzq-devrenanferraris-projects.vercel.app",
  "https://genesis-swart-nu.vercel.app",
]

app.use(
  cors({
    origin: origins,
    credentials: true,
    methods: ["*"],
    allowedHeaders: ["*"],
  }),
)

app.use(express.json())

// Types
interface LoginRequest {
  email: string
  password: string
}

interface SignupRequest {
  email: string
  password: string
}

interface GenRequest {
  user_id?: string
  prompt: string
}

// Routes
app.get("/", (req, res) => {
  res.json({ message: "Genesis API is running", status: "ok" })
})

app.get("/health", (req, res) => {
  res.json({
    status: "healthy",
    openai_configured: !!OPENAI_API_KEY,
    supabase_configured: !!(SUPABASE_URL && SUPABASE_KEY),
  })
})

app.post("/auth/login", async (req, res) => {
  try {
    const { email, password }: LoginRequest = req.body

    const response = await supabase.auth.signInWithPassword({
      email,
      password,
    })

    if (response.data.user) {
      res.json({
        success: true,
        user: {
          id: response.data.user.id,
          email: response.data.user.email,
        },
        session: response.data.session?.access_token || null,
      })
    } else {
      res.status(401).json({ detail: "Invalid credentials" })
    }
  } catch (error: any) {
    console.log(`Login error: ${error.message}`)
    res.status(401).json({ detail: `Login failed: ${error.message}` })
  }
})

app.post("/auth/signup", async (req, res) => {
  try {
    const { email, password }: SignupRequest = req.body

    const response = await supabase.auth.signUp({
      email,
      password,
    })

    if (response.data.user) {
      try {
        await supabase.from("users").insert({
          id: response.data.user.id,
          email,
          plan: "free",
        })
      } catch (dbError: any) {
        console.log(`Database insert error: ${dbError.message}`)
        // Continue even if user table insert fails
      }

      res.json({
        success: true,
        user: {
          id: response.data.user.id,
          email: response.data.user.email,
        },
      })
    } else {
      res.status(400).json({ detail: "Signup failed" })
    }
  } catch (error: any) {
    console.log(`Signup error: ${error.message}`)
    res.status(400).json({ detail: `Signup failed: ${error.message}` })
  }
})

app.get("/auth/user/:user_id", async (req, res) => {
  try {
    const { user_id } = req.params
    const response = await supabase.from("users").select("*").eq("id", user_id).single()

    if (response.data) {
      res.json({ user: response.data })
    } else {
      res.status(404).json({ detail: "User not found" })
    }
  } catch (error: any) {
    res.status(500).json({ detail: `Error fetching user: ${error.message}` })
  }
})

app.get("/projects/:user_id", async (req, res) => {
  try {
    const { user_id } = req.params
    const response = await supabase
      .from("projects")
      .select("*")
      .eq("user_id", user_id)
      .order("created_at", { ascending: false })

    res.json({ projects: response.data })
  } catch (error: any) {
    res.status(500).json({ detail: `Error fetching projects: ${error.message}` })
  }
})

const generateProject = async (req: express.Request, res: express.Response) => {
  try {
    const { user_id, prompt } = req.body

    console.log(`[DEBUG] Received request: user_id=${user_id}, prompt=${prompt?.substring(0, 50)}...`)

    if (!user_id) {
      return res.status(401).json({ detail: "User ID required" })
    }

    if (!OPENAI_API_KEY) {
      return res.status(500).json({ detail: "OpenAI API key not configured" })
    }

    // System message for LLM
    const systemMsg =
      "Você é um gerador de projetos completos. " +
      "Crie os arquivos do projeto separados, indicando o nome de cada arquivo e seu conteúdo em JSON. " +
      'Exemplo de resposta JSON: {"App.js": "conteúdo do App.js", "index.html": "conteúdo do index.html"} ' +
      "Inclua também um README.md explicando o projeto."

    console.log("[DEBUG] Calling OpenAI API...")
    const response = await openai.chat.completions.create({
      model: "gpt-4o",
      messages: [
        { role: "system", content: systemMsg },
        { role: "user", content: prompt },
      ],
      temperature: 0.2,
      max_tokens: 4000,
    })

    const content = response.choices[0].message.content || ""
    console.log(`[DEBUG] OpenAI response received, length: ${content.length}`)

    // Try to parse as JSON
    let files: Record<string, string>
    try {
      files = JSON.parse(content)
      console.log(`[DEBUG] Successfully parsed JSON with ${Object.keys(files).length} files`)
    } catch (jsonError) {
      console.log(`[DEBUG] JSON parsing failed: ${jsonError}`)
      // If parsing fails, put everything in App.js
      files = { "App.js": content, "README.md": `# Projeto: ${prompt}` }
    }

    try {
      console.log("[DEBUG] Saving to Supabase...")
      await supabase.from("projects").insert({
        user_id,
        prompt,
        llm_output: content,
      })
      console.log("[DEBUG] Successfully saved to Supabase")
    } catch (dbError: any) {
      console.log(`[DEBUG] Supabase error: ${dbError.message}`)
      // Continue even if database save fails
    }

    console.log(`[DEBUG] Successfully generated project with ${Object.keys(files).length} files`)
    res.json({
      user_id,
      llm_output: content,
      files,
    })
  } catch (error: any) {
    console.log(`[ERROR] generate_project failed: ${error.message}`)
    res.status(500).json({ detail: `Erro no backend: ${error.message}` })
  }
}

app.post("/generate_project", generateProject)

app.post("/generate", generateProject)

app.listen(PORT, () => {
  console.log(`Genesis backend running on port ${PORT}`)
})
