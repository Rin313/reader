<template>
  <n-config-provider :theme-overrides="themeOverrides">
    <div class="min-h-screen bg-[#f8fafc] text-slate-800 flex flex-col font-sans selection:bg-indigo-100 selection:text-indigo-700 transition-colors duration-300">
      
      <!-- 顶部导航栏 -->
      <header class="sticky top-0 z-50 bg-white/80 backdrop-blur-lg border-b border-slate-200/60 transition-all duration-300">
        <div class="max-w-5xl mx-auto px-4 h-16 flex items-center justify-between">
          <!-- Logo区域 -->
          <div class="flex items-center gap-3 cursor-pointer select-none group" @click="resetApp">
            <div class="w-9 h-9 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform duration-300">
              <n-icon size="20" color="#fff"><BookOutline /></n-icon>
            </div>
            <div class="flex flex-col justify-center">
              <span class="text-base font-bold tracking-tight text-slate-900 leading-none">DeepReader</span>
              <span class="text-[10px] text-slate-400 font-medium tracking-wider uppercase mt-0.5">Intelligent Learning</span>
            </div>
          </div>

          <!-- 右侧控制区 -->
          <div class="flex items-center gap-3">
            
            <!-- 视图切换 (响应式：桌面端显示文字按钮，移动端显示图标下拉) -->
            <div class="hidden sm:block bg-slate-100/80 p-1 rounded-lg border border-slate-200/50">
              <n-radio-group v-model:value="viewMode" size="small">
                <n-radio-button value="en" class="!px-3">英文</n-radio-button>
                <n-radio-button value="dual" class="!px-3">对照</n-radio-button>
                <n-radio-button value="cn" class="!px-3">译文</n-radio-button>
              </n-radio-group>
            </div>
            <n-popselect v-model:value="viewMode" :options="viewModeOptions" trigger="click" class="sm:hidden">
              <n-button circle secondary size="small" class="sm:hidden">
                <template #icon><n-icon><EyeOutline /></n-icon></template>
              </n-button>
            </n-popselect>

            <div class="w-px h-4 bg-slate-300 mx-1"></div>

            <!-- 功能开关组 -->
            <div class="flex items-center gap-2">
              <n-tooltip trigger="hover" :show-arrow="false">
                <template #trigger>
                  <n-button circle secondary size="small" :type="segmentationEnabled ? 'primary' : 'default'" @click="toggleSegmentation">
                    <template #icon><n-icon><CutOutline /></n-icon></template>
                  </n-button>
                </template>
                意群/长难句分割
              </n-tooltip>

              <n-tooltip trigger="hover" :show-arrow="false">
                <template #trigger>
                  <n-button circle secondary size="small" :type="vocabHighlightEnabled ? 'warning' : 'default'" @click="toggleVocab">
                    <template #icon><n-icon><SearchOutline /></n-icon></template>
                  </n-button>
                </template>
                生词高亮
              </n-tooltip>
            </div>

            <!-- 导入按钮 -->
            <n-dropdown trigger="click" :options="uploadOptions" @select="handleUploadSelect" show-arrow>
              <n-button type="primary" size="small" class="ml-1 shadow-md shadow-indigo-500/20">
                <template #icon><n-icon><CloudUploadOutline /></n-icon></template>
                <span class="hidden sm:inline ml-1">导入</span>
              </n-button>
            </n-dropdown>
          </div>
        </div>
      </header>

      <!-- 主内容区域 -->
      <main class="flex-1 max-w-3xl mx-auto w-full px-4 py-8 pb-44 relative min-h-[calc(100vh-4rem)]">
        
        <!-- 空状态 / 引导页 -->
        <transition name="fade" mode="out-in">
          <div v-if="paragraphs.length === 0" class="flex flex-col items-center justify-center py-32 text-slate-400 select-none h-full">
            <div class="relative mb-8 group cursor-pointer" @click="fileInput.click()">
              <div class="absolute inset-0 bg-indigo-100 rounded-full scale-110 opacity-0 group-hover:opacity-100 transition-all duration-500 blur-xl"></div>
              <div class="w-20 h-20 bg-white border-2 border-dashed border-slate-300 rounded-full flex items-center justify-center relative z-10 group-hover:border-indigo-400 group-hover:scale-105 transition-all duration-300">
                <n-icon size="36" class="text-slate-300 group-hover:text-indigo-500 transition-colors"><DocumentTextOutline /></n-icon>
              </div>
            </div>
            <h2 class="text-lg font-bold text-slate-700 mb-2">开启深度阅读之旅</h2>
            <p class="text-sm text-slate-500 text-center max-w-[260px] leading-relaxed">
              支持 TXT, EPUB, MOBI, PDF<br>智能提取文本 · 神经机器翻译 · 意群分析
            </p>
          </div>

          <!-- 文章内容列表 -->
          <div v-else class="space-y-6">
            <!-- 顶部元数据 -->
            <div class="flex justify-between items-center px-2 pb-2 border-b border-slate-100">
              <span class="text-xs font-bold text-slate-400 uppercase tracking-widest">Reading Mode</span>
              <span class="text-xs font-mono text-slate-400">{{ paragraphs.length }} segments</span>
            </div>

            <transition-group name="list" tag="div" class="space-y-6">
              <div 
                v-for="(para, index) in paragraphs" 
                :key="para.id"
                :id="`para-${index}`"
                class="group relative p-6 rounded-2xl transition-all duration-500 cursor-pointer border border-transparent hover:bg-white hover:shadow-sm hover:border-slate-100"
                :class="currentPlayingIndex === index ? '!bg-white !shadow-xl !shadow-indigo-100/60 !border-indigo-100 ring-1 ring-indigo-50 scale-[1.02] z-10' : ''"
                @click="handleParagraphClick(index)"
              >
                <!-- 播放状态指示条 -->
                <div 
                  class="absolute left-0 top-6 bottom-6 w-1 rounded-r-full transition-all duration-300 origin-left"
                  :class="currentPlayingIndex === index ? 'bg-indigo-500 scale-x-100' : 'bg-slate-200 scale-x-0 group-hover:scale-x-50'"
                ></div>

                <!-- 段落序号 -->
                <div class="absolute -left-10 top-7 text-[10px] font-mono text-slate-300 opacity-0 lg:group-hover:opacity-100 transition-opacity text-right w-6">
                  {{ String(index + 1).padStart(2, '0') }}
                </div>

                <!-- 英文原文区域 -->
                <div v-if="viewMode !== 'cn'" class="relative mb-1">
                  <!-- 播放按钮 (悬浮) -->
                  <div class="absolute -right-2 -top-2 opacity-0 group-hover:opacity-100 transition-all duration-300 z-20 scale-75">
                    <n-button size="tiny" circle type="primary" class="shadow-lg" @click.stop="playParagraph(index)">
                       <template #icon><n-icon><Play /></n-icon></template>
                    </n-button>
                  </div>

                  <div class="font-serif text-lg sm:text-xl leading-[1.8] text-slate-800 tracking-wide text-justify">
                    <!-- 分割模式 -->
                    <template v-if="segmentationEnabled && para.chunks">
                      <span 
                        v-for="(chunk, cIndex) in para.chunks" 
                        :key="cIndex"
                        class="inline-block mr-2 mb-1 px-1.5 rounded hover:bg-indigo-50 hover:text-indigo-700 border-b-2 border-transparent hover:border-indigo-200 transition-all duration-200"
                        v-html="renderText(chunk)"
                      ></span>
                    </template>
                    <!-- 普通模式 -->
                    <template v-else>
                       <span v-html="renderText(para.enText)"></span>
                    </template>
                  </div>
                </div>

                <!-- 中文译文区域 -->
                <div v-if="viewMode !== 'en'" class="transition-all duration-500">
                   <div 
                     v-if="viewMode === 'dual'" 
                     class="mt-3 pt-3 border-t border-dashed border-slate-100"
                   ></div>
                   <p class="text-[15px] leading-7 text-slate-500 font-sans text-justify font-normal">
                     {{ para.cnText || 'Wait for translation...' }}
                   </p>
                </div>
              </div>
            </transition-group>
          </div>
        </transition>
      </main>

      <!-- 底部悬浮播放器 -->
      <transition name="slide-up">
        <div v-if="paragraphs.length > 0" class="fixed bottom-6 left-0 right-0 z-40 px-4 flex justify-center pointer-events-none">
          <div class="bg-slate-900/90 backdrop-blur-md text-white pl-4 pr-4 py-3 rounded-2xl shadow-2xl shadow-slate-900/30 w-full max-w-lg pointer-events-auto border border-slate-700/50 flex flex-col gap-1">
            
            <!-- 播放器上半部：控制与信息 -->
            <div class="flex items-center gap-4">
              <!-- 主播放按钮 -->
              <button 
                class="w-10 h-10 rounded-full bg-indigo-500 hover:bg-indigo-400 active:scale-95 flex items-center justify-center transition-all shadow-lg shadow-indigo-500/40 shrink-0"
                @click="togglePlay"
              >
                <n-icon size="20" color="white">
                  <Pause v-if="isPlaying" />
                  <Play v-else class="ml-0.5" />
                </n-icon>
              </button>

              <!-- 文本信息 -->
              <div class="flex-1 min-w-0 flex flex-col justify-center h-10">
                <div class="flex items-center gap-2">
                  <span class="text-[10px] font-bold text-indigo-400 bg-indigo-900/30 px-1.5 py-0.5 rounded uppercase tracking-wider">
                    {{ isPlaying ? 'Reading' : 'Paused' }}
                  </span>
                  <span class="text-[10px] text-slate-400 font-mono">
                     Paragraph {{ currentPlayingIndex + 1 }} / {{ paragraphs.length }}
                  </span>
                </div>
                <div class="text-sm text-slate-200 truncate font-serif opacity-90 mt-0.5">
                  {{ currentTextPreview }}
                </div>
              </div>

              <!-- 右侧控制组 -->
              <div class="flex items-center gap-1 pl-2 border-l border-slate-700/60">
                 <n-button text class="text-slate-400 hover:text-white w-8 h-8" @click="changeParagraph(-1)">
                    <template #icon><n-icon size="18"><PlaySkipBack /></n-icon></template>
                 </n-button>
                 <n-button text class="text-slate-400 hover:text-white w-8 h-8" @click="changeParagraph(1)">
                    <template #icon><n-icon size="18"><PlaySkipForward /></n-icon></template>
                 </n-button>
                 
                 <!-- 倍速选择 -->
                 <n-popselect v-model:value="ttsSpeed" :options="speedOptions" trigger="click" placement="top-end" class="bg-slate-800 border-slate-700">
                    <button class="ml-1 px-2 py-1 rounded text-[10px] font-bold bg-slate-800 text-indigo-300 hover:bg-slate-700 border border-slate-600 transition-colors min-w-[3rem]">
                      {{ ttsSpeed }}x
                    </button>
                 </n-popselect>
              </div>
            </div>

            <!-- 进度条 -->
            <div class="pt-1 px-1">
               <n-progress 
                type="line" 
                :percentage="playProgress" 
                :show-indicator="false" 
                color="#6366f1" 
                rail-color="#334155"
                processing
                height="2"
                class="cursor-pointer opacity-80 hover:opacity-100 transition-opacity"
              />
            </div>

          </div>
        </div>
      </transition>

      <!-- 隐藏的文件输入 -->
      <input type="file" ref="fileInput" class="hidden" @change="handleFileChange" accept=".txt,.epub,.mobi,.pdf" />
      <input type="file" ref="vocabInput" class="hidden" @change="handleVocabChange" accept=".txt,.json,.csv" />

    </div>
  </n-config-provider>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { 
  NConfigProvider, NButton, NIcon, NRadioGroup, NRadioButton, 
  NDivider, NTooltip, NDropdown, NProgress, NPopselect, createDiscreteApi 
} from 'naive-ui'
import { 
  BookOutline, CloudUploadOutline, CutOutline, SearchOutline, 
  Play, Pause, DocumentTextOutline, EyeOutline,
  PlaySkipBack, PlaySkipForward
} from '@vicons/ionicons5'

