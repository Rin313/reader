<template>
  <n-config-provider :theme-overrides="themeOverrides">
    <div class="min-h-screen bg-[#f8fafc] text-slate-700 flex flex-col font-sans selection:bg-indigo-100 selection:text-indigo-800"> 
      <!-- Header -->
      <header class="sticky top-0 z-50 bg-white/80 backdrop-blur-lg border-b border-slate-200/50 transition-all duration-300">
        <div class="max-w-screen-xl mx-auto px-6 h-16 flex items-center justify-between">
            <div class="flex items-center gap-3 cursor-pointer select-none group opacity-90 hover:opacity-100 transition-opacity" @click="resetReader">
                <div class="w-9 h-9 bg-indigo-600 rounded-lg flex items-center justify-center shadow-lg shadow-indigo-500/30">
                  <n-icon size="20" color="#fff"><BookOutline /></n-icon>
                </div>
                <div class="flex flex-col">
                  <span class="text-lg font-bold tracking-tight text-slate-800 leading-none font-serif">DeepReader</span>
                </div>
            </div>
            <!-- Controls -->
            <div class="flex items-center gap-4">
                <div class="hidden sm:flex items-center p-1 bg-slate-100/80 rounded-lg border border-slate-200/50">
                  <n-radio-group v-model:value="viewMode" size="small" @update:value="handleViewModeChange">
                      <n-radio-button value="en" class="!px-4 !font-medium">English</n-radio-button>
                      <n-radio-button value="dual" class="!px-4 !font-medium">对照</n-radio-button>
                      <n-radio-button value="cn" class="!px-4 !font-medium">中文</n-radio-button>
                  </n-radio-group>
                </div>
                <n-divider vertical class="!h-5 !bg-slate-300 hidden sm:block" />
                <div class="flex items-center gap-2">
                    <n-tooltip trigger="hover" :show-arrow="false">
                        <template #trigger>
                        <n-button circle quaternary :type="segmentationEnabled ? 'primary' : 'default'" @click="toggleSegmentation" class="!w-9 !h-9">
                            <template #icon><n-icon size="20"><GitNetworkOutline /></n-icon></template>
                        </n-button>
                        </template>
                        {{ segmentationEnabled ? '关闭意群辅助' : '开启意群辅助' }}
                    </n-tooltip>
                    <n-tooltip trigger="hover" :show-arrow="false">
                        <template #trigger>
                        <n-button circle quaternary :type="vocabHighlightEnabled ? 'warning' : 'default'" @click="toggleVocab" class="!w-9 !h-9">
                            <template #icon><n-icon size="20"><SearchOutline /></n-icon></template>
                        </n-button>
                        </template>
                        {{ vocabHighlightEnabled ? '关闭生词高亮' : '开启生词高亮' }}
                    </n-tooltip>
                    <n-popselect v-model:value="currentTranslator" :options="translatorOptions" trigger="click" @update:value="handleTranslatorChange">
                        <n-button circle quaternary type="default" class="!w-9 !h-9">
                            <template #icon><n-icon size="20"><LanguageOutline /></n-icon></template>
                        </n-button>
                    </n-popselect>
                    <n-tooltip trigger="hover" :show-arrow="false">
                        <template #trigger>
                        <n-button circle quaternary type="default" @click="vocabInputRef.click()" class="!w-9 !h-9">
                            <template #icon><n-icon size="18"><LibraryOutline /></n-icon></template>
                        </n-button>
                        </template>
                        导入词汇库
                    </n-tooltip>
                </div>
            </div>
        </div>
      </header>
      <main class="flex-1 max-w-4xl mx-auto w-full px-6 py-12 pb-48 relative">
        <transition name="fade" mode="out-in">
          <div v-if="paragraphs.length === 0" class="flex flex-col items-center justify-center py-20 select-none min-h-[60vh]">
            <div 
              class="w-full max-w-2xl border border-dashed border-slate-300 hover:border-indigo-400 hover:bg-white bg-slate-50/50 rounded-3xl p-16 flex flex-col items-center text-center transition-all duration-500 cursor-pointer group"
              @click="fileInputRef.click()"
            >
              <div class="w-24 h-24 bg-white text-indigo-500 group-hover:text-indigo-600 group-hover:scale-105 group-hover:shadow-xl transition-all duration-500 rounded-2xl flex items-center justify-center mb-8 shadow-sm border border-slate-100">
                <n-icon size="48" class="opacity-80 group-hover:opacity-100"><CloudUploadOutline /></n-icon>
              </div>
              <h2 class="text-2xl font-serif font-bold text-slate-700 mb-3 group-hover:text-indigo-700 transition-colors">开启沉浸式阅读</h2>
              <p class="text-base text-slate-400 mb-8 font-light">拖入或点击上传 TXT, EPUB, MOBI, PDF</p>
            </div>
          </div>
          <div v-else class="space-y-6">
            <!-- Info Bar -->
            <div class="sticky top-20 z-20 flex justify-between items-center px-4 py-2 bg-[#f1f5f9]/90 backdrop-blur-sm text-xs text-slate-400 rounded-lg">
              <span>{{ paragraphs.length }} Paragraphs</span>
              <span v-if="isBatchTranslating" class="text-amber-600 flex items-center gap-1">
                <n-icon class="animate-spin"><ReloadOutline /></n-icon> Translating...
              </span>
              <span v-if="isPlaying || isBuffering" class="text-indigo-500 font-medium flex items-center gap-1" :class="{'animate-pulse': isBuffering}">
                <n-icon><PulseOutline /></n-icon> {{ isBuffering ? 'Loading...' : 'Reading...' }}
              </span>
            </div>
            <!-- Paragraph List -->
            <div 
              v-for="(para, index) in paragraphs" 
              :key="para.id"
              :id="`para-${index}`"
              :data-index="index"
              class="para-observer-item relative p-6 sm:p-8 rounded-2xl transition-all duration-300 border scroll-m-32 hover:border-indigo-200"
              :class="getParagraphClass(index)"
              @click="handleParagraphClick($event, index)"
            >
              <div v-if="currentPlayingIndex === index" class="absolute left-0 top-8 bottom-8 w-1 bg-indigo-500 rounded-r-full"></div>
              <span class="absolute top-4 left-4 text-[10px] font-mono text-slate-300 select-none">#{{ index + 1 }}</span>

              <div class="absolute top-4 right-4 flex gap-2">
                 <n-icon v-if="para.processingSegment" size="16" class="animate-spin text-indigo-300"><GitNetworkOutline /></n-icon>
                 <n-icon v-if="para.translating" size="16" class="animate-spin text-amber-400"><LanguageOutline /></n-icon>
              </div>
              <!-- English Content -->
              <div v-if="viewMode !== 'cn'" class="relative">
                <div class="font-serif text-xl tracking-wide leading-[1.95] transition-colors duration-300"
                  :class="[
                    (currentPlayingIndex === index && readingPhase === 'en') ? 'text-indigo-900 font-medium' : 'text-slate-800'
                  ]">
                  <template v-if="segmentationEnabled && para.chunks && para.chunks.length > 0">
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
                <div v-if="!para.cnText && para.translating" class="space-y-2 animate-pulse">
                   <div class="h-4 bg-slate-200 rounded w-3/4"></div>
                   <div class="h-4 bg-slate-200 rounded w-1/2"></div>
                </div>
                <p v-else class="text-base leading-8 font-sans text-justify transition-colors duration-300"
                   :class="(currentPlayingIndex === index && readingPhase === 'cn') ? 'text-indigo-700 font-medium' : 'text-slate-500 hover:text-slate-700'">
                  {{ para.cnText }}
                </p>
              </div>
            </div>
            
            <div class="h-32 flex items-center justify-center text-slate-300 text-sm font-serif italic">
               - End of Text -
            </div>
          </div>
        </transition>
      </main>
      <!-- 悬浮播放器 -->
      <transition name="slide-up">
        <div v-if="paragraphs.length > 0" class="fixed bottom-6 left-0 right-0 z-40 px-4 flex justify-center pointer-events-none">
           <div class="bg-slate-900/95 backdrop-blur-xl text-white p-3 pl-4 rounded-2xl shadow-2xl shadow-slate-900/30 w-full max-w-xl pointer-events-auto border border-slate-700/50 flex flex-col gap-2 ring-1 ring-white/10">
            <div class="flex items-center gap-3">
              <!-- Play/Pause Button -->
              <button 
                class="w-12 h-12 rounded-full bg-indigo-600 hover:bg-indigo-500 active:scale-95 flex items-center justify-center transition-all shadow-lg shadow-indigo-500/30 group relative shrink-0"
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

              <!-- Text Info -->
              <div class="flex-1 min-w-0 flex flex-col justify-center mr-2">
                <div class="text-[10px] text-indigo-300 font-bold tracking-wider uppercase mb-0.5 flex items-center gap-2">
                  <span v-if="readingPhase" class="bg-indigo-500/20 px-1 rounded text-[9px] border border-indigo-500/30">{{ readingPhase === 'en' ? 'ENGLISH' : 'CHINESE' }}</span>
                </div>
                <div class="text-sm text-slate-100 truncate font-serif opacity-90">
                  {{ currentTextPreview }}
                </div>
              </div>

              <!-- Voice & Speed Controls Group -->
                <div class="flex items-center gap-1.5 bg-slate-800/50 rounded-lg p-1 border border-slate-700/50">
                <n-popselect v-model:value="currentEnVoice" :options="enVoiceOptions" trigger="click" placement="top" virtual-scroll @update:value="onAudioConfigChange">
                    <button class="w-7 h-7 flex items-center justify-center rounded hover:bg-slate-700 text-slate-400 hover:text-indigo-300 transition-colors">
                        <span class="text-[10px] font-bold">EN</span>
                    </button>  
                </n-popselect>
                <n-popselect v-model:value="currentCnVoice" :options="cnVoiceOptions" trigger="click" placement="top" virtual-scroll @update:value="onAudioConfigChange">
                    <button class="w-7 h-7 flex items-center justify-center rounded hover:bg-slate-700 text-slate-400 hover:text-indigo-300 transition-colors">
                    <span class="text-[10px] font-bold">CN</span>
                    </button>
                </n-popselect>
                <div class="w-[1px] h-4 bg-slate-700 mx-0.5"></div>
                <n-popselect v-model:value="ttsSpeed" :options="speedOptions" trigger="click" placement="top-end" @update:value="onAudioConfigChange">
                    <button class="px-1.5 py-1 rounded text-xs font-bold text-slate-300 hover:text-white hover:bg-slate-700 transition-colors min-w-[2.5rem]">
                    {{ ttsSpeed }}x
                    </button>
                </n-popselect>
                </div>
            </div>

            <!-- Progress Bar -->
            <div class="px-1 pb-1 pt-1 relative group">
               <n-progress type="line" :percentage="playProgress" :show-indicator="false" color="#818cf8" rail-color="#334155" height="3" class="cursor-pointer" />
              <div class="absolute top-0 left-0 w-full h-full cursor-pointer" @click="seekAudio"></div> 
              <div class="flex justify-between mt-1.5 text-[10px] text-slate-500 font-mono">
                <span>{{ formatTime(currentTime) }}</span>
              </div>
            </div>
          </div>
        </div>
      </transition>
      <n-modal v-model:show="showColumnSelector" preset="card" title="导入配置" class="max-w-md w-[90vw]">
          <div class="max-h-[60vh] overflow-y-auto pr-1 custom-scrollbar">
           <p class="text-slate-500 text-sm mb-4">请选择包含英文单词的一列：</p>
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
  getIndexed, setIndexed, matchVocabulary, translateParagraphs, translatorOptions,enVoices,cnVoices,formatTime,formatVoiceLabel,getAudioUrl
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
const viewMode = ref('en')

