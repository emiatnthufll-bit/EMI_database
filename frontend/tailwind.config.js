export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      container: { center: true, padding: '1rem' },
      boxShadow: { soft: '0 1px 3px rgba(0,0,0,0.08)' }
    },
  },
  plugins: [],
}
