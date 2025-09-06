import { type NextRequest, NextResponse } from "next/server"
import { createClient } from "@supabase/supabase-js"

const supabase = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_KEY!)

export async function POST(request: NextRequest) {
  try {
    const { email, password } = await request.json()

    const { data: authData, error: authError } = await supabase.auth.signInWithPassword({
      email,
      password,
    })

    if (authError) {
      return NextResponse.json({ success: false, error: authError.message }, { status: 400 })
    }

    const { data: userData, error: userError } = await supabase.from("users").select("*").eq("email", email).single()

    let user = userData

    if (userError && userError.code === "PGRST116") {
      // User doesn't exist, create one
      const { data: newUser, error: createError } = await supabase
        .from("users")
        .insert([{ email, plan: "free" }])
        .select()
        .single()

      if (createError) {
        return NextResponse.json({ success: false, error: createError.message }, { status: 500 })
      }
      user = newUser
    }

    return NextResponse.json({
      success: true,
      user: {
        id: user.id,
        email: user.email,
      },
    })
  } catch (error) {
    console.error("Login error:", error)
    return NextResponse.json({ success: false, error: "Internal server error" }, { status: 500 })
  }
}