// 功能开关
const segmentationEnabled = ref(false)
const vocabHighlightEnabled = ref(false)
const userVocabList = shallowRef(new Set())
// 翻译相关状态
const currentTranslator = ref('google')
const translationQueue = new Set() 
let translationTimer = null
const isBatchTranslating = ref(false)
// TTS 状态
let abortController = null
const audio = new Audio()
const isPlaying = ref(false)
const isBuffering = ref(false)
const currentPlayingIndex = ref(-1)
const ttsSpeed = ref(1.0)
const currentTime = ref(0)
const totalTime = ref(0)
const readingPhase = ref('en')
const currentEnVoice = ref(enVoices[0]?.ShortName)
const currentCnVoice = ref(cnVoices[0]?.ShortName)
const showColumnSelector = ref(false)
const excelSheetData = shallowRef([])
const excelColumns = ref([])

// Computed properties
const enVoiceOptions = computed(() => enVoices.map(v => ({ label: formatVoiceLabel(v), value: v.ShortName })))
const cnVoiceOptions = computed(() => cnVoices.map(v => ({ label: formatVoiceLabel(v), value: v.ShortName })))
const currentTextPreview = computed(() => {
  const p = paragraphs.value[currentPlayingIndex.value]
  if (!p) return 'Ready to start'
  if (readingPhase.value === 'cn' && p.cnText) return p.cnText
  return p.enText
})
const playProgress = computed(() => totalTime.value > 0 ? (currentTime.value / totalTime.value) * 100 : 0)
const handleParagraphClick = (e, index) => {
  const selection = window.getSelection()
  if (selection && selection.toString().length > 0) return
  playParagraph(index)
}

