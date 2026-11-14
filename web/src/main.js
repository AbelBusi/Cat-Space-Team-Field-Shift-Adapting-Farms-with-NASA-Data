import '@fontsource/atkinson-hyperlegible/400.css'
import '@fontsource/atkinson-hyperlegible/700.css'
import '@fontsource-variable/bricolage-grotesque/opsz.css'
import '@fontsource/pixelify-sans/500.css'
import '@fontsource/ibm-plex-mono/400.css'
import '@fontsource/ibm-plex-mono/500.css'
import './style.css'
import { createApp } from 'vue'
import App from './App.vue'

import { t } from './i18n.js'

const app = createApp(App)
app.config.globalProperties.t = t   // t('English text') in every template
app.mount('#app')
