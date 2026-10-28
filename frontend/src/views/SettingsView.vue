<script setup>
import { onMounted, reactive, ref } from "vue";
import AppShell from "../components/AppShell.vue";
import { credentialApi } from "../api";

const loading = ref(true);
const saving = ref(false);
const status = ref(null);
const error = ref("");
const saved = ref(false);
const form = reactive({
  tavily_api_key: "",
  llm_api_key: "",
  llm_model: "openai/gpt-4o-mini",
  llm_base_url: "",
  clear_tavily_api_key: false,
  clear_llm_api_key: false,
});

onMounted(async () => {
  try {
    status.value = await credentialApi.get();
    form.llm_model = status.value.llm_model;
    form.llm_base_url = status.value.llm_base_url;
  } catch (exception) {
    error.value = exception.message;
  } finally {
    loading.value = false;
  }
});

async function save() {
  saving.value = true;
  error.value = "";
  saved.value = false;
  try {
    status.value = await credentialApi.save(form);
    form.tavily_api_key = "";
    form.llm_api_key = "";
    form.clear_tavily_api_key = false;
    form.clear_llm_api_key = false;
    saved.value = true;
  } catch (exception) {
    error.value = exception.message;
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <AppShell>
    <div class="page-head">
      <div>
        <h1>模型与搜索</h1>
        <p>Key 只会发送给本地 FastAPI，并加密保存在这台电脑的数据目录中。</p>
      </div>
    </div>
    <div v-if="error" class="error-banner">{{ error }}</div>
    <div v-if="saved" class="notice-banner">设置已保存，可以开始生成学习计划。</div>
    <div v-if="loading" class="loading-page"><div class="loading-mark">正在读取设置</div></div>
    <div v-else class="planner-grid">
      <form class="panel form-stack" @submit.prevent="save">
        <label class="field">
          <span>Tavily API Key {{ status?.tavily_configured ? "（已配置，留空则不修改）" : "" }}</span>
          <input
            v-model.trim="form.tavily_api_key"
            type="password"
            autocomplete="off"
            placeholder="tvly-..."
            :disabled="form.clear_tavily_api_key"
          />
        </label>
        <label v-if="status?.tavily_configured" class="check-field">
          <input v-model="form.clear_tavily_api_key" type="checkbox" />
          <span>清除当前账号保存的 Tavily Key</span>
        </label>
        <label class="field">
          <span>大模型 API Key {{ status?.llm_configured ? "（已配置，留空则不修改）" : "" }}</span>
          <input
            v-model.trim="form.llm_api_key"
            type="password"
            autocomplete="off"
            placeholder="sk-..."
            :disabled="form.clear_llm_api_key"
          />
        </label>
        <label v-if="status?.llm_configured" class="check-field">
          <input v-model="form.clear_llm_api_key" type="checkbox" />
          <span>清除当前账号保存的大模型 Key</span>
        </label>
        <label class="field">
          <span>模型名（LiteLLM 格式）</span>
          <input v-model.trim="form.llm_model" required placeholder="openai/gpt-4o-mini" />
        </label>
        <label class="field">
          <span>OpenAI 兼容接口地址（可选）</span>
          <input v-model.trim="form.llm_base_url" type="url" placeholder="https://your-provider.example.com/v1" />
        </label>
        <button class="button signal" type="submit" :disabled="saving">
          {{ saving ? "正在保存…" : "保存设置" }}
        </button>
      </form>
      <aside class="panel panel-aside">
        <h2>怎么填写</h2>
        <p>Tavily Key 用于实时搜索课程、官方文档和项目资料，可在 Tavily 控制台创建。</p>
        <p>模型名遵循 LiteLLM 命名。OpenAI 可用 <code>openai/gpt-4o-mini</code>，DeepSeek 可用 <code>deepseek/deepseek-chat</code>。</p>
        <p>如果使用第三方 OpenAI 兼容网关，填写其 <code>/v1</code> 接口地址和对应 Key。</p>
      </aside>
    </div>
  </AppShell>
</template>