// --- 主题配置 ---
const themeOverrides = {
  common: {
    primaryColor: '#4f46e5', // Indigo-600
    primaryColorHover: '#4338ca',
    primaryColorPressed: '#3730a3',
    borderRadius: '8px',
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
  },
  Button: {
    heightSmall: '32px',
    fontSizeSmall: '13px',
  }
}

// 消息提示API
const { message } = createDiscreteApi(['message'], {
  configProviderProps: { themeOverrides }
})

// --- 状态变量 ---
const viewMode = ref('dual') // en, cn, dual
const segmentationEnabled = ref(false)
const vocabHighlightEnabled = ref(false)
const isPlaying = ref(false)
const currentPlayingIndex = ref(-1)
const ttsSpeed = ref(1.0)
const currentTime = ref(0)
const totalTime = ref(100) // 模拟当前段落总时长

const fileInput = ref(null)
const vocabInput = ref(null)
const paragraphs = ref([])

// 模拟用户生词库
const userVocabList = ref(new Set(['intelligence', 'cognitive', 'perceives', 'autonomous', 'heuristic', 'algorithm'])) 

// --- 选项配置 ---
const uploadOptions = [
  { label: '上传文档 (PDF/EPUB/TXT)', key: 'doc' },
  { label: '上传生词库', key: 'vocab' }
]

