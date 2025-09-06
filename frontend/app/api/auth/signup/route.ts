import { type NextRequest, NextResponse } from "next/server"
import { createClient } from "@supabase/supabase-js"

const supabase = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_KEY!)

export async function POST(request: NextRequest) {
  try {
    const { email, password } = await request.json()

    const { data: authData, error: authError } = await supabase.auth.signUp({
      email,
      password,
    })

    if (authError) {
      return NextResponse.json({ success: false, error: authError.message }, { status: 400 })
    }

    const { data: userData, error: userError } = await supabase
      .from("users")
      .insert([{ email, plan: "free" }])
      .select()
      .single()

    if (userError) {
      return NextResponse.json({ success: false, error: userError.message }, { status: 500 })
    }

    return NextResponse.json({
      success: true,
      user: {
        id: userData.id,
        email: userData.email,
      },
    })
  } catch (error) {
    console.error("Signup error:", error)
    return NextResponse.json({ success: false, error: "Internal server error" }, { status: 500 })
  }
}
