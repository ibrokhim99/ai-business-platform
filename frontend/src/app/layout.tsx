import type { Metadata } from 'next';
import './globals.css';
import { AuthProvider } from '@/lib/auth';
import { ThemeProvider } from '@/lib/theme';

export const metadata: Metadata = {
  title: 'BizIQ — AI Biznes Tahlilchisi',
  description: 'Bozor hajmi, prognoz, joylashuv, moliyaviy va kredit tahlili uchun suhbat shaklidagi AI.',
};

// Anti-FOUC: apply theme class before React hydrates
const themeScript = `
(function(){try{
  var s=localStorage.getItem('biziq_theme')||'system';
  var d=window.matchMedia('(prefers-color-scheme: dark)').matches;
  var e=s==='system'?(d?'dark':'light'):s;
  if(e==='dark')document.documentElement.classList.add('dark');
  document.documentElement.style.colorScheme=e;
}catch(_){}})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="h-full bg-canvas text-fg">
        <ThemeProvider>
          <AuthProvider>{children}</AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
