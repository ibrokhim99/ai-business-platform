import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        canvas:    'rgb(var(--canvas) / <alpha-value>)',
        panel:     'rgb(var(--panel) / <alpha-value>)',
        elev:      'rgb(var(--elev) / <alpha-value>)',
        elev2:     'rgb(var(--elev-2) / <alpha-value>)',
        line:      'rgb(var(--line) / <alpha-value>)',
        'line-strong': 'rgb(var(--line-strong) / <alpha-value>)',
        fg:        'rgb(var(--fg) / <alpha-value>)',
        muted:     'rgb(var(--muted) / <alpha-value>)',
        subtle:    'rgb(var(--subtle) / <alpha-value>)',
        accent:    'rgb(var(--accent) / <alpha-value>)',
        'accent-fg': 'rgb(var(--accent-fg) / <alpha-value>)',
        'accent-soft': 'rgb(var(--accent-soft) / <alpha-value>)',
      },
      boxShadow: {
        soft: '0 1px 3px rgb(0 0 0 / 0.04), 0 1px 2px rgb(0 0 0 / 0.06)',
        card: '0 4px 14px rgb(0 0 0 / 0.06)',
        pop: '0 12px 32px rgb(0 0 0 / 0.12)',
      },
      borderRadius: {
        '4xl': '2rem',
      },
    },
  },
  plugins: [],
};
export default config;
