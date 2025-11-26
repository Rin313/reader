<template>
  <n-config-provider :theme-overrides="themeOverrides">
    <div class="min-h-screen bg-[#f8fafc] text-slate-800 flex flex-col font-sans selection:bg-indigo-100 selection:text-indigo-700">
      <header class="sticky top-0 z-50 bg-white/90 backdrop-blur-md border-b border-slate-200/60 transition-all duration-300 supports-backdrop-blur:bg-white/60">
        <div class="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <!-- Logo -->
          <div class="flex items-center gap-3 cursor-pointer select-none group" @click="resetReader">
            <div class="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
              <n-icon size="24" color="#fff"><BookOutline /></n-icon>
            </div>
            <div class="flex flex-col">
              <span class="text-lg font-bold tracking-tight text-slate-900 leading-none">DeepReader</span>
              <span class="text-[10px] text-slate-500 font-medium tracking-wide uppercase">Immersive Learning</span>
            </div>
          </div>
          <div class="flex items-center gap-4">
            <!-- 视图切换 -->
            <div class="hidden sm:block p-1 bg-slate-100 rounded-lg">
              <n-radio-group v-model:value="viewMode" size="small" @update:value="handleViewModeChange">
                <n-radio-button value="en" class="px-3">EN</n-radio-button>
                <n-radio-button value="dual" class="px-3">Dual</n-radio-button>
                <n-radio-button value="cn" class="px-3">CN</n-radio-button>
              </n-radio-group>
            </div>

            <n-divider vertical class="!h-6 !bg-slate-200 hidden sm:block" />
            <n-popselect v-model:value="currentTranslator" :options="translatorOptions" trigger="click">
              <n-button circle secondary type="default" class="!w-9 !h-9 mr-1">
                <template #icon><n-icon size="18"><LanguageOutline /></n-icon></template>
              </n-button>
            </n-popselect>

            <div class="flex items-center gap-2">
              <n-tooltip trigger="hover" :show-arrow="false">
                <template #trigger>
                  <n-button circle secondary :type="segmentationEnabled ? 'primary' : 'default'" @click="toggleSegmentation" class="!w-9 !h-9">
                    <template #icon><n-icon size="18"><GitNetworkOutline /></n-icon></template>
                  </n-button>
                </template>
                {{ segmentationEnabled ? '关闭意群分割' : '开启意群分割' }}
              </n-tooltip>

              <n-tooltip trigger="hover" :show-arrow="false">
                <template #trigger>
                  <n-button circle secondary :type="vocabHighlightEnabled ? 'warning' : 'default'" @click="toggleVocab" class="!w-9 !h-9">
                    <template #icon><n-icon size="18"><SearchOutline /></n-icon></template>
                  </n-button>
                </template>
                {{ vocabHighlightEnabled ? '关闭生词高亮' : '开启生词高亮' }}
              </n-tooltip>
              
              <n-tooltip trigger="hover" :show-arrow="false">
                <template #trigger>
                  <n-button circle secondary type="default" @click="vocabInputRef.click()" class="!w-9 !h-9">
                    <template #icon><n-icon size="16"><LibraryOutline /></n-icon></template>
                  </n-button>
                </template>
                导入词汇库
              </n-tooltip>
            </div>
          </div>
        </div>
      </header>

      <!-- 2. 主内容区域 -->
      <main class="flex-1 max-w-3xl mx-auto w-full px-4 py-10 pb-48 relative">
        <transition name="fade" mode="out-in">
          
          <!-- 空状态 -->
          <div v-if="paragraphs.length === 0" class="flex flex-col items-center justify-center py-20 select-none min-h-[60vh]">
            <div 
              class="w-full max-w-lg border-2 border-dashed border-slate-300 hover:border-indigo-400 hover:bg-indigo-50/30 bg-white rounded-3xl p-12 flex flex-col items-center text-center transition-all duration-300 cursor-pointer group"
              @click="fileInputRef.click()"
            >
              <div class="w-20 h-20 bg-indigo-50 text-indigo-500 group-hover:bg-indigo-100 group-hover:scale-110 transition-all rounded-full flex items-center justify-center mb-6 shadow-sm">
                <n-icon size="40"><CloudUploadOutline /></n-icon>
              </div>
              <h2 class="text-xl font-bold text-slate-700 mb-2 group-hover:text-indigo-600 transition-colors">点击上传书籍</h2>
              <p class="text-sm text-slate-400 mb-6">支持 TXT, EPUB, MOBI, PDF<br>智能提取文本与意群分析</p>
            </div>
          </div>

          <!-- 阅读区域 -->
          <div v-else class="space-y-8">
            <!-- 顶部状态栏 -->
            <div class="sticky top-20 z-20 flex justify-between items-center px-2 py-2 bg-[#f8fafc]/90 backdrop-blur text-xs text-slate-500 border-b border-slate-200/50">
              <span>共 {{ paragraphs.length }} 个段落 | 翻译引擎: {{ currentTranslator }}</span>
              <span v-if="isBatchTranslating" class="text-amber-600 flex items-center gap-1">
                <n-icon class="animate-spin"><ReloadOutline /></n-icon> 正在翻译...
              </span>
              <span v-if="isPlaying || isBuffering" class="text-indigo-500 font-medium flex items-center gap-1" :class="{'animate-pulse': isBuffering}">
                <n-icon><PulseOutline /></n-icon> {{ isBuffering ? '加载语音...' : '正在朗读...' }}
              </span>
            </div>

            <div 
              v-for="(para, index) in paragraphs" 
              :key="para.id"
              :id="`para-${index}`"
              :data-index="index"
              class="para-observer-item relative p-6 sm:p-8 rounded-2xl transition-all duration-300 border scroll-m-32"
              :class="getParagraphClass(index)"
              @click="playParagraph(index)"
            >
              <!--Active indicator & index  -->
              <div v-if="currentPlayingIndex === index" class="absolute left-0 top-8 bottom-8 w-1 bg-indigo-500 rounded-r-full"></div>
              <span class="absolute top-4 left-4 text-[10px] font-mono text-slate-300 select-none">#{{ index + 1 }}</span>

              <!-- Loading Indicators -->
              <div class="absolute top-4 right-4 flex gap-2">
                 <n-icon v-if="para.processingSegment" size="16" class="animate-spin text-indigo-300"><GitNetworkOutline /></n-icon>
                 <n-icon v-if="para.translating" size="16" class="animate-spin text-amber-400" title="翻译中..."><LanguageOutline /></n-icon>
              </div>

              <!-- 英文内容 -->
              <div v-if="viewMode !== 'cn'" class="relative">
                <!-- 当前正在读英文部分时高亮颜色加深 -->
                <div class="font-serif text-xl tracking-wide transition-colors duration-300" 
                     :class="[
                       segmentationEnabled ? 'leading-[2.6]' : 'leading-[1.8]',
                       (currentPlayingIndex === index && readingPhase === 'en') ? 'text-indigo-900 font-medium' : 'text-slate-800'
                     ]">
                  <template v-if="segmentationEnabled && para.chunks?.length">
                    <span 
                      v-for="(chunk, cIndex) in para.chunks" 
                      :key="cIndex"
                      class="inline-block mr-2 mb-1 px-1.5 py-0.5 rounded-md bg-slate-100 hover:bg-indigo-50 border-b-2 border-slate-200 hover:border-indigo-300 cursor-text transition-colors text-[0.95em]"
                      v-html="getChunkHtml(para, cIndex, chunk)"
                    ></span>
                  </template>
                  <template v-else>
                     <span v-html="getRawHtml(para)"></span>
                  </template>
                </div>
              </div>

              <!-- 中文内容 -->
              <div v-if="viewMode !== 'en'" class="mt-4 pt-4 border-t border-dashed border-slate-200">
                <!-- 骨架屏 Loading -->
                <div v-if="!para.cnText && para.translating" class="space-y-2 animate-pulse">
                   <div class="h-4 bg-slate-200 rounded w-3/4"></div>
                   <div class="h-4 bg-slate-200 rounded w-1/2"></div>
                </div>
                <!-- 翻译结果 -->
                <p v-else class="text-base leading-8 font-sans text-justify transition-colors duration-300"
                   :class="(currentPlayingIndex === index && readingPhase === 'cn') ? 'text-indigo-700 font-medium' : 'text-slate-500 hover:text-slate-700'">
                  {{ para.cnText || '（翻译中...）' }}
                </p>
              </div>
            </div>
            
            <div class="h-24"></div>
          </div>
        </transition>
      </main>

      <!-- 3. 底部悬浮播放器 -->
      <transition name="slide-up">
        <div v-if="paragraphs.length > 0" class="fixed bottom-6 left-0 right-0 z-40 px-4 flex justify-center pointer-events-none">
           <div class="bg-slate-900/95 backdrop-blur-xl text-white p-3 pl-4 rounded-2xl shadow-2xl shadow-slate-900/30 w-full max-w-xl pointer-events-auto border border-slate-700/50 flex flex-col gap-2 ring-1 ring-white/10">
            <div class="flex items-center gap-4">
              <!-- Play/Pause Button with Loading State -->
              <button 
                class="w-12 h-12 rounded-full bg-indigo-600 hover:bg-indigo-500 active:scale-95 flex items-center justify-center transition-all shadow-lg shadow-indigo-500/30 group relative"
                @click="togglePlay"
              >
                <n-icon size="24" class="text-white group-hover:scale-110 transition-transform" v-if="!isBuffering">
                  <Pause v-if="isPlaying" />
                  <Play v-else class="ml-1" />
                </n-icon>
                <n-icon size="24" class="text-white animate-spin" v-else>
                  <ReloadOutline />
                </n-icon>
              </button>

              <div class="flex-1 min-w-0 flex flex-col justify-center">
                <div class="text-[10px] text-indigo-300 font-bold tracking-wider uppercase mb-0.5 flex items-center gap-2">
                  <span v-if="readingPhase" class="bg-indigo-500/20 px-1 rounded text-[9px] border border-indigo-500/30">{{ readingPhase === 'en' ? 'ENGLISH' : 'CHINESE' }}</span>
                </div>
                <div class="text-sm text-slate-100 truncate font-serif opacity-90">
                  {{ currentTextPreview }}
                </div>
              </div>
               <n-popselect v-model:value="ttsSpeed" :options="speedOptions" trigger="click" placement="top-end" @update:value="onSpeedChange">
                <button class="px-2 py-1 ml-2 rounded text-xs font-bold bg-slate-800 text-slate-300 hover:text-white border border-slate-700 transition-colors min-w-[3rem]">
                  {{ ttsSpeed }}x
                </button>
              </n-popselect>
            </div>
            <!-- Progress Bar -->
            <div class="px-1 pb-1 pt-1 relative group">
               <n-progress 
                type="line" :percentage="playProgress" :show-indicator="false" 
                color="#818cf8" rail-color="#334155" height="3" class="cursor-pointer"
              />
              <div class="absolute top-0 left-0 w-full h-full cursor-pointer" @click="seekAudio"></div> 
              <div class="flex justify-between mt-1.5 text-[10px] text-slate-500 font-mono">
                <span>{{ formatTime(currentTime) }}</span>
              </div>
            </div>
          </div>
        </div>
      </transition>

      <!-- 模态框 -->
      <n-modal v-model:show="showColumnSelector" preset="card" title="选择单词所在的列" class="max-w-lg w-[90vw]">
          <div class="max-h-[60vh] overflow-y-auto pr-1 custom-scrollbar">
           <p class="text-slate-500 text-sm mb-4">检测到以下表格列，请选择包含英文单词的那一列进行导入：</p>
           <div class="grid grid-cols-1 gap-2">
             <div 
                v-for="(col, idx) in excelColumns" 
                :key="idx"
                class="p-3 border border-slate-200 rounded-lg hover:border-indigo-500 hover:bg-indigo-50 cursor-pointer transition-all flex flex-col"
                @click="confirmColumnSelection(idx)"
             >
                <span class="font-bold text-slate-700 text-sm">{{ col.header || `第 ${idx + 1} 列` }}</span>
                <span class="text-xs text-slate-400 mt-1 truncate">预览: {{ col.preview }}</span>
             </div>
           </div>
        </div>
      </n-modal>

      <!-- Hidden Inputs -->
      <input type="file" ref="fileInputRef" class="hidden" @change="handleFileChange" accept=".txt,.epub,.mobi,.pdf" />
      <input type="file" ref="vocabInputRef" class="hidden" @change="handleVocabFileParse" accept=".csv,.xlsx" />

    </div>
  </n-config-provider>
