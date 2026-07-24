import { createApp } from 'vue'
import { createPinia } from 'pinia'
import naive from 'naive-ui'
import router from './router'
import App from './App.vue'
import './styles/main.css'

// Older releases persisted research reports in localStorage. Remove those
// snapshots once at startup so an upgrade cannot resurrect a previous user's
// report after the new memory-only behavior is deployed.
try {
  const legacyResearchPrefix = 'deep-research:research-state:'
  Object.keys(window.localStorage)
    .filter((key) => key.startsWith(legacyResearchPrefix))
    .forEach((key) => window.localStorage.removeItem(key))
} catch {
  // Some privacy modes can deny storage access; in that case the in-memory
  // store still starts empty and the application remains usable.
}

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(naive)
app.mount('#app')
