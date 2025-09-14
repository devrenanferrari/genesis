Vamos criar uma aplicação de finanças usando Next.js com o App Router. Esta aplicação permitirá que os usuários vejam um resumo de suas despesas e receitas, além de adicionar novas transações. Vamos usar Tailwind CSS e Shadcn/UI para o estilo.

### Estrutura do Projeto

1. **Página Inicial**: Exibe o resumo financeiro.
2. **Formulário de Transações**: Permite adicionar novas transações.
3. **Lista de Transações**: Mostra todas as transações.

### Passo a Passo

#### 1. Configuração Inicial

Primeiro, vamos configurar o projeto Next.js com Tailwind CSS e Shadcn/UI.

```bash
npx create-next-app@latest finance-app
cd finance-app
npm install tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

Configure o `tailwind.config.js`:

```javascript
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
```

Adicione o Tailwind aos estilos globais em `styles/globals.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

#### 2. Criar Componentes

Vamos criar os componentes principais: `ResumoFinanceiro`, `FormularioTransacao`, e `ListaTransacoes`.

<CodeProject id="finance_app">

  tsx file="components/resumo-financeiro.tsx"
  export default function ResumoFinanceiro() {
    return (
      <div className="p-4 bg-white rounded shadow-md">
        <h2 className="text-xl font-bold">Resumo Financeiro</h2>
        <p>Total de Receitas: R$ 0,00</p>
        <p>Total de Despesas: R$ 0,00</p>
      </div>
    )
  }

  tsx file="components/formulario-transacao.tsx"
  import { Button } from "@/components/ui/button"

  export default function FormularioTransacao() {
    return (
      <form className="flex flex-col gap-4 p-4 bg-white rounded shadow-md">
        <input className="border p-2 rounded" placeholder="Descrição" />
        <input className="border p-2 rounded" type="number" placeholder="Valor" />
        <Button>Adicionar Transação</Button>
      </form>
    )
  }

  tsx file="components/lista-transacoes.tsx"
  export default function ListaTransacoes() {
    return (
      <div className="p-4 bg-white rounded shadow-md">
        <h2 className="text-xl font-bold">Transações</h2>
        <ul>
          <li>Sem transações</li>
        </ul>
      </div>
    )
  }

  tsx file="app/page.tsx"
  import ResumoFinanceiro from "@/components/resumo-financeiro"
  import FormularioTransacao from "@/components/formulario-transacao"
  import ListaTransacoes from "@/components/lista-transacoes"

  export default function Home() {
    return (
      <main className="flex flex-col gap-4 p-10">
        <ResumoFinanceiro />
        <FormularioTransacao />
        <ListaTransacoes />
      </main>
    )
  }

</CodeProject>

#### 3. Executar o Projeto

Para iniciar o projeto, execute:

```bash
npm run dev
```

Acesse `http://localhost:3000` para ver a aplicação em execução.

### Boas Práticas

- **Acessibilidade**: Certifique-se de usar rótulos apropriados e roles ARIA.
- **Responsividade**: Use classes do Tailwind para garantir que a aplicação funcione bem em diferentes tamanhos de tela.
- **Organização**: Mantenha os componentes bem organizados e separados em arquivos.

<Actions>
  <Action name="Adicionar autenticação" description="Criar fluxo de cadastro e login com Supabase" />
  <Action name="Implementar armazenamento de dados" description="Usar um banco de dados como Supabase ou Firebase para persistência" />
  <Action name="Adicionar gráficos" description="Visualizar dados financeiros com gráficos usando Chart.js ou Recharts" />
  <Action name="Implementar notificações" description="Adicionar alertas para transações importantes ou metas atingidas" />
</Actions>