<script setup>
import { onMounted, reactive, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";
import AppShell from "../components/AppShell.vue";
import { credentialApi, planApi } from "../api";

const router = useRouter();
const loading = ref(false);
const error = ref("");
const configured = ref(true);
const form = reactive({
  topic: "FastAPI 从入门到项目部署",
  goal: "能够独立开发带数据库、鉴权和测试的 REST API，并完成一次本地部署",
  level: "入门",
  weekly_hours: 6,
  duration_weeks: 6,
  language: "中文",
  constraints: "有 Python 基础，希望每周都有可以验证的产出",
});

onMounted(async () => {
  try {
    configured.value = (await credentialApi.get()).configured;
  } catch {
    configured.value = false;
  }
});

async function submit() {
  loading.value = true;
  error.value = "";
  try {
    const plan = await planApi.create(form);
    router.push(`/app/plans/${plan.id}`);
  } catch (exception) {
    error.value = exception.message;
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <AppShell>
    <div class="page-head">
      <div>
        <h1>描述你想学的事</h1>
        <p>目标越具体，路线越容易变成可执行的交付物。</p>
      </div>
    </div>

    <div v-if="!configured" class="notice-banner">
      还没有配置 Tavily 与大模型 Key。
      <RouterLink to="/app/settings">现在去设置</RouterLink>
    </div>
    <div v-if="error" class="error-banner">{{ error }}</div>

    <div class="planner-grid">
      <form class="panel form-stack" @submit.prevent="submit">
        <label class="field">
          <span>想学什么</span>
          <input v-model.trim="form.topic" required minlength="2" maxlength="120" />
        </label>
        <label class="field">
          <span>学完以后要能做到什么</span>
          <textarea
            v-model.trim="form.goal"
            required
            minlength="10"
            maxlength="1500"
            placeholder="例如：能独立开发一个带用户登录、数据库和测试的 API 项目"
          ></textarea>
        </label>
        <div class="two-fields">
          <label class="field">
            <span>当前基础</span>
            <select v-model="form.level">
              <option>零基础</option>
              <option>入门</option>
              <option>进阶</option>
              <option>项目实战</option>
            </select>
          </label>
          <label class="field">
            <span>资料语言</span>
            <select v-model="form.language">
              <option>中文</option>
              <option>英文</option>
              <option>中英混合</option>
            </select>
          </label>
        </div>
        <div class="two-fields">
          <label class="field">
            <span>每周可投入小时</span>
            <input v-model.number="form.weekly_hours" type="number" min="1" max="40" required />
          </label>
          <label class="field">
            <span>计划周期（周）</span>
            <input v-model.number="form.duration_weeks" type="number" min="1" max="52" required />
          </label>
        </div>
        <label class="field">
          <span>额外限制</span>
          <textarea
            v-model.trim="form.constraints"
            maxlength="1000"
            placeholder="例如：只看官方文档，希望有视频，最终需要项目演示"
          ></textarea>
        </label>
        <button class="button signal" type="submit" :disabled="loading || !configured">
          {{ loading ? "正在提交…" : "搜索资料并生成路线" }}
        </button>
      </form>

      <aside class="panel panel-aside">
        <div class="hero-kicker" style="color: #f3c64f">生成闭环</div>
        <h2>三个 Agent 接力</h2>
        <ol>
          <li>Tavily 按主题、目标和实战需求检索资料。</li>
          <li>资料策展 Agent 排除重复与低相关页面。</li>
          <li>路线 Agent 按时间预算安排阶段和交付物。</li>
          <li>审查 Agent 独立打分，指出不适合执行的部分。</li>
        </ol>
        <p>通常需要几十秒。页面会持续显示当前阶段，不需要手动刷新。</p>
      </aside>
    </div>
  </AppShell>
</template>