</template>

<script setup>
import { ref, computed, onBeforeUnmount, shallowRef, onMounted } from 'vue'
import { 
  NConfigProvider, NButton, NIcon, NRadioGroup, NRadioButton, 
  NDivider, NTooltip, NProgress, NPopselect, NModal, createDiscreteApi 
} from 'naive-ui'
import { 
  BookOutline, CloudUploadOutline, SearchOutline, LanguageOutline, ReloadOutline,
  Play, Pause, GitNetworkOutline, LibraryOutline, PulseOutline,
} from '@vicons/ionicons5'
import { 
  uploadAndExtract, segmentSentence, readExcelFile, extractColumnFromData, 
  getIndexed, setIndexed, matchVocabulary, translateParagraphs,translatorOptions
} from './assets/common'

// --- Theme & Config ---
const themeOverrides = {
  common: { primaryColor: '#4f46e5', primaryColorHover: '#4338ca', borderRadius: '8px' }
}
const { message } = createDiscreteApi(['message'], { configProviderProps: { themeOverrides } })

// --- Refs & State ---
const fileInputRef = ref(null)
const vocabInputRef = ref(null)
const paragraphs = ref([]) 
const viewMode = ref('dual')

// 功能开关
const segmentationEnabled = ref(false)
const vocabHighlightEnabled = ref(false)
const userVocabList = shallowRef(new Set())

