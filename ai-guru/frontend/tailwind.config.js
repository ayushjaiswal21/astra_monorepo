/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        gray: {
          900: '#111827',
          800: '#1F2937', // Main background
          700: '#374151', // Component background
          600: '#4B5563',
          500: '#6B7280',
          400: '#9CA3AF',
          300: '#D1D5DB',
          200: '#E5E7EB',
          100: '#F3F4F6',
        },
        blue: {
          600: '#2563EB',
          700: '#1D4ED8',
        }
      }
    },
  },
  plugins: [],
}
