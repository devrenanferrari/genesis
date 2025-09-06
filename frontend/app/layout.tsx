// frontend/app/layout.tsx
import './globals.css';

export const metadata = {
  title: 'Gerador de Projetos IA',
  description: 'Frontend do projeto IA',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