// 翻译相关状态
const currentTranslator = ref('google')

const translationQueue = new Set() 
let translationTimer = null
const isBatchTranslating = ref(false)

// TTS 状态 (Real Implementation)
let abortController = null // 为了在请求新语音时取消旧请求
const audio = new Audio()
const isPlaying = ref(false)
const isBuffering = ref(false)
const currentPlayingIndex = ref(-1)
const ttsSpeed = ref(1.0)
const currentTime = ref(0)
const totalTime = ref(0)
const readingPhase = ref('en') // 'en' | 'cn'

// 词汇导入 UI 状态
const showColumnSelector = ref(false)
const excelSheetData = shallowRef([])
const excelColumns = ref([])

// --- TTS 工具函数  ---
const getAudioUrl = async (text, voice, rate="+0%") => {
  // 取消上一个挂起的请求
  if (abortController) abortController.abort()
  abortController = new AbortController()

  try {
    const response = await fetch('http://127.0.0.1:8000/tts', { 
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice, rate }),
      signal: abortController.signal
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.detail || 'TTS request failed')
    }
    const audioBlob = await response.blob()
    return URL.createObjectURL(audioBlob)
  } catch (error) {
    if (error.name === 'AbortError') return null
    console.error('TTS Fetch Error:', error)
    throw error
  }
}