const viewModeOptions = [
  { label: '仅英文', value: 'en' },
  { label: '中英对照', value: 'dual' },
  { label: '仅中文', value: 'cn' },
]

const speedOptions = [
  { label: '0.75x', value: 0.75 },
  { label: '1.0x', value: 1.0 },
  { label: '1.25x', value: 1.25 },
  { label: '1.5x', value: 1.5 },
  { label: '2.0x', value: 2.0 },
]

// --- 核心业务逻辑 (模拟) ---

// 1. 重置
const resetApp = () => {
  if(paragraphs.value.length > 0) {
    if(confirm('确定要清空当前阅读内容吗？')) {
      paragraphs.value = []
      isPlaying.value = false
      currentPlayingIndex.value = -1
    }
  }
}

// 2. 文本渲染 (处理高亮)
// 简单的 HTML 注入，实际生产环境需注意 XSS 防护
const renderText = (text) => {
  if (!text) return ''
  if (!vocabHighlightEnabled.value) return text
  
  let processed = text
  const sortedVocab = Array.from(userVocabList.value).sort((a, b) => b.length - a.length)
  
  sortedVocab.forEach(word => {
    // 匹配单词边界，不区分大小写
    const regex = new RegExp(`\\b(${word})\\b`, 'gi')
    processed = processed.replace(regex, '<span class="bg-amber-200 text-amber-900 px-0.5 rounded shadow-sm font-medium">$1</span>')
  })
  return processed
}

