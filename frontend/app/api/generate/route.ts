import { type NextRequest, NextResponse } from "next/server"
import { createClient } from "@supabase/supabase-js"

const supabase = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_KEY!)

export async function POST(request: NextRequest) {
  try {
    const { prompt, user_id } = await request.json()

    const openaiResponse = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "gpt-4",
        messages: [
          {
            role: "system",
            content: `You are a React project generator. Generate a complete React project with multiple files based on the user's request. 
            Return a JSON object with "files" key containing an object where keys are file paths and values are the file contents.
            Include files like: App.tsx, components/*.tsx, styles/*.css, etc.
            Example format: {"files": {"App.tsx": "import React...", "components/Button.tsx": "export default function Button..."}}`,
          },
          {
            role: "user",
            content: prompt,
          },
        ],
        max_tokens: 3000,
      }),
    })

    const openaiData = await openaiResponse.json()
    const generatedContent = openaiData.choices[0]?.message?.content || "Error generating code"

    let files = {}
    try {
      const parsed = JSON.parse(generatedContent)
      files = parsed.files || { "App.tsx": generatedContent }
    } catch {
      // If not JSON, treat as single file
      files = { "App.tsx": generatedContent }
    }

    // Save project to database
    const { data: project, error } = await supabase
      .from("projects")
      .insert([
        {
          user_id,
          prompt,
          llm_output: JSON.stringify(files),
        },
      ])
      .select()
      .single()

    if (error) {
      console.error("Database error:", error)
      return NextResponse.json({ success: false, error: "Failed to save project" }, { status: 500 })
    }

    return NextResponse.json({
      success: true,
      files,
      project: {
        id: project.id,
        prompt,
      },
    })
  } catch (error) {
    console.error("Generate error:", error)
    return NextResponse.json({ success: false, error: "Internal server error" }, { status: 500 })
  }
}