const playParagraph = async (index, resetPhase = true) => {
  if (index < 0 || index >= paragraphs.value.length) return
  
  currentPlayingIndex.value = index
  
  if (resetPhase) {
    readingPhase.value = (viewMode.value === 'cn') ? 'cn' : 'en'
  }

  const el = document.getElementById(`para-${index}`)
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })

  await loadAndPlayAudio()
}

const handleTranslatorChange = () => {
  if (translationTimer) clearTimeout(translationTimer)
  translationQueue.clear()
  isBatchTranslating.value = false
  paragraphs.value.forEach(p => { p.cnText = ''; p.translating = false })
  setTimeout(() => { initObserver() }, 600)
}

onMounted(async () => {
  try {
    const data = await getIndexed('vocabs', [])
    if (Array.isArray(data)) userVocabList.value = new Set(data)
  } catch (e) { console.error('本地词库加载失败', e) }
  audio.addEventListener('timeupdate', () => { currentTime.value = audio.currentTime })
  audio.addEventListener('loadedmetadata', () => { totalTime.value = audio.duration; isBuffering.value = false })
  audio.addEventListener('waiting', () => { isBuffering.value = true })
  audio.addEventListener('playing', () => { isBuffering.value = false; isPlaying.value = true })
  audio.addEventListener('pause', () => { isPlaying.value = false })
  audio.addEventListener('ended', async () => {
    if (viewMode.value === 'dual' && readingPhase.value === 'en') {
      const p = paragraphs.value[currentPlayingIndex.value]
      if (p && p.cnText) {
        readingPhase.value = 'cn'
        await loadAndPlayAudio()
        return
      }
    }
    if (currentPlayingIndex.value < paragraphs.value.length - 1) {
      playParagraph(currentPlayingIndex.value + 1)
    } else {
      isPlaying.value = false; currentPlayingIndex.value = -1; currentTime.value = 0; totalTime.value = 0
    }
  })
})

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
    audio.src = ''
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
        enText: line, cnText: '', chunks: null, enTextDisplay: null, chunksDisplay: null, 
        processingSegment: false, processingVocab: false, translating: false 
      }));
      message.success(`导入成功`);
      setTimeout(() => { initObserver() }, 600)
    } else { message.error("未提取到有效文本"); }
  } catch (error) { message.error("解析失败"); console.error(error); } finally { e.target.value = '' }
}

