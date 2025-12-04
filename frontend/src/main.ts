import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import './styles/main.css'
import { usePreferencesStore } from './stores/preferences'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)

const preferences = usePreferencesStore()
preferences.initialize()

app.mount('#app')
