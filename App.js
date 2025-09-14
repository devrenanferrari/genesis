Para criar uma aplicação de finanças completa, vamos expandir a estrutura inicial com funcionalidades adicionais, como persistência de dados, autenticação e visualização de relatórios. Vamos usar Next.js com o App Router, Tailwind CSS, shadcn/ui e Supabase para o backend.

### Estrutura do Projeto

1. **Página Inicial**: Exibe uma lista de transações.
2. **Formulário de Transação**: Permite adicionar novas transações.
3. **Autenticação**: Fluxo de login e cadastro.
4. **Persistência de Dados**: Armazenamento de transações no Supabase.
5. **Relatórios**: Visualização gráfica de despesas e receitas.

Vamos criar o projeto completo:

<CodeProject id="complete_finance_app">

  tsx file="app/page.tsx"
  import { TransactionForm } from "@/components/transaction-form"
  import { TransactionList } from "@/components/transaction-list"
  import { useSession } from "@/lib/auth"

  export default function HomePage() {
    const { user } = useSession()

    if (!user) {
      return <p>Por favor, faça login para ver suas finanças.</p>
    }

    return (
      <main className="container mx-auto p-4">
        <h1 className="text-2xl font-bold mb-4">Minhas Finanças</h1>
        <TransactionForm />
        <TransactionList />
      </main>
    )
  }

  tsx file="components/transaction-form.tsx"
  import { Button } from "@/components/ui/button"
  import { useState } from "react"
  import { useSupabase } from "@/lib/supabase"

  export function TransactionForm() {
    const [amount, setAmount] = useState("")
    const [description, setDescription] = useState("")
    const { supabase } = useSupabase()

    const handleSubmit = async (e) => {
      e.preventDefault()
      const { data, error } = await supabase
        .from('transactions')
        .insert([{ description, amount: parseFloat(amount) }])
      
      if (error) console.error("Erro ao adicionar transação:", error)
      else console.log("Transação adicionada:", data)
    }

    return (
      <form onSubmit={handleSubmit} className="flex flex-col gap-4 mb-8">
        <input
          className="border p-2 rounded"
          placeholder="Descrição"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <input
          className="border p-2 rounded"
          type="number"
          placeholder="Valor"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
        <Button type="submit">Adicionar Transação</Button>
      </form>
    )
  }

  tsx file="components/transaction-list.tsx"
  import { useEffect, useState } from "react"
  import { useSupabase } from "@/lib/supabase"

  export function TransactionList() {
    const [transactions, setTransactions] = useState([])
    const { supabase } = useSupabase()

    useEffect(() => {
      const fetchTransactions = async () => {
        const { data, error } = await supabase
          .from('transactions')
          .select('*')
        
        if (error) console.error("Erro ao buscar transações:", error)
        else setTransactions(data)
      }

      fetchTransactions()
    }, [supabase])

    return (
      <ul className="space-y-2">
        {transactions.map((transaction) => (
          <li key={transaction.id} className="border p-2 rounded flex justify-between">
            <span>{transaction.description}</span>
            <span>R$ {transaction.amount}</span>
          </li>
        ))}
      </ul>
    )
  }

  ts file="lib/auth.ts"
  import { createContext, useContext, useEffect, useState } from "react"
  import { useSupabase } from "@/lib/supabase"

  const AuthContext = createContext(null)

  export function AuthProvider({ children }) {
    const { supabase } = useSupabase()
    const [user, setUser] = useState(null)

    useEffect(() => {
      const session = supabase.auth.session()
      setUser(session?.user ?? null)

      const { data: authListener } = supabase.auth.onAuthStateChange(
        async (event, session) => {
          setUser(session?.user ?? null)
        }
      )

      return () => {
        authListener?.unsubscribe()
      }
    }, [supabase])

    return (
      <AuthContext.Provider value={{ user }}>
        {children}
      </AuthContext.Provider>
    )
  }

  export function useSession() {
    return useContext(AuthContext)
  }

  ts file="lib/supabase.ts"
  import { createClient } from '@supabase/supabase-js'

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

  export const supabase = createClient(supabaseUrl, supabaseAnonKey)

  export function useSupabase() {
    return { supabase }
  }

</CodeProject>

### Próximos Passos

<Actions>
  <Action name="Implementar gráficos" description="Adicionar gráficos para visualização de despesas e receitas usando bibliotecas como Chart.js." />
  <Action name="Melhorar autenticação" description="Adicionar recuperação de senha e autenticação social (Google, Facebook)." />
  <Action name="Adicionar categorias" description="Permitir que usuários categorizem transações para melhor organização." />
  <Action name="Exportar dados" description="Habilitar exportação de dados financeiros para CSV ou PDF." />
</Actions>

Essa aplicação agora inclui autenticação e persistência de dados usando Supabase, permitindo que os usuários gerenciem suas finanças de forma segura e eficiente.