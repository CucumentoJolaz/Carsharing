import { createRouter, createWebHistory } from 'vue-router'
import MainPage from "@/pages/MainPage.vue";
import AnalyticsPage from "@/pages/AnalyticsPage.vue";
import RentPage from "@/pages/RentPage.vue";

const routes = [
  {
    path: '/',
    name: 'Main',
    component: MainPage
  },
  {
    path: '/analytics',
    name: 'Analytics',
    component: AnalyticsPage
  },
  {
    path: '/rent',
    name: 'Rent',
    component: RentPage
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router;