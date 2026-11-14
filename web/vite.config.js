import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// base './' so the built site works from any folder or GitHub Pages path.
export default defineConfig({ plugins: [vue()], base: './' })
