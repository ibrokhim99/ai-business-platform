'use client';

import { useState, FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { AlertTriangle } from 'lucide-react';
import { QuickThemeToggle } from '@/components/notebook/ThemeToggle';

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState('admin@bank.uz');
  const [password, setPassword] = useState('admin123');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      router.push('/');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Kirishda xatolik yuz berdi.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-canvas flex flex-col">
      <div className="flex justify-end p-4">
        <QuickThemeToggle />
      </div>
      <div className="flex-1 flex items-center justify-center px-4 -mt-10">
        <div className="w-full max-w-sm">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-400 to-violet-600 mb-4 shadow-soft">
              <span className="text-white font-bold text-lg tracking-tight">B</span>
            </div>
            <h1 className="text-2xl font-semibold text-fg tracking-tight">BizIQ’ga xush kelibsiz</h1>
            <p className="text-muted text-sm mt-1">AI biznes tahlilchingizga kiring</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-3">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Elektron pochta"
              className="w-full bg-elev border border-line rounded-xl px-4 py-3 text-fg placeholder:text-subtle outline-none focus:border-accent transition"
            />
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Parol"
              className="w-full bg-elev border border-line rounded-xl px-4 py-3 text-fg placeholder:text-subtle outline-none focus:border-accent transition"
            />

            {error && (
              <div className="flex items-start gap-2 px-3 py-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-500 text-sm">
                <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-accent hover:opacity-90 disabled:opacity-60 disabled:cursor-not-allowed text-accent-fg font-medium py-3 rounded-xl transition flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-accent-fg border-t-transparent rounded-full animate-spin" />
                  Kirilmoqda…
                </>
              ) : (
                'Davom etish'
              )}
            </button>
          </form>

          <p className="text-center text-subtle text-xs mt-6">
            Demo maʻlumotlar oldindan toʻldirilgan · <span className="text-muted">admin@bank.uz / admin123</span>
          </p>
        </div>
      </div>
    </div>
  );
}
