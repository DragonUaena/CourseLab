<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  report: { type: Object, required: true },
  actions: { type: Boolean, default: false },
});

defineEmits(["download"]);

const activeTab = ref("resources");
const tabs = computed(() => [
  { id: "resources", label: "资料索引", count: props.report.resources.length },
  { id: "checks", label: "质量检查", count: props.report.evaluation.dimensions.length },
  { id: "review", label: "审查建议", count: props.report.evaluation.issues.length },
]);

const generationTime = computed(() => {
  const started = props.report.profile.started_at;
  const completed = props.report.profile.completed_at;
  if (!started || !completed) return "";
  const seconds = Math.max(0, Math.round((new Date(completed).getTime() - new Date(started).getTime()) / 1000));
  if (!Number.isFinite(seconds)) return "";
  const minutes = Math.floor(seconds / 60);
  return minutes ? `${minutes} 分 ${seconds % 60} 秒` : `${seconds} 秒`;
});

const tokenUsage = computed(() => {
  const total = props.report.profile.token_usage?.total_tokens;
  return total ? `${Number(total).toLocaleString("zh-CN")} tokens` : "";
});

function resourceById(id) {
  return props.report.resources.find((resource) => resource.id === id);
}

function freshness(resource) {
  if (resource.published_date) return `发布于 ${resource.published_date}`;
  if (resource.retrieved_at) return `检索于 ${resource.retrieved_at}`;
  return "日期未记录";
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
        <div v-if="generationTime">
          <span>生成耗时</span>
          <strong>{{ generationTime }}</strong>
        </div>
        <div v-if="tokenUsage">
          <span>模型用量</span>
          <strong>{{ tokenUsage }}</strong>
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
            <div v-if="stage.objectives?.length" class="stage-block">
              <strong>学习目标</strong>
              <ul>
                <li v-for="item in stage.objectives" :key="item">{{ item }}</li>
              </ul>
            </div>
            <div v-if="stage.schedule?.length" class="schedule-list">
              <div v-for="item in stage.schedule" :key="`${item.period}-${item.focus}`" class="schedule-item">
                <span>{{ item.period }}</span>
                <strong>{{ item.focus }}</strong>
                <p>{{ item.output }}</p>
              </div>
            </div>
            <div class="stage-details">
              <span><strong>练习</strong>　{{ stage.practice }}</span>
              <span><strong>交付</strong>　{{ stage.deliverable }}</span>
            </div>
            <div v-if="stage.acceptance_criteria?.length" class="stage-block">
              <strong>验收标准</strong>
              <ul>
                <li v-for="item in stage.acceptance_criteria" :key="item">{{ item }}</li>
              </ul>
            </div>
            <div class="evidence-list">
              <strong class="evidence-title">阶段依据</strong>
              <a
                v-for="resourceId in stage.resource_ids"
                :key="resourceId"
                class="evidence-item"
                :href="resourceById(resourceId)?.url"
                target="_blank"
                rel="noreferrer"
              >
                <span>{{ resourceId }} · {{ resourceById(resourceId)?.resource_type }}</span>
                <strong>{{ resourceById(resourceId)?.title }}</strong>
                <small>{{ resourceById(resourceId)?.reason }}</small>
              </a>
            </div>
          </div>
        </div>

        <div class="route-outcomes">
          <section>
            <h3>开始之前</h3>
            <ul>
              <li v-for="item in report.roadmap.prerequisites" :key="item">{{ item }}</li>
            </ul>
          </section>
          <section>
            <h3>最终交付</h3>
            <p>{{ report.roadmap.final_project }}</p>
            <ul v-if="report.roadmap.project_requirements?.length">
              <li v-for="item in report.roadmap.project_requirements" :key="item">{{ item }}</li>
            </ul>
          </section>
        </div>
        <div v-if="report.roadmap.study_strategy?.length" class="strategy-note">
          <h3>执行策略</h3>
          <ul>
            <li v-for="item in report.roadmap.study_strategy" :key="item">{{ item }}</li>
          </ul>
        </div>
      </section>

      <aside class="report-sidebar">
        <section class="score-card report-score">
          <div class="score-head">
            <div class="score-number">{{ report.evaluation.total_score }}</div>
            <span class="score-verdict">
              {{ report.evaluation.verdict === "recommended" ? "建议执行" : "建议修订" }}
            </span>
          </div>
          <strong>计划可用性 / 100</strong>
          <p>{{ report.evaluation.summary }}</p>
        </section>

        <div class="report-tabs" role="tablist" aria-label="报告详情">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            class="report-tab"
            :class="{ active: activeTab === tab.id }"
            type="button"
            role="tab"
            :aria-selected="activeTab === tab.id"
            @click="activeTab = tab.id"
          >
            <span>{{ tab.label }}</span>
            <small>{{ tab.count }}</small>
          </button>
        </div>

        <section v-if="activeTab === 'resources'" class="side-panel tab-panel" role="tabpanel">
          <div class="tab-panel-head">
            <h3>资料索引</h3>
            <span>按计划引用筛选</span>
          </div>
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
              <span>{{ resource.provider }} · {{ resource.resource_type }} · {{ freshness(resource) }}</span>
              <p class="resource-reason">{{ resource.reason }}</p>
            </a>
          </div>
        </section>

        <section v-else-if="activeTab === 'checks'" class="side-panel tab-panel" role="tabpanel">
          <div class="tab-panel-head">
            <h3>五项检查</h3>
            <span>Agent 评分</span>
          </div>
          <div v-for="dimension in report.evaluation.dimensions" :key="dimension.name" class="dimension">
            <div class="dimension-label">
              <span>{{ dimension.name }}</span>
              <span>{{ dimension.score }}/20</span>
            </div>
            <div class="dimension-bar"><i :style="{ width: `${dimension.score * 5}%` }"></i></div>
          </div>
          <div v-if="report.evaluation.program_checks?.checks?.length" class="audit-list">
            <div
              v-for="check in report.evaluation.program_checks.checks"
              :key="check.name"
              class="audit-row"
            >
              <span :class="{ passed: check.passed }">{{ check.passed ? "通过" : "注意" }}</span>
              <div>
                <strong>{{ check.name }}</strong>
                <small>{{ check.detail }}</small>
              </div>
            </div>
          </div>
        </section>

        <section v-else class="side-panel tab-panel" role="tabpanel">
          <div class="tab-panel-head">
            <h3>审查建议</h3>
            <span>风险与下一步</span>
          </div>
          <div class="review-group">
            <strong>优势</strong>
            <ul>
              <li v-for="item in report.evaluation.strengths" :key="item">{{ item }}</li>
            </ul>
          </div>
          <div class="review-group review-risk">
            <strong>需要留意</strong>
            <ul>
              <li v-for="item in report.evaluation.issues" :key="item">{{ item }}</li>
            </ul>
          </div>
          <div class="review-group">
            <strong>建议调整</strong>
            <ul>
              <li v-for="item in report.evaluation.recommendations" :key="item">{{ item }}</li>
            </ul>
          </div>
        </section>

        <button v-if="actions" class="button signal report-download" type="button" @click="$emit('download')">
          下载 Markdown 报告
        </button>
      </aside>
    </div>
  </article>
</template>

