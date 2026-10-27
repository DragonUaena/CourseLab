<script setup>
import { onMounted, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { authApi, setToken } from "../api";

const router = useRouter();
const user = ref(null);

onMounted(async () => {
  try {
    user.value = await authApi.me();
  } catch {
    setToken("");
    router.push({ name: "login" });
  }
});

function logout() {
  setToken("");
  router.push({ name: "home" });
}
</script>

<template>
  <div class="app-layout">
    <aside class="app-sidebar">
      <RouterLink class="brand" to="/app">
        <span class="brand-mark" aria-hidden="true"></span>
        <span>CourseLab</span>
      </RouterLink>
      <nav class="app-nav" aria-label="主要导航">
        <RouterLink to="/app">我的路线</RouterLink>
        <RouterLink to="/app/new">生成计划</RouterLink>
        <RouterLink to="/app/settings">模型设置</RouterLink>
        <RouterLink to="/demo">演示报告</RouterLink>
      </nav>
      <div class="sidebar-foot">
        <div v-if="user" class="user-chip">
          <strong>{{ user.display_name }}</strong>
          <span>{{ user.email }}</span>
        </div>
        <button class="button ghost" type="button" @click="logout">退出</button>
      </div>
    </aside>
    <main class="app-main">
      <slot />
    </main>
  </div>
</template>

