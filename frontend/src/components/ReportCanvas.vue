<script setup>
const props = defineProps({
  report: { type: Object, required: true },
  actions: { type: Boolean, default: false },
});

defineEmits(["download"]);

function resourceById(id) {
  return props.report.resources.find((resource) => resource.id === id);
}
</script>

<template>
  <article class="report">
    <header class="report-cover">
      <div class="hero-kicker">计划与资料审阅</div>
      <h1>{{ report.roadmap.title }}</h1>
      <p class="report-summary">{{ report.roadmap.overview }}</p>
      <div class="report-meta">
        <div>
          <span>学习目标</span>
          <strong>{{ report.profile.level }} · {{ report.profile.language }}</strong>
        </div>
        <div>
          <span>时间预算</span>
          <strong>{{ report.profile.duration_weeks }} 周 / 每周 {{ report.profile.weekly_hours }} 小时</strong>
        </div>
        <div>
          <span>资料数量</span>
          <strong>{{ report.resources.length }} 个可追溯来源</strong>
        </div>
        <div>
          <span>计划结论</span>
          <strong>{{ report.evaluation.verdict === "recommended" ? "建议执行" : "建议修订" }}</strong>
        </div>
      </div>
    </header>

    <div class="report-grid">
      <section class="route-section" aria-labelledby="route-heading">
        <div class="section-title">
          <h2 id="route-heading">学习轨迹</h2>
          <span>从先修到综合交付</span>
        </div>
        <div v-for="(stage, index) in report.roadmap.stages" :key="`${stage.name}-${index}`" class="stage">
          <div class="stage-number">{{ index + 1 }}</div>
          <div class="stage-body">
            <div class="stage-head">
              <h3>{{ stage.name }}</h3>
              <span>{{ stage.weeks }} 周 · {{ stage.weeks * report.profile.weekly_hours }} 小时</span>
            </div>
            <p class="stage-focus">{{ stage.focus }}</p>
            <div class="topic-list">
              <span v-for="topic in stage.topics" :key="topic">{{ topic }}</span>
            </div>
            <div class="stage-details">
              <span><strong>练习</strong>　{{ stage.practice }}</span>
              <span><strong>交付</strong>　{{ stage.deliverable }}</span>
              <span>
                <strong>资料</strong>　
                <a
                  v-for="resourceId in stage.resource_ids"
                  :key="resourceId"
                  class="resource-link"
                  :href="resourceById(resourceId)?.url"
                  target="_blank"
                  rel="noreferrer"
                >
                  {{ resourceId }}
                </a>
              </span>
            </div>
          </div>
        </div>
      </section>

      <aside class="sidebar-stack">
        <section class="score-card">
          <div class="score-number">{{ report.evaluation.total_score }}</div>
          <p>计划可用性 / 100</p>
          <p>{{ report.evaluation.summary }}</p>
        </section>

        <section class="side-panel">
          <h3>五项检查</h3>
          <div v-for="dimension in report.evaluation.dimensions" :key="dimension.name" class="dimension">
            <div class="dimension-label">
              <span>{{ dimension.name }}</span>
              <span>{{ dimension.score }}/20</span>
            </div>
            <div class="dimension-bar"><i :style="{ width: `${dimension.score * 5}%` }"></i></div>
          </div>
        </section>

        <section class="side-panel">
          <h3>先修与交付</h3>
          <ul>
            <li v-for="item in report.roadmap.prerequisites" :key="item">{{ item }}</li>
            <li>{{ report.roadmap.final_project }}</li>
          </ul>
        </section>

        <section class="side-panel">
          <h3>资料索引</h3>
          <div class="resource-list">
            <a
              v-for="resource in report.resources"
              :key="resource.id"
              class="resource-card"
              :href="resource.url"
              target="_blank"
              rel="noreferrer"
            >
              <strong>{{ resource.id }}　{{ resource.title }}</strong>
              <span>{{ resource.provider }} · {{ resource.resource_type }}</span>
              <p class="resource-reason">{{ resource.reason }}</p>
            </a>
          </div>
        </section>

        <section class="side-panel">
          <h3>审查意见</h3>
          <ul>
            <li v-for="item in [...report.evaluation.issues, ...report.evaluation.recommendations]" :key="item">
              {{ item }}
            </li>
          </ul>
        </section>

        <button v-if="actions" class="button signal" type="button" @click="$emit('download')">
          下载 Markdown 报告
        </button>
      </aside>
    </div>
  </article>
</template>

