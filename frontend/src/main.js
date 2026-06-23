import { createApp } from 'vue'
import App from '@/App.vue'
import components from "@/components/UI";
import router from "@/router/router.js";
import { initMockAuth } from "@/api/mockAuth.js"
const app = createApp(App)

// initialise components
components.forEach(component => {
    app.component(component.name, component)
})

app.use(router)

// Mocking authentication. 
// TO-DO replace with normal one
await initMockAuth()

app.mount('#app')
