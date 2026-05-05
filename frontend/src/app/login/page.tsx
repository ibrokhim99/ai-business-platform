'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace('/');
  }, [router]);

  return (
    <div className="min-h-screen grid place-items-center bg-canvas">
      <div className="w-6 h-6 border-2 border-line border-t-accent rounded-full animate-spin" />
    </div>
  );
}
