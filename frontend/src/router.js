import { createRouter, createWebHistory } from "vue-router";
import { getToken } from "./api";
import LandingView from "./views/LandingView.vue";
import AuthView from "./views/AuthView.vue";
import DashboardView from "./views/DashboardView.vue";
import CreatePlanView from "./views/CreatePlanView.vue";
import PlanDetailView from "./views/PlanDetailView.vue";
import DemoView from "./views/DemoView.vue";
import SettingsView from "./views/SettingsView.vue";

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    { path: "/", name: "home", component: LandingView },
    { path: "/demo", name: "demo", component: DemoView },
    { path: "/login", name: "login", component: AuthView, props: { mode: "login" } },
    { path: "/register", name: "register", component: AuthView, props: { mode: "register" } },
    { path: "/app", name: "dashboard", component: DashboardView, meta: { auth: true } },
    { path: "/app/new", name: "new-plan", component: CreatePlanView, meta: { auth: true } },
    { path: "/app/plans/:id", name: "plan-detail", component: PlanDetailView, meta: { auth: true } },
    { path: "/app/settings", name: "settings", component: SettingsView, meta: { auth: true } },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

router.beforeEach((to) => {
  if (to.meta.auth && !getToken()) return { name: "login", query: { redirect: to.fullPath } };
  if ((to.name === "login" || to.name === "register") && getToken()) return { name: "dashboard" };
});

export default router;