// --- Logic: 初始化 ---
onMounted(async () => {
  try {
    const data = await getIndexed('vocabs', [])
    if (Array.isArray(data)) userVocabList.value = new Set(data)
  } catch (e) { console.error('本地词库加载失败', e) }

  // 绑定 Audio 事件
  audio.addEventListener('timeupdate', () => {
    currentTime.value = audio.currentTime
  })
  audio.addEventListener('loadedmetadata', () => {
    totalTime.value = audio.duration
    isBuffering.value = false // 加载完毕，停止 buffering 动画
  })
  audio.addEventListener('waiting', () => { isBuffering.value = true })
  audio.addEventListener('playing', () => { isBuffering.value = false; isPlaying.value = true })
  audio.addEventListener('pause', () => { isPlaying.value = false })
  
  // 核心自动播放逻辑
  audio.addEventListener('ended', async () => {
    // 如果当前模式是双语，且刚刚读完英文，则切换到中文
    if (viewMode.value === 'dual' && readingPhase.value === 'en') {
      const p = paragraphs.value[currentPlayingIndex.value]
      // 只有当有中文翻译时才读，否则直接跳下一段
      if (p && p.cnText) {
        readingPhase.value = 'cn'
        await loadAndPlayAudio()
        return
      }
    }
    
    // 否则跳到下一段 (或如果是最后一段则停止)
    if (currentPlayingIndex.value < paragraphs.value.length - 1) {
      playParagraph(currentPlayingIndex.value + 1)
    } else {
      isPlaying.value = false
      currentPlayingIndex.value = -1
      currentTime.value = 0
      totalTime.value = 0
    }
  })
})

