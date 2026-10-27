<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import AppShell from "../components/AppShell.vue";
import ReportCanvas from "../components/ReportCanvas.vue";
import { downloadReport, planApi } from "../api";

const route = useRoute();
const router = useRouter();
const plan = ref(null);
const error = ref("");
const deleting = ref(false);
let timer;

const reportData = computed(() => {
  if (!plan.value?.roadmap) return null;
  return {
    profile: plan.value,
    roadmap: plan.value.roadmap,
    resources: plan.value.resources,
    evaluation: plan.value.evaluation,
  };
});

async function load() {
  try {
    plan.value = await planApi.get(route.params.id);
    error.value = "";
    if (["queued", "running"].includes(plan.value.status)) {
      timer = window.setTimeout(load, 1800);
    }
  } catch (exception) {
    error.value = exception.message;
  }
}

async function retry() {
  try {
    plan.value = await planApi.retry(plan.value.id);
    error.value = "";
    timer = window.setTimeout(load, 800);
  } catch (exception) {
    error.value = exception.message;
  }
}

async function remove() {
  if (!window.confirm("删除后无法恢复，确认删除这份学习计划？")) return;
  deleting.value = true;
  try {
    await planApi.remove(plan.value.id);
    router.push("/app");
  } catch (exception) {
    error.value = exception.message;
    deleting.value = false;
  }
}

function download() {
  downloadReport(plan.value.id, `courselab-${plan.value.topic}.md`).catch((exception) => {
    error.value = exception.message;
  });
}

onMounted(load);
onBeforeUnmount(() => window.clearTimeout(timer));
</script>

<template>
  <AppShell>
    <div v-if="error" class="error-banner">{{ error }}</div>
    <div v-if="!plan" class="loading-page"><div class="loading-mark">正在打开计划</div></div>
    <template v-else>
      <div class="page-head">
        <div>
          <h1>{{ plan.topic }}</h1>
          <p>{{ plan.level }} · {{ plan.duration_weeks }} 周 · 每周 {{ plan.weekly_hours }} 小时</p>
        </div>
        <div class="inline-actions">
          <button
            v-if="reportData"
            class="button secondary"
            type="button"
            @click="download"
          >
            下载报告
          </button>
          <button class="button danger" type="button" :disabled="deleting" @click="remove">删除</button>
        </div>
      </div>

      <section v-if="['queued', 'running'].includes(plan.status)" class="panel">
        <div class="hero-kicker">Agent 正在工作</div>
        <h2>{{ plan.stage }}</h2>
        <div class="progress-shell">
          <div class="progress-track"><div class="progress-fill" :style="{ width: `${plan.progress}%` }"></div></div>
          <div class="progress-labels">
            <span>搜索资料 → 编排路线 → 独立审查</span>
            <span>{{ plan.progress }}%</span>
          </div>
        </div>
        <p style="color: var(--muted); margin: 0">页面会自动更新，可以暂时离开，生成结果会保存在当前电脑。</p>
      </section>

      <section v-else-if="plan.status === 'failed'" class="empty-state">
        <div class="hero-kicker">生成没有完成</div>
        <h2>先处理这个问题，再继续。</h2>
        <p>{{ plan.error }}</p>
        <div class="inline-actions">
          <button class="button signal" type="button" @click="retry">重新生成</button>
        </div>
      </section>

      <ReportCanvas v-else-if="reportData" :report="reportData" actions @download="download" />
    </template>
  </AppShell>
</template>

