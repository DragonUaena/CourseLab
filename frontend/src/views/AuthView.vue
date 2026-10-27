<script setup>
import { computed, reactive, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";
import { authApi, setToken } from "../api";

const props = defineProps({ mode: { type: String, default: "login" } });
const router = useRouter();
const route = useRoute();
const loading = ref(false);
const error = ref("");
const form = reactive({ display_name: "", email: "", password: "" });
const isRegister = computed(() => props.mode === "register");

async function submit() {
  loading.value = true;
  error.value = "";
  try {
    const payload = isRegister.value
      ? { display_name: form.display_name, email: form.email, password: form.password }
      : { email: form.email, password: form.password };
    const result = isRegister.value ? await authApi.register(payload) : await authApi.login(payload);
    setToken(result.access_token);
    router.push(route.query.redirect || "/app");
  } catch (exception) {
    error.value = exception.message;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="auth-page">
    <aside class="auth-aside">
      <RouterLink class="brand" to="/">
        <span class="brand-mark" aria-hidden="true"></span>
        <span>CourseLab</span>
      </RouterLink>
      <p class="auth-quote">好路线不是资料堆在一起，而是每一步都知道为什么出发。</p>
      <small>本地部署 · 每个账号独立保存计划</small>
    </aside>
    <main class="auth-main">
      <div class="auth-card">
        <div class="hero-kicker">{{ isRegister ? "建立学习档案" : "继续你的路线" }}</div>
        <h1>{{ isRegister ? "从目标开始。" : "欢迎回来。" }}</h1>
        <p class="auth-subtitle">
          {{ isRegister ? "账号只保存在当前电脑的数据库中。" : "登录后查看或继续生成自己的学习计划。" }}
        </p>
        <div v-if="error" class="error-banner">{{ error }}</div>
        <form class="form-stack" @submit.prevent="submit">
          <label v-if="isRegister" class="field">
            <span>怎么称呼你</span>
            <input v-model.trim="form.display_name" required minlength="2" maxlength="40" autocomplete="name" />
          </label>
          <label class="field">
            <span>邮箱</span>
            <input v-model.trim="form.email" type="email" required autocomplete="email" />
          </label>
          <label class="field">
            <span>密码</span>
            <input
              v-model="form.password"
              type="password"
              required
              :minlength="isRegister ? 8 : undefined"
              :autocomplete="isRegister ? 'new-password' : 'current-password'"
            />
          </label>
          <button class="button signal" type="submit" :disabled="loading">
            {{ loading ? "请稍候…" : isRegister ? "创建账号" : "登录" }}
          </button>
        </form>
        <div class="form-meta" style="margin-top: 24px">
          <span>{{ isRegister ? "已经有账号？" : "第一次使用？" }}</span>
          <RouterLink :to="isRegister ? '/login' : '/register'">
            {{ isRegister ? "直接登录" : "创建账号" }}
          </RouterLink>
        </div>
      </div>
    </main>
  </div>
</template>