// --- Logic: 阅读器核心 ---
const getParagraphClass = (index) => {
  const isActive = currentPlayingIndex.value === index
  return [
    'group',
    isActive 
      ? 'bg-white shadow-xl shadow-indigo-100/60 border-indigo-200 ring-1 ring-indigo-100 z-10' 
      : 'bg-white shadow-sm hover:shadow-md hover:border-slate-300 border-transparent'
  ]
}

const resetReader = () => {
  if(paragraphs.value.length && confirm('确定要清空当前书籍吗？')) {
    pauseTTS()
    audio.src = '' // 清空音频
    paragraphs.value = []
    currentPlayingIndex.value = -1
    translationQueue.clear()
    observer?.disconnect()
  }
}

const handleFileChange = async (e) => {
  const file = e.target.files[0]
  if (!file) return
  try {
    const extracted = await uploadAndExtract(file);
    if (extracted?.lines?.length) {
      paragraphs.value = extracted.lines.map((line, index) => ({
        id: `p-${index}`,
        enText: line,
        cnText: '', 
        chunks: null, 
        enTextDisplay: null, 
        chunksDisplay: null, 
        processingSegment: false,
        processingVocab: false,
        translating: false 
      }));
      message.success(`导入成功`);
      setTimeout(() => { initObserver() }, 100)
    } else {
      message.error("未提取到有效文本");
    }
  } catch (error) {
    message.error("解析失败");
    console.error(error);
  } finally {
    e.target.value = ''
  }
}

// --- Logic: 核心调度逻辑 ---
const handleViewModeChange = () => {
  initObserver()
  // 如果正在播放且模式改变，可能需要重启当前段落的播放逻辑
  if (isPlaying.value) {
    playParagraph(currentPlayingIndex.value)
  }
}

const processParagraph = async (index) => {
  const p = paragraphs.value[index]
  if (!p) return
  const needsChinese = viewMode.value === 'cn' || viewMode.value === 'dual'
  const needsEnglishEnhancement = viewMode.value === 'en' || viewMode.value === 'dual'

  if (needsChinese) {
    if (!p.cnText && !p.translating) queueTranslation(index)
  }
  if (needsEnglishEnhancement) {
    if (segmentationEnabled.value && !p.chunks && !p.processingSegment) {
      p.processingSegment = true
      try {
        const res = await segmentSentence(p.enText)
        p.chunks = res?.segments || [p.enText]
      } catch { p.chunks = [p.enText] } 
      finally { 
        p.processingSegment = false
        if (vocabHighlightEnabled.value) matchAndHighlight(index)
      }
    }
    if (vocabHighlightEnabled.value) matchAndHighlight(index)
  }
}

// --- Logic: 翻译队列 ---
const queueTranslation = (index) => {
  if (translationQueue.has(index)) return
  const p = paragraphs.value[index]
  if (p.cnText || p.translating) return
  translationQueue.add(index)
  p.translating = true 
  if (translationTimer) clearTimeout(translationTimer)
  translationTimer = setTimeout(flushTranslationQueue, 600)
}

const flushTranslationQueue = async () => {
  if (translationQueue.size === 0) return
  const indices = Array.from(translationQueue).sort((a,b) => a - b).slice(0, 10)
  indices.forEach(i => translationQueue.delete(i))
  if (translationQueue.size > 0) translationTimer = setTimeout(flushTranslationQueue, 1000)
  
  isBatchTranslating.value = true
  const textsToTranslate = indices.map(i => paragraphs.value[i].enText)
  
  try {
    const translatedTexts = await translateParagraphs(textsToTranslate, currentTranslator.value, 'en', 'zh')
    indices.forEach((idx, arrayIndex) => {
      if (paragraphs.value[idx]) {
        paragraphs.value[idx].cnText = translatedTexts[arrayIndex]
        paragraphs.value[idx].translating = false
      }
    })
  } catch (error) {
    console.error("Translation error", error)
    message.warning("部分翻译失败，请滚动重试")
    indices.forEach(idx => { if (paragraphs.value[idx]) paragraphs.value[idx].translating = false })
  } finally {
    isBatchTranslating.value = false
  }
}

