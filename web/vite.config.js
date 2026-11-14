import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'

// base './' so the built site works from any folder or GitHub Pages path.
export default defineConfig({ plugins: [vue(), tailwindcss()], base: './' })
