/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        dm: {
          bg: '#0e1120',
          surface: '#15192d',
          card: '#1a2038',
          muted: '#222844',
          border: '#2a3050',
          primary: '#8b5cf6',   /* violet-500 */
          primary2: '#f59e0b',  /* amber-500 */
          text: '#e5e7eb',      /* gray-200 */
          subt: '#9ca3af'       /* gray-400 */
        }
      },
      boxShadow: {
        'dm-soft': '0 10px 25px rgba(0,0,0,0.35)',
        'dm-inner': 'inset 0 1px 0 rgba(255,255,255,0.04)',
      },
      borderRadius: {
        '2xl': '1rem',
      },
      fontFamily: {
        sans: ['InterVariable', 'Inter', 'system-ui', 'ui-sans-serif', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'Noto Sans', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