const handleViewModeChange = () => { initObserver(); if (isPlaying.value) playParagraph(currentPlayingIndex.value) }

const processParagraph = async (index) => {
  const p = paragraphs.value[index]
  if (!p) return
  const needsChinese = viewMode.value === 'cn' || viewMode.value === 'dual'
  const needsEnglishEnhancement = viewMode.value === 'en' || viewMode.value === 'dual'
  if (needsEnglishEnhancement) {
    if (segmentationEnabled.value && !p.chunks && !p.processingSegment) {
      p.processingSegment = true
      try { 
        const res = await segmentSentence(p.enText); 
        if (res && res.segments && res.segments.length > 0) {
            p.chunks = res.segments
        } else {
            p.chunks = null 
        }
      } 
      catch { p.chunks = null } 
      finally { 
        p.processingSegment = false; 
        if (vocabHighlightEnabled.value) matchAndHighlight(index) 
      }
    }
    if (vocabHighlightEnabled.value) matchAndHighlight(index)
  }
  if (needsChinese && !p.cnText && !p.translating) queueTranslation(index)
}

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
    indices.forEach((idx, arrayIndex) => { if (paragraphs.value[idx]) { paragraphs.value[idx].cnText = translatedTexts[arrayIndex]; paragraphs.value[idx].translating = false } })
  } catch (error) { message.warning("部分翻译失败，请滚动重试"); indices.forEach(idx => { if (paragraphs.value[idx]) paragraphs.value[idx].translating = false }) } finally { isBatchTranslating.value = false }
}

const handleVocabFileParse = async (e) => {
  const file = e.target.files[0]
  if (!file) return
  e.target.value = ''
  try {
    const data = await readExcelFile(file)
    if (!data || data.length === 0) throw new Error("文件为空")
    excelSheetData.value = data
    excelColumns.value = (data[0] || []).map((header, idx) => ({ header: header, preview: `${data[1]?.[idx] || '-'}, ${data[2]?.[idx] || '-'}` }))
    showColumnSelector.value = true
  } catch (err) { message.error("Excel 解析失败") }
}
const confirmColumnSelection = async (colIndex) => {
  showColumnSelector.value = false
  try {
    const dataRows = excelSheetData.value.length > 1 ? excelSheetData.value.slice(1) : []
    if (dataRows.length === 0) { message.warning("表格除表头外没有数据"); return }
    const words = extractColumnFromData(dataRows, colIndex)
    if (!words.length) { message.warning("该列没有有效数据"); return }
    await setIndexed('vocabs', words)
    userVocabList.value = new Set(words)
    paragraphs.value.forEach(p => { p.enTextDisplay = null; p.chunksDisplay = null })
    message.success(`已导入 ${words.length} 个词汇`)
    if (vocabHighlightEnabled.value) initObserver()
  } catch (e) { console.error(e); message.error("保存词库失败") }
}