// 3. 模拟后端：提取文本
const mockExtractText = () => {
  return new Promise(resolve => {
    setTimeout(() => {
      resolve([
        { id: 1, enText: "Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to the natural intelligence displayed by animals including humans.", cnText: "", chunks: null },
        { id: 2, enText: "Leading AI textbooks define the field as the study of \"intelligent agents\": any system that perceives its environment and takes actions that maximize its chance of achieving its goals.", cnText: "", chunks: null },
        { id: 3, enText: "Some popular accounts use the term \"artificial intelligence\" to describe machines that mimic \"cognitive\" functions that humans associate with the human mind, such as \"learning\" and \"problem solving\".", cnText: "", chunks: null },
        { id: 4, enText: "The field was founded on the assumption that human intelligence can be so precisely described that a machine can be made to simulate it.", cnText: "", chunks: null },
        { id: 5, enText: "This raises philosophical arguments about the mind and the ethics of creating artificial beings endowed with human-like intelligence.", cnText: "", chunks: null },
      ])
    }, 800)
  })
}

// 4. 模拟后端：翻译
const mockTranslate = async (text) => {
  // 简单模拟延迟返回
  await new Promise(r => setTimeout(r, Math.random() * 500 + 200))
  return "（模拟翻译结果）" + text.substring(0, 20) + "... 这是一段由后端API生成的中文对照翻译，旨在帮助用户理解长难句结构。"
}

