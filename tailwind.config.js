/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        wsb: {
          green: '#00c853',
          red: '#ff1744',
          gold: '#ffd600',
          dark: '#0d1117',
          card: '#161b22',
          border: '#30363d',
        },
      },
    },
  },
  plugins: [],
}
