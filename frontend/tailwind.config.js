/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // *arr-style dark theme
        'arr-bg': '#1a1d23',
        'arr-bg-alt': '#23262e',
        'arr-sidebar': '#13151a',
        'arr-accent': '#f5871f',  // Orange accent
        'arr-accent-hover': '#e67e00',
        'arr-success': '#27c24c',
        'arr-danger': '#f05050',
        'arr-warning': '#fad733',
        'arr-text': '#cccccc',
        'arr-text-muted': '#888888',
        'arr-border': '#2d3139',
      }
    }
  },
  plugins: []
}
