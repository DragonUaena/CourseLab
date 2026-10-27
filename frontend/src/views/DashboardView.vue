<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import AppShell from "../components/AppShell.vue";
import { planApi } from "../api";

const plans = ref([]);
const loading = ref(true);
const error = ref("");
const completed = computed(() => plans.value.filter((plan) => plan.status === "completed").length);
const generating = computed(() => plans.value.filter((plan) => ["queued", "running"].includes(plan.status)).length);
const statusText = { queued: "排队中", running: "生成中", completed: "已完成", failed: "需重试" };

onMounted(async () => {
  try {
    plans.value = await planApi.list();
  } catch (exception) {
    error.value = exception.message;
  } finally {
    loading.value = false;
  }
});

function formatDate(value) {
  return new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(
    new Date(value),
  );
}
</script>

<template>
  <AppShell>
    <div class="page-head">
      <div>
        <h1>我的学习地图</h1>
        <p>每个计划都保存了路线、资料索引和独立审查结果。</p>
      </div>
      <RouterLink class="button signal" to="/app/new">生成新计划</RouterLink>
    </div>

    <div v-if="error" class="error-banner">{{ error }}</div>
    <div v-if="loading" class="loading-page"><div class="loading-mark">正在打开学习档案</div></div>
    <template v-else>
      <section class="stats-row" aria-label="计划统计">
        <div class="stat"><span>全部计划</span><strong>{{ plans.length }}</strong></div>
        <div class="stat"><span>已经完成</span><strong>{{ completed }}</strong></div>
        <div class="stat"><span>正在生成</span><strong>{{ generating }}</strong></div>
      </section>

      <section v-if="plans.length" class="plan-list">
        <RouterLink v-for="plan in plans" :key="plan.id" class="plan-row" :to="`/app/plans/${plan.id}`">
          <div>
            <h3>{{ plan.topic }}</h3>
            <p>{{ plan.duration_weeks }} 周 · 每周 {{ plan.weekly_hours }} 小时 · {{ formatDate(plan.created_at) }}</p>
          </div>
          <span class="status" :class="plan.status">{{ statusText[plan.status] }}</span>
        </RouterLink>
      </section>

      <section v-else class="empty-state">
        <div class="hero-kicker">还没有路线</div>
        <h2>不用先知道该学什么，只要先说想成为什么。</h2>
        <p>第一次生成会调用 Tavily 和大模型。你可以在“模型设置”中填写自己的 Key，演示报告则不需要 Key。</p>
        <div class="inline-actions">
          <RouterLink class="button signal" to="/app/new">规划第一门课</RouterLink>
          <RouterLink class="button secondary" to="/demo">先看演示</RouterLink>
        </div>
      </section>
    </template>
  </AppShell>
</template>

