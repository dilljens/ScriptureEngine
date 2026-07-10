/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Parallelism type colors — used for highlights and badges
        'parallel-synonymous': {
          bg: '#FEF3C7',
          text: '#92400E',
          border: '#F59E0B',
        },
        'parallel-antithetic-a': {
          bg: '#FFE4E6',
          text: '#9F1239',
          border: '#E11D48',
        },
        'parallel-antithetic-b': {
          bg: '#DBEAFE',
          text: '#1E40AF',
          border: '#2563EB',
        },
        'parallel-synthetic': {
          bg: '#CCFBF1',
          text: '#0F766E',
          border: '#14B8A6',
        },
        'parallel-staircase': {
          1: '#DCFCE7',
          2: '#BBF7D0',
          3: '#86EFAC',
          4: '#4ADE80',
          5: '#22C55E',
        },
        'chiasm-a': {
          bg: '#FEE2E2',
          border: '#EF4444',
        },
        'chiasm-b': {
          bg: '#DBEAFE',
          border: '#3B82F6',
        },
        'chiasm-c': {
          bg: '#DCFCE7',
          border: '#22C55E',
        },
        'chiasm-pivot': {
          bg: '#FEF9C3',
          border: '#EAB308',
        },
      },
    },
  },
  plugins: [],
}
