<script setup>
import { onMounted, ref } from "vue";
import { RouterLink } from "vue-router";
import ReportCanvas from "../components/ReportCanvas.vue";
import { demoApi } from "../api";

const report = ref(null);
const error = ref("");

onMounted(async () => {
  try {
    report.value = await demoApi();
  } catch (exception) {
    error.value = exception.message;
  }
});

function download() {
  const url = URL.createObjectURL(new Blob([report.value.report_markdown], { type: "text/markdown;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "courselab-demo-report.md";
  link.click();
  URL.revokeObjectURL(url);
}
</script>

<template>
  <header class="site-header">
    <RouterLink class="brand" to="/">
      <span class="brand-mark" aria-hidden="true"></span>
      <span>CourseLab</span>
    </RouterLink>
    <div class="header-actions">
      <RouterLink class="text-link" to="/">返回首页</RouterLink>
      <RouterLink class="button" to="/register">生成我的路线</RouterLink>
    </div>
  </header>

  <main class="app-main">
    <div class="demo-ribbon">
      <p><strong>演示报告</strong>　这是一份固定样例，不调用 Tavily 或大模型，也不消耗 API。</p>
      <button class="button ghost" type="button" @click="download">下载样例</button>
    </div>
    <div v-if="error" class="error-banner">{{ error }}</div>
    <div v-if="!report" class="loading-page"><div class="loading-mark">正在整理样例路线</div></div>
    <ReportCanvas v-else :report="report" actions @download="download" />
  </main>
</template>