const generateHighlightHtml = (text, matches) => {
  if (!text) return ''
  if (!matches?.length) return text
  const sorted = [...matches].sort((a, b) => b.start - a.start)
  let result = text
  sorted.forEach(m => {
    const { start, length } = m
    if (start < 0 || start + length > result.length) return
    const word = result.slice(start, start + length)
    result = result.slice(0, start) + 
      `<span class="border-b-[1.5px] border-amber-400 text-amber-900/90 cursor-help hover:bg-amber-100/50 hover:text-amber-700 transition-colors">${word}</span>` + 
      result.slice(start + length)
  })
  return result
}

const getRawHtml = (para) => (vocabHighlightEnabled.value && para.enTextDisplay) ? para.enTextDisplay : para.enText
const getChunkHtml = (para, index, originalChunk) => (vocabHighlightEnabled.value && para.chunksDisplay?.[index]) ? para.chunksDisplay[index] : originalChunk

const matchAndHighlight = async (index) => {
  const p = paragraphs.value[index]
  if (!userVocabList.value.size) return
  const isChunkMode = segmentationEnabled.value && p.chunks && p.chunks.length > 0
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

let observer = null
const initObserver = () => {
  if (observer) observer.disconnect()
  observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => { if (entry.isIntersecting) { const idx = Number(entry.target.dataset.index); if (!isNaN(idx)) processParagraph(idx) } })
  }, { rootMargin: '400px 0px 400px 0px', threshold: 0.01 })
  const elements = document.querySelectorAll('.para-observer-item')
  if (elements.length > 0) elements.forEach(el => observer.observe(el))
}

const toggleSegmentation = () => { segmentationEnabled.value = !segmentationEnabled.value; initObserver() }
const toggleVocab = () => { vocabHighlightEnabled.value = !vocabHighlightEnabled.value; if (vocabHighlightEnabled.value) { if (userVocabList.value.size === 0) message.warning("请先导入词汇库"); initObserver() } }

onBeforeUnmount(() => {
  observer?.disconnect()
  if (translationTimer) clearTimeout(translationTimer)
  if (audio) { audio.pause(); audio.src = '' }
  if (abortController) abortController.abort()
})

const speedOptions = [0.75, 1.0, 1.25, 1.5].map(v => ({ label: `${v}x`, value: v }))
const togglePlay = () => {
  if (isPlaying.value) { audio.pause(); isPlaying.value = false } 
  else { if (currentPlayingIndex.value === -1 && paragraphs.value.length > 0) playParagraph(0); else audio.play().catch(e => console.error("Resume failed", e)) }
}
const pauseTTS = () => { audio.pause(); isPlaying.value = false }
const seekAudio = (e) => { 
  if (!totalTime.value) return
  const rect = e.target.getBoundingClientRect()
  const percent = (e.clientX - rect.left) / rect.width
  const newTime = percent * totalTime.value
  audio.currentTime = newTime
  currentTime.value = newTime
}
const onAudioConfigChange = () => { if (currentPlayingIndex.value !== -1) playParagraph(currentPlayingIndex.value, false) }
const getFormattedRate = () => { const r = ttsSpeed.value; const percent = Math.round((r - 1) * 100); return percent >= 0 ? `+${percent}%` : `${percent}%` }
const loadAndPlayAudio = async () => {
  const p = paragraphs.value[currentPlayingIndex.value]
  if (!p) return
  let textToRead = '', voice = ''
  if (readingPhase.value === 'en') { textToRead = p.enText; voice = currentEnVoice.value } 
  else { textToRead = p.cnText; voice = currentCnVoice.value }
  if (!textToRead) return
  isBuffering.value = true
  try {
    if (abortController) abortController.abort()
    abortController = new AbortController()
    const url = await getAudioUrl(abortController,textToRead, voice, getFormattedRate())
    if (!url) return 
    audio.src = url
    audio.play().catch(e => { console.error("Auto play failed", e); isPlaying.value = false })
  } catch (error) { message.error("TTS 请求失败"); isBuffering.value = false }
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