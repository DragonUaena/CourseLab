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
const refreshing = ref(false);
const stopping = ref(false);
const now = ref(Date.now());
let timer;
let clockTimer;
let requestInFlight = false;
let pollFailures = 0;
let disposed = false;

const reportData = computed(() => {
  if (!plan.value?.roadmap) return null;
  return {
    profile: plan.value,
    roadmap: plan.value.roadmap,
    resources: plan.value.resources,
    evaluation: plan.value.evaluation,
  };
});

const elapsedLabel = computed(() => {
  if (!plan.value?.started_at) return "";
  const started = new Date(plan.value.started_at).getTime();
  const ended = plan.value.completed_at ? new Date(plan.value.completed_at).getTime() : now.value;
  if (!Number.isFinite(started) || !Number.isFinite(ended)) return "";
  return formatDuration(Math.max(0, Math.round((ended - started) / 1000)));
});

function formatDuration(totalSeconds) {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  if (hours) return `${hours} 小时 ${minutes} 分`;
  if (minutes) return `${minutes} 分 ${seconds} 秒`;
  return `${seconds} 秒`;
}

function clearTimer() {
  if (timer) window.clearTimeout(timer);
  timer = undefined;
}

function scheduleRefresh(delay) {
  clearTimer();
  if (!disposed) timer = window.setTimeout(() => load(), delay);
}

function isActive(value) {
  return ["queued", "running"].includes(value?.status);
}

async function load({ manual = false } = {}) {
  if (requestInFlight) return;
  requestInFlight = true;
  if (manual) refreshing.value = true;
  try {
    plan.value = await planApi.get(route.params.id);
    error.value = "";
    pollFailures = 0;
    if (!disposed && isActive(plan.value)) scheduleRefresh(1800);
  } catch (exception) {
    error.value = exception.message;
    if (plan.value && isActive(plan.value) && pollFailures < 4) {
      const delay = Math.min(1500 * 2 ** pollFailures, 12000);
      pollFailures += 1;
      scheduleRefresh(delay);
    }
  } finally {
    requestInFlight = false;
    refreshing.value = false;
  }
}

async function retry() {
  try {
    plan.value = await planApi.retry(plan.value.id);
    error.value = "";
    pollFailures = 0;
    scheduleRefresh(800);
  } catch (exception) {
    error.value = exception.message;
  }
}

async function stopGeneration() {
  if (!window.confirm("停止后本次生成结果不会保留，确认停止？")) return;
  stopping.value = true;
  clearTimer();
  try {
    plan.value = await planApi.stop(plan.value.id);
    error.value = "";
  } catch (exception) {
    error.value = exception.message;
    if (isActive(plan.value)) scheduleRefresh(1800);
  } finally {
    stopping.value = false;
  }
}

function refresh() {
  clearTimer();
  pollFailures = 0;
  load({ manual: true });
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

onMounted(() => {
  load();
  clockTimer = window.setInterval(() => {
    now.value = Date.now();
  }, 1000);
});
onBeforeUnmount(() => {
  disposed = true;
  clearTimer();
  window.clearInterval(clockTimer);
});
</script>

<template>
  <AppShell>
    <div v-if="error" class="error-banner">{{ error }}</div>
    <div v-if="!plan && !error" class="loading-page"><div class="loading-mark">正在打开计划</div></div>
    <section v-else-if="!plan" class="empty-state">
      <div class="hero-kicker">暂时无法打开</div>
      <h2>检查网络后再试一次。</h2>
      <p>这份计划没有丢失，可以重新读取生成状态。</p>
      <button class="button signal" type="button" :disabled="refreshing" @click="refresh">
        {{ refreshing ? "正在刷新…" : "刷新状态" }}
      </button>
    </section>
    <template v-else>
      <div class="page-head">
        <div>
          <h1>{{ plan.topic }}</h1>
          <p>
            {{ plan.level }} · {{ plan.duration_weeks }} 周 · 每周 {{ plan.weekly_hours }} 小时
            <template v-if="elapsedLabel"> · 生成耗时 {{ elapsedLabel }}</template>
          </p>
        </div>
        <div class="inline-actions">
          <button class="button ghost" type="button" :disabled="refreshing" @click="refresh">
            {{ refreshing ? "刷新中…" : "刷新状态" }}
          </button>
          <button
            v-if="reportData"
            class="button secondary"
            type="button"
            @click="download"
          >
            下载报告
          </button>
          <button
            v-if="isActive(plan)"
            class="button danger"
            type="button"
            :disabled="stopping"
            @click="stopGeneration"
          >
            {{ stopping ? "正在停止…" : "停止生成" }}
          </button>
          <button v-if="!isActive(plan)" class="button danger" type="button" :disabled="deleting" @click="remove">
            删除
          </button>
        </div>
      </div>

      <section v-if="isActive(plan)" class="panel" aria-live="polite" aria-atomic="true">
        <div class="hero-kicker">Agent 正在工作</div>
        <h2>{{ plan.stage }}</h2>
        <div class="progress-shell">
          <div
            class="progress-track"
            role="progressbar"
            aria-label="计划生成进度"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-valuenow="plan.progress"
          >
            <div class="progress-fill" :style="{ width: `${plan.progress}%` }"></div>
          </div>
          <div class="progress-labels">
            <span>搜索资料 → 编排路线 → 独立审查</span>
            <span>{{ plan.progress }}% · 已用时 {{ elapsedLabel }}</span>
          </div>
        </div>
        <p style="color: var(--muted); margin: 0">页面会自动更新，可以暂时离开，生成结果会保存在当前电脑。</p>
        <div class="inline-actions" style="margin-top: 24px">
          <button class="button danger" type="button" :disabled="stopping" @click="stopGeneration">
            {{ stopping ? "正在停止…" : "停止本次生成" }}
          </button>
        </div>
      </section>

      <section v-else-if="plan.status === 'failed'" class="empty-state">
        <div class="hero-kicker">生成没有完成</div>
        <h2>先处理这个问题，再继续。</h2>
        <p>{{ plan.error }}</p>
        <div class="inline-actions">
          <button class="button signal" type="button" :disabled="refreshing" @click="retry">重新生成</button>
        </div>
      </section>

      <section v-else-if="plan.status === 'cancelled'" class="empty-state">
        <div class="hero-kicker">已停止生成</div>
        <h2>本次任务已经结束。</h2>
        <p>{{ plan.error }}。未完成的中间结果不会被当作正式报告。</p>
        <button class="button signal" type="button" @click="retry">重新生成</button>
      </section>
      <ReportCanvas v-else-if="reportData" :report="reportData" actions @download="download" />
      <section v-else class="empty-state">
        <div class="hero-kicker">结果不完整</div>
        <h2>生成状态与报告内容不一致。</h2>
        <p>可以重新生成这份计划，之前的旧报告不会被当作本次结果。</p>
        <button class="button signal" type="button" @click="retry">重新生成</button>
      </section>
    </template>
  </AppShell>
</template>