// --- Logic: 词汇表导入 ---
const handleVocabFileParse = async (e) => {
  const file = e.target.files[0]
  if (!file) return
  e.target.value = ''
  try {
    const data = await readExcelFile(file)
    if (!data || data.length === 0) throw new Error("文件为空")
    excelSheetData.value = data
    excelColumns.value = (data[0] || []).map((header, idx) => ({
      header: header,
      preview: `${data[1]?.[idx] || '-'}, ${data[2]?.[idx] || '-'}`
    }))
    showColumnSelector.value = true
  } catch (err) { message.error("Excel 解析失败") }
}

const confirmColumnSelection = async (colIndex) => {
  showColumnSelector.value = false
  try {
    const words = extractColumnFromData(excelSheetData.value, colIndex)
    if (!words.length) { message.warning("该列没有有效数据"); return }
    await setIndexed('vocabs', words)
    userVocabList.value = new Set(words)
    paragraphs.value.forEach(p => { p.enTextDisplay = null; p.chunksDisplay = null })
    message.success(`已导入 ${words.length} 个生词`)
    if (vocabHighlightEnabled.value) initObserver()
  } catch (e) { message.error("保存词库失败") }
}

// --- Logic: 文本处理工具 ---
const generateHighlightHtml = (text, matches) => {
  if (!text) return ''
  if (!matches?.length) return text
  const sorted = [...matches].sort((a, b) => b.start - a.start)
  let result = text
  sorted.forEach(m => {
    const { start, length } = m
    if (start < 0 || start + length > result.length) return
    const word = result.slice(start, start + length)
    result = result.slice(0, start) + `<span class="bg-amber-200 text-amber-900 border-b-2 border-amber-300 rounded-sm px-0.5 mx-0.5 font-semibold cursor-help hover:bg-amber-300">${word}</span>` + result.slice(start + length)
  })
  return result
}

const getRawHtml = (para) => (vocabHighlightEnabled.value && para.enTextDisplay) ? para.enTextDisplay : para.enText
const getChunkHtml = (para, index, originalChunk) => (vocabHighlightEnabled.value && para.chunksDisplay?.[index]) ? para.chunksDisplay[index] : originalChunk

const matchAndHighlight = async (index) => {
  const p = paragraphs.value[index]
  if (!userVocabList.value.size) return
  const isChunkMode = segmentationEnabled.value && p.chunks?.length
  const hasCache = isChunkMode ? !!p.chunksDisplay : !!p.enTextDisplay
  if (hasCache || p.processingVocab) return
  p.processingVocab = true
  const targets = isChunkMode ? p.chunks : [p.enText]
  try {
    const results = await matchVocabulary(Array.from(userVocabList.value), targets)
    if (results && results.length === targets.length) {
      if (isChunkMode) p.chunksDisplay = targets.map((t, i) => generateHighlightHtml(t, results[i]))
      else p.enTextDisplay = generateHighlightHtml(targets[0], results[0])
    }
  } finally { p.processingVocab = false }
}

// --- Logic: 懒加载观察者 ---
let observer = null
const initObserver = () => {
  if (observer) observer.disconnect()
  observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const idx = Number(entry.target.dataset.index)
        if (!isNaN(idx)) processParagraph(idx)
      }
    })
  }, { rootMargin: '400px 0px 400px 0px', threshold: 0.01 })
  const elements = document.querySelectorAll('.para-observer-item')
  if (elements.length > 0) elements.forEach(el => observer.observe(el))
}

const toggleSegmentation = () => {
  segmentationEnabled.value = !segmentationEnabled.value
  initObserver()
}

