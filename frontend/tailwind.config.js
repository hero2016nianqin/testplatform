/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // 主色：工业蓝
        primary: {
          DEFAULT: '#165DFF',
          light: '#5C8EFF',
          lighter: '#ECF5FF',
          dark: '#124ACC',
        },
        // 次要色
        secondary: {
          DEFAULT: '#409EFF',
          light: '#79bbff',
          lighter: '#ECF5FF',
          dark: '#337ECC',
        },
        success: '#67C23A',
        warning: '#E6A23C',
        danger: '#F56C6C',
        info: '#909399',
      },
      fontFamily: {
        sans: [
          'Inter', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"',
          'Roboto', '"Helvetica Neue"', 'Arial', '"PingFang SC"',
          '"Noto Sans SC"', 'Microsoft YaHei', 'sans-serif',
        ],
      },
      borderRadius: {
        none: '0',
        sm: '4px',
        DEFAULT: '8px',
        md: '6px',
        lg: '8px',
        xl: '12px',
        '2xl': '16px',
        full: '9999px',
      },
      boxShadow: {
        card: '0 2px 12px rgba(22, 93, 255, 0.08)',
        'card-hover': '0 6px 20px rgba(22, 93, 255, 0.14)',
        'card-sm': '0 1px 6px rgba(22, 93, 255, 0.06)',
      },
      spacing: {
        card: '96px',
        'card-lg': '128px',
        'card-sm': '72px',
      },
    },
  },
  plugins: [],
}
