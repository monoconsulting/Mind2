/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        dm: {
          bg: '#0b1020',
          surface: '#121830',
          border: '#1e2748',
          text: '#e6e8ef',
          subt: '#9aa3c7',
        },
      },
      fontFamily: {
        sans: ['InterVariable', 'Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

