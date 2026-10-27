<script setup>
import { RouterLink } from "vue-router";
</script>

<template>
  <header class="site-header">
    <RouterLink class="brand" to="/">
      <span class="brand-mark" aria-hidden="true"></span>
      <span>CourseLab</span>
    </RouterLink>
    <div class="header-actions">
      <RouterLink class="text-link" to="/demo">看一份演示报告</RouterLink>
      <RouterLink class="text-link" to="/login">登录</RouterLink>
      <RouterLink class="button" to="/register">创建账号</RouterLink>
    </div>
  </header>

  <main>
    <section class="hero">
      <div class="hero-copy">
        <div class="hero-kicker">多 Agent 学习路线规划</div>
        <h1>把想学的，铺成一条走得完的路。</h1>
        <p class="hero-lead">
          说出目标、基础和可投入的时间。CourseLab 会先搜索可信资料，再安排阶段、匹配资源，最后交由独立 Agent 检查这条计划是否真的能执行。
        </p>
        <div class="hero-actions">
          <RouterLink class="button signal" to="/register">开始规划</RouterLink>
          <RouterLink class="button secondary" to="/demo">查看完整报告</RouterLink>
        </div>
        <p class="hero-note">本地多账号 · Tavily 实时检索 · CrewAI 路线编排与审查</p>
      </div>

      <div class="route-board" aria-label="路线规划示意">
        <div class="board-head">
          <span>样例路线 / FastAPI 六周</span>
          <span class="board-badge">88 分</span>
        </div>
        <div class="route-diagram">
          <div class="route-node current">
            <div class="node-dot">1</div>
            <div class="node-copy">
              <strong>建立 API 心智模型</strong>
              <span>官方教程 · 请求参数 · Swagger</span>
            </div>
          </div>
          <div class="route-node">
            <div class="node-dot">2</div>
            <div class="node-copy">
              <strong>结构与持久化</strong>
              <span>SQLAlchemy · CRUD · 分层项目</span>
            </div>
          </div>
          <div class="route-node">
            <div class="node-dot">3</div>
            <div class="node-copy">
              <strong>安全与业务闭环</strong>
              <span>JWT · 用户隔离 · 接口测试</span>
            </div>
          </div>
          <div class="route-node">
            <div class="node-dot">4</div>
            <div class="node-copy">
              <strong>测试与交付</strong>
              <span>pytest · Docker · README</span>
            </div>
          </div>
        </div>
        <div class="board-stamp">可执行<br />88 / 100</div>
      </div>
    </section>

    <section class="feature-strip">
      <div class="feature-grid">
        <article class="feature-item">
          <b>先检索，再规划</b>
          <p>路线不会凭空编造资料。Tavily 先返回来源，资料策展 Agent 只从搜索结果中筛选。</p>
        </article>
        <article class="feature-item">
          <b>把时间算进去</b>
          <p>输入每周可投入小时数和学习周期，路线会把阶段、练习和交付物控制在预算内。</p>
        </article>
        <article class="feature-item">
          <b>独立审查可用性</b>
          <p>另一个 Agent 从目标匹配、顺序、工作量、资料质量和可执行性五项检查计划。</p>
        </article>
      </div>
    </section>
  </main>
</template>