// 5. 模拟后端：意群分割
const mockSegmentation = async (text) => {
  // 简单按标点和连词分割模拟
  return text
    .replace(/([,.:;])/g, '$1|')
    .replace(/\b(that|which|as|and|but|or|because)\b/gi, '|$1')
    .split('|')
    .map(s => s.trim())
    .filter(s => s.length > 0)
}

// --- 事件处理 ---

const handleUploadSelect = (key) => {
  if (key === 'doc') fileInput.value.click()
  if (key === 'vocab') vocabInput.value.click()
}

const handleFileChange = async (e) => {
  const file = e.target.files[0]
  if (!file) return
  
  message.loading("正在解析文档结构...")
  // 模拟 API 调用
  const extracted = await mockExtractText()
  paragraphs.value = extracted
  message.success("解析完成，开始后台翻译...")
  
  // 并发/流式翻译模拟
  extracted.forEach(async (p, index) => {
    p.cnText = await mockTranslate(p.enText)
  })
  
  // 清理 Input
  e.target.value = ''
}

const handleVocabChange = (e) => {
  if(e.target.files[0]) {
    message.success("词汇库导入成功，已更新高亮索引")
    // 实际逻辑会解析文件内容到 userVocabList
    e.target.value = ''
  }
}

const toggleSegmentation = async () => {
  segmentationEnabled.value = !segmentationEnabled.value
  if (segmentationEnabled.value) {
    const needsSeg = paragraphs.value.some(p => !p.chunks)
    if (needsSeg) {
      message.loading("正在进行句法分析...")
      for (let p of paragraphs.value) {
        if (!p.chunks) p.chunks = await mockSegmentation(p.enText)
      }
      message.success("意群分割完成")
    }
  }
}

const toggleVocab = () => {
  vocabHighlightEnabled.value = !vocabHighlightEnabled.value
  if(vocabHighlightEnabled.value) message.info("生词高亮已开启")
}

// --- 播放器逻辑 ---

const togglePlay = () => {
  if (isPlaying.value) {
    pauseTTS()
  } else {
    if (currentPlayingIndex.value === -1 && paragraphs.value.length > 0) {
      playParagraph(0)
    } else {
      resumeTTS()
    }
  }
}

const playParagraph = (index) => {
  if (index < 0 || index >= paragraphs.value.length) return
  
  currentPlayingIndex.value = index
  isPlaying.value = true
  currentTime.value = 0
  totalTime.value = 100 // 实际应由 TTS API 返回音频时长
  
  // 自动滚动定位
  const el = document.getElementById(`para-${index}`)
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
  
  startProgressTimer()
}

const changeParagraph = (offset) => {
  const newIndex = currentPlayingIndex.value + offset
  if (newIndex >= 0 && newIndex < paragraphs.value.length) {
    playParagraph(newIndex)
  }
}

const pauseTTS = () => {
  isPlaying.value = false
  stopProgressTimer()
}

const resumeTTS = () => {
  isPlaying.value = true
  startProgressTimer()
}

let timer = null
const startProgressTimer = () => {
  stopProgressTimer()
  timer = setInterval(() => {
    if (!isPlaying.value) return
    
    if (currentTime.value >= totalTime.value) {
      // 本段播放结束，自动下一段
      if (currentPlayingIndex.value < paragraphs.value.length - 1) {
        playParagraph(currentPlayingIndex.value + 1)
      } else {
        isPlaying.value = false
        currentTime.value = 0
        stopProgressTimer()
      }
    } else {
      currentTime.value += (1 * ttsSpeed.value)
    }
  }, 50)
}

const stopProgressTimer = () => {
  if (timer) clearInterval(timer)
}

const handleParagraphClick = (index) => {
  // 点击段落即播放
  playParagraph(index)
}

// --- Computed ---
const playProgress = computed(() => {
  if (totalTime.value === 0) return 0
  return Math.min(100, (currentTime.value / totalTime.value) * 100)
})

const currentTextPreview = computed(() => {
  if (currentPlayingIndex.value === -1) return 'Ready to start'
  return paragraphs.value[currentPlayingIndex.value]?.enText || ''
})

</script>

<style scoped>
/* 列表动画 */
.list-enter-active,
.list-leave-active {
  transition: all 0.5s ease;
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

/* 基础淡入淡出 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 底部播放器滑入 */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.4s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}
</style>