/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: '#246B45', soft: '#4F8A5B', bg: '#F7F9F6', text: '#1F2933', amber: '#E9A23B', red: '#C84630', blue: '#3478A5' },
      },
      fontFamily: { sans: ['Inter', '"Noto Sans Telugu"', '"Noto Sans"', 'system-ui', 'sans-serif'] },
    },
  },
  plugins: [],
}