const toggleVocab = () => {
  vocabHighlightEnabled.value = !vocabHighlightEnabled.value
  if (vocabHighlightEnabled.value) {
    if (userVocabList.value.size === 0) message.warning("请先导入词汇库")
    initObserver()
  }
}

onBeforeUnmount(() => {
  observer?.disconnect()
  if (translationTimer) clearTimeout(translationTimer)
  if (audio) {
    audio.pause()
    audio.src = ''
  }
  if (abortController) abortController.abort()
})

// --- Logic: 真实播放器控制 ---
const currentTextPreview = computed(() => {
  const p = paragraphs.value[currentPlayingIndex.value]
  if (!p) return 'Ready to play'
  if (readingPhase.value === 'cn' && p.cnText) return p.cnText
  return p.enText
})

const playProgress = computed(() => totalTime.value > 0 ? (currentTime.value / totalTime.value) * 100 : 0)
const formatTime = (sec) => `00:${Math.floor(sec).toString().padStart(2, '0')}`
const speedOptions = [0.75, 1.0, 1.25, 1.5].map(v => ({ label: `${v}x`, value: v }))

const togglePlay = () => {
  if (isPlaying.value) {
    audio.pause()
    isPlaying.value = false
  } else {
    if (currentPlayingIndex.value === -1 && paragraphs.value.length > 0) {
      playParagraph(0)
    } else {
      audio.play().catch(e => console.error("Resume failed", e))
    }
  }
}

const pauseTTS = () => {
  audio.pause()
  isPlaying.value = false
}

const seekAudio = (e) => { 
  if (!totalTime.value) return
  const rect = e.target.getBoundingClientRect()
  const percent = (e.clientX - rect.left) / rect.width
  const newTime = percent * totalTime.value
  audio.currentTime = newTime
  currentTime.value = newTime
}

const onSpeedChange = () => {
  // 如果正在播放，语速改变需要重新请求音频
  if (currentPlayingIndex.value !== -1) {
    playParagraph(currentPlayingIndex.value, false) // false = don't reset phase
  }
}

// 格式化语速为 API 需要的格式 e.g. 1.0 -> "+0%", 1.25 -> "+25%"
const getFormattedRate = () => {
  const r = ttsSpeed.value
  const percent = Math.round((r - 1) * 100)
  return percent >= 0 ? `+${percent}%` : `${percent}%`
}

// 播放特定段落的入口
const playParagraph = async (index, resetPhase = true) => {
  if (index < 0 || index >= paragraphs.value.length) return
  
  currentPlayingIndex.value = index
  
  // 初始化阅读阶段
  if (resetPhase) {
    // 如果模式是 'cn' (只读中文)，则初始阶段就是 'cn'
    // 其他模式 (en, dual) 初始阶段都是 'en'
    readingPhase.value = (viewMode.value === 'cn') ? 'cn' : 'en'
  }

  // 滚动到可见区域
  const el = document.getElementById(`para-${index}`)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })

  await loadAndPlayAudio()
}

// 实际请求音频并播放的核心函数
const loadAndPlayAudio = async () => {
  const p = paragraphs.value[currentPlayingIndex.value]
  if (!p) return

  // 确定要读的文本
  let textToRead = ''
  let voice = ''
  
  if (readingPhase.value === 'en') {
    textToRead = p.enText
    voice = 'en-US-AriaNeural' // 英文女声 (示例)
  } else {
    textToRead = p.cnText || '翻译中，请稍后'
    voice = 'zh-CN-XiaoxiaoNeural' // 中文女声 (示例)
  }

  if (!textToRead) return

  isBuffering.value = true
  try {
    const url = await getAudioUrl(textToRead, voice, getFormattedRate())
    if (!url) return 
    
    audio.src = url
    audio.play().catch(e => {
      console.error("Auto play failed", e)
      isPlaying.value = false
    })
  } catch (error) {
    message.error("TTS 请求失败")
    isBuffering.value = false
  }
}

</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.slide-up-enter-active, .slide-up-leave-active { transition: transform 0.4s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.3s ease; }
.slide-up-enter-from, .slide-up-leave-to { transform: translateY(100%); opacity: 0; }
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 2px; }
</style>