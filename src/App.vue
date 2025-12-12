<template>
  <n-config-provider :theme-overrides="themeOverrides">
    <div class="min-h-screen bg-[#f8fafc] text-slate-700 flex flex-col font-sans selection:bg-indigo-100 selection:text-indigo-800"> 
      <header class="sticky top-0 z-50 bg-white/90 backdrop-blur-lg border-b border-slate-200/60 transition-all duration-300">
        <div class="max-w-screen-2xl mx-auto px-3 sm:px-6 h-16 flex items-center justify-between">
            <div class="flex items-center gap-3 cursor-pointer select-none group opacity-90 hover:opacity-100 transition-opacity" @click="resetReader">
                <div class="w-9 h-9 bg-indigo-600 rounded-lg flex items-center justify-center shadow-lg shadow-indigo-500/30 shrink-0">
                  <n-icon size="20" color="#fff"><BookOutline /></n-icon>
                </div>
                <div class="hidden sm:flex flex-col">
                  <span class="text-lg font-bold tracking-tight text-slate-800 leading-none font-serif">DeepReader</span>
                </div>
            </div>
            <!-- Controls -->
            <div class="flex items-center gap-2 sm:gap-4">
                <div class="flex items-center p-1 bg-slate-100/80 rounded-lg border border-slate-200/50">
                  <n-radio-group v-model:value="viewMode" size="small" @update:value="handleViewModeChange">
                      <n-radio-button value="en" class="!px-2 sm:!px-3">EN</n-radio-button>
                      <n-radio-button value="dual" class="!px-2 sm:!px-3">Dual</n-radio-button>
                      <n-radio-button value="cn" class="!px-2 sm:!px-3">CN</n-radio-button>
                  </n-radio-group>
                </div>
                <n-divider vertical class="!h-5 !bg-slate-300 hidden sm:block" />
                <div class="flex items-center gap-1 sm:gap-2">
                    <n-tooltip trigger="hover" :show-arrow="false">
                        <template #trigger>
                        <n-button circle quaternary :type="segmentationEnabled ? 'primary' : 'default'" @click="toggleSegmentation">
                            <template #icon><n-icon size="20"><GitNetworkOutline /></n-icon></template>
                        </n-button>
                        </template>
                        {{ segmentationEnabled ? '关闭意群辅助' : '开启意群辅助' }}
                    </n-tooltip>
                    <n-tooltip trigger="hover" :show-arrow="false">
                        <template #trigger>
                        <n-button circle quaternary :type="vocabHighlightEnabled ? 'warning' : 'default'" @click="toggleVocab">
                            <template #icon><n-icon size="20"><SearchOutline /></n-icon></template>
                        </n-button>
                        </template>
                        {{ vocabHighlightEnabled ? '关闭生词高亮' : '开启生词高亮' }}
                    </n-tooltip>
                    <n-popselect v-model:value="currentTranslator" :options="translatorOptions" trigger="click" @update:value="handleTranslatorChange">
                        <n-button circle quaternary type="default">
                            <template #icon><n-icon size="20"><LanguageOutline /></n-icon></template>
                        </n-button>
                    </n-popselect>
                    <n-button circle quaternary type="default" @click="vocabInputRef.click()">
                        <template #icon><n-icon size="20"><LibraryOutline /></n-icon></template>
                    </n-button>
                </div>
            </div>
        </div>
      </header>
      <main class="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-8 py-8 pb-48 relative">
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
              <p class="text-base text-slate-400 mb-8 font-light">点击上传 TXT, EPUB, MOBI, PDF</p>
            </div>
          </div>
          <div v-else class="space-y-2">
            <div class="sticky top-16 z-20 flex justify-between items-center px-2 py-1.5 bg-[#f8fafc]/95 backdrop-blur border-b border-slate-100 mb-6 text-xs text-slate-400 font-mono">
              <span class="pl-2">{{ paragraphs.length }} Paragraphs</span>
              <div class="flex gap-4 pr-2">
                <span v-if="isBatchTranslating" class="text-amber-600 flex items-center gap-1">
                    <n-icon class="animate-spin"><ReloadOutline /></n-icon> Translating...
                </span>
                <span v-if="isPlaying || isBuffering" class="text-indigo-500 font-medium flex items-center gap-1" :class="{'animate-pulse': isBuffering}">
                    <n-icon><PulseOutline /></n-icon> {{ isBuffering ? 'Loading...' : 'Reading...' }}
                </span>
              </div>
            </div>
            <!-- Paragraphs -->
            <div 
              v-for="(para, index) in paragraphs" 
              :key="para.id"
              :id="`para-${index}`"
              :data-index="index"
              class="para-observer-item relative rounded-xl transition-all duration-300 border-l-4 scroll-m-32"
              :class="getParagraphClass(index)"
              @click="handleParagraphClick($event, index)"
            >
              <span class="absolute top-2 left-1 sm:left-2 text-[9px] font-mono text-slate-300 select-none opacity-0 group-hover:opacity-100 transition-opacity">#{{ index + 1 }}</span>
              <div class="absolute top-2 right-2 flex gap-2 opacity-50">
                 <n-icon v-if="para.processingSegment" size="14" class="animate-spin text-indigo-400"><GitNetworkOutline /></n-icon>
                 <n-icon v-if="para.translating" size="14" class="animate-spin text-amber-400"><LanguageOutline /></n-icon>
              </div>
              <!-- English Content -->
              <div v-if="viewMode !== 'cn'" class="relative px-2 sm:px-6 py-3 sm:py-4">
                <div class="en-reading-text text-xl tracking-wide leading-[1.9] transition-colors duration-300"
                  :class="[
                    (currentPlayingIndex === index && readingPhase === 'en') ? 'text-indigo-900 font-medium' : 'text-slate-800'
                  ]">
                  <template v-if="segmentationEnabled && para.chunks && para.chunks.length > 0">
                    <template v-for="(chunk, cIndex) in para.chunks" :key="cIndex">
                      <span 
                        class="phrase-chunk"
                        v-html="getChunkHtml(para, cIndex, chunk)"
                      ></span><span 
                        v-if="cIndex < para.chunks.length - 1" 
                        class="phrase-sep"
                        aria-hidden="true"
                      >·</span>
                    </template>
                  </template>
                  <template v-else>
                     <span v-html="getRawHtml(para)"></span>
                  </template>
                </div>
              </div>
              <!-- Chinese Content-->
              <div v-if="viewMode !== 'en'" class="px-2 sm:px-6 pb-4 pt-1">
                <div v-if="viewMode === 'dual'" class="mb-3 border-t border-dashed border-slate-100 w-full"></div>
                <div v-if="!para.cnText && para.translating" class="space-y-2 animate-pulse mt-2">
                   <div class="h-4 bg-slate-100 rounded w-3/4"></div>
                   <div class="h-4 bg-slate-100 rounded w-1/2"></div>
                </div>
                <p v-else class="text-base leading-8 font-sans text-justify transition-colors duration-300"
                   :class="(currentPlayingIndex === index && readingPhase === 'cn') ? 'text-indigo-700 font-medium' : 'text-slate-500 hover:text-slate-700'">
                  {{ para.cnText }}
                </p>
              </div>
            </div> 
            <div class="h-32 flex items-center justify-center text-slate-300 text-sm font-serif italic">- End of Text -</div>
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
                <span class="text-xs text-slate-400 mt-1 truncate">{{ col.preview }}</span>
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
  getIndexed, setIndexed, matchVocabulary, translateParagraphs, translatorOptions,
  enVoices, cnVoices, formatVoiceLabel, getAudioUrl,speedOptions, formatRate, generateHighlightHtml
} from './assets/common'
const themeOverrides = {
  common: { primaryColor: '#4f46e5', primaryColorHover: '#4338ca', borderRadius: '8px' }
}
const { message } = createDiscreteApi(['message'], { configProviderProps: { themeOverrides } })
const fileInputRef = ref(null)
const vocabInputRef = ref(null)
const paragraphs = ref([]) 
const viewMode = ref('en')
const segmentationEnabled = ref(false)
const vocabHighlightEnabled = ref(false)
const currentTranslator = ref('google')
const translationQueue = new Set() 
let translationTimer = null
const isBatchTranslating = ref(false)
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
const enVoiceOptions = computed(() => enVoices.map(v => ({ label: formatVoiceLabel(v), value: v.ShortName })))
const cnVoiceOptions = computed(() => cnVoices.map(v => ({ label: formatVoiceLabel(v), value: v.ShortName })))
const currentTextPreview = computed(() => {
  const p = paragraphs.value[currentPlayingIndex.value]
  return !p ? 'Ready to start' : (readingPhase.value === 'cn' && p.cnText) ? p.cnText : p.enText
})
const playProgress = computed(() => totalTime.value > 0 ? (currentTime.value / totalTime.value) * 100 : 0)
const handleParagraphClick = (index) => {
  if (window.getSelection()?.toString().length > 0) return
  playParagraph(index)
}
const playParagraph = async (index, resetPhase = true) => {
  if (index < 0 || index >= paragraphs.value.length) return
  currentPlayingIndex.value = index
  if (resetPhase) readingPhase.value = viewMode.value === 'cn' ? 'cn' : 'en'
  document.getElementById(`para-${index}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  await loadAndPlayAudio()
}
const handleTranslatorChange = () => {
  clearTimeout(translationTimer)
  translationQueue.clear()
  isBatchTranslating.value = false
  paragraphs.value.forEach(p => { p.cnText = ''; p.translating = false })
  setTimeout(initObserver, 600)
}
onMounted(async () => {
  audio.addEventListener('timeupdate', () => { currentTime.value = audio.currentTime })
  audio.addEventListener('loadedmetadata', () => { totalTime.value = audio.duration; isBuffering.value = false })
  audio.addEventListener('waiting', () => { isBuffering.value = true })
  audio.addEventListener('playing', () => { isBuffering.value = false; isPlaying.value = true })
  audio.addEventListener('pause', () => { isPlaying.value = false })
  audio.addEventListener('ended', async () => {
    const p = paragraphs.value[currentPlayingIndex.value]
    if (viewMode.value === 'dual' && readingPhase.value === 'en' && p?.cnText) {
      readingPhase.value = 'cn'
      return loadAndPlayAudio()
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
      ? 'bg-white shadow-xl shadow-indigo-100/50 border-indigo-500/30 z-10' 
      : 'bg-white/60 hover:bg-white border-transparent hover:border-slate-200 hover:shadow-sm'
  ]
}
const resetReader = () => {
  if (paragraphs.value.length && confirm('Clear all？')) {
    pauseTTS(); audio.src = ''; paragraphs.value = []
    currentPlayingIndex.value = -1; translationQueue.clear(); observer?.disconnect()
  }
}
const handleFileChange = async (e) => {
  const file = e.target.files[0]
  if (!file) return
  try {
    const extracted = await uploadAndExtract(file)
    if (extracted?.lines?.length) {
      paragraphs.value = extracted.lines.map((line, index) => ({
        id: `p-${index}`,
        enText: line, cnText: '', chunks: null, enTextDisplay: null, chunksDisplay: null, 
        processingSegment: false, processingVocab: false, translating: false 
      }));
      message.success(`导入成功`);
      setTimeout(initObserver, 600)
    } else { message.error("未提取到有效文本"); }
  } catch (error) { message.error("解析失败"); console.error(error); } finally { e.target.value = '' }
}
const handleViewModeChange = () => { initObserver(); if (isPlaying.value) playParagraph(currentPlayingIndex.value) }
const processParagraph = async (index) => {
  const p = paragraphs.value[index]
  if (!p) return
  const needsChinese = viewMode.value !== 'en'
  const needsEnglish = viewMode.value !== 'cn'

  if (needsEnglish) {
    if (segmentationEnabled.value && !p.chunks && !p.processingSegment) {
      p.processingSegment = true
      try { 
        const res = await segmentSentence(p.enText)
        p.chunks = res?.segments?.length > 0 ? res.segments : null
      } catch { p.chunks = null } 
      finally { p.processingSegment = false; if (vocabHighlightEnabled.value) matchAndHighlight(index) }
    }
    if (vocabHighlightEnabled.value) matchAndHighlight(index)
  }
  if (needsChinese && !p.cnText && !p.translating) queueTranslation(index)
}
const queueTranslation = (index) => {
  const p = paragraphs.value[index]
  if (translationQueue.has(index) || p.cnText || p.translating) return
  translationQueue.add(index)
  p.translating = true 
  clearTimeout(translationTimer)
  translationTimer = setTimeout(flushTranslationQueue, 600)
}
const flushTranslationQueue = async () => {
  if (!translationQueue.size) return
  const indices = [...translationQueue].sort((a, b) => a - b).slice(0, 10)
  indices.forEach(i => translationQueue.delete(i))
  if (translationQueue.size) translationTimer = setTimeout(flushTranslationQueue, 600)
  isBatchTranslating.value = true
  try {
    const translated = await translateParagraphs(indices.map(i => paragraphs.value[i].enText), currentTranslator.value, 'auto', 'zh')
    indices.forEach((idx, i) => { 
      if (paragraphs.value[idx]) { paragraphs.value[idx].cnText = translated[i]; paragraphs.value[idx].translating = false } 
    })
  } catch { 
    message.warning("部分翻译失败，请滚动重试")
    indices.forEach(idx => { if (paragraphs.value[idx]) paragraphs.value[idx].translating = false }) 
  } finally { isBatchTranslating.value = false }
}
const handleVocabFileParse = async (e) => {
  const file = e.target.files[0]
  if (!file) return
  e.target.value = ''
  try {
    const data = await readExcelFile(file)
    if (!data?.length) throw new Error("文件为空")
    excelSheetData.value = data
    excelColumns.value = (data[0] || []).map((header, idx) => ({ 
      header, preview: `${data[1]?.[idx] || '-'}, ${data[2]?.[idx] || '-'}` 
    }))
    showColumnSelector.value = true
  } catch { message.error("Excel 解析失败") }
}
const confirmColumnSelection = async (colIndex) => {
  showColumnSelector.value = false
  try {
    const dataRows = excelSheetData.value.slice(1)
    const words = [...(new Set(extractColumnFromData(dataRows, colIndex)))];
    if (!words.length) { message.warning("该列没有有效数据"); return }
    await setIndexed('vocabs', words)
    paragraphs.value.forEach(p => { p.enTextDisplay = null; p.chunksDisplay = null })
    message.success(`已导入 ${words.length} 个词汇`)
    if (vocabHighlightEnabled.value) initObserver()
  } catch (e) { console.error(e); message.error("保存词库失败") }
}
const getRawHtml = (para) => (vocabHighlightEnabled.value && para.enTextDisplay) ? para.enTextDisplay : para.enText
const getChunkHtml = (para, index, originalChunk) => (vocabHighlightEnabled.value && para.chunksDisplay?.[index]) ? para.chunksDisplay[index] : originalChunk
const matchAndHighlight = async (index) => {
  const p = paragraphs.value[index]
  const userVocabList = await getIndexed('vocabs', []);
  if (!userVocabList.length || p.processingVocab) return
  const isChunkMode = segmentationEnabled.value && p.chunks?.length > 0
  if (isChunkMode ? p.chunksDisplay : p.enTextDisplay) return
  p.processingVocab = true
  const targets = isChunkMode ? p.chunks : [p.enText]
  try {
    const results = await matchVocabulary(userVocabList, targets)
    if (results?.length === targets.length) {
      if (isChunkMode) p.chunksDisplay = targets.map((t, i) => generateHighlightHtml(t, results[i]))
      else p.enTextDisplay = generateHighlightHtml(targets[0], results[0])
    }
  } finally { p.processingVocab = false }
}
let observer = null
const initObserver = () => {
  observer?.disconnect()
  observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => { if (entry.isIntersecting) { const idx = Number(entry.target.dataset.index); if (!isNaN(idx)) processParagraph(idx) } })
  }, { rootMargin: '400px 0px 400px 0px', threshold: 0.01 })
  document.querySelectorAll('.para-observer-item').forEach(el => observer.observe(el))
}
const toggleSegmentation = () => { segmentationEnabled.value = !segmentationEnabled.value; initObserver() }
const toggleVocab = async () => { vocabHighlightEnabled.value = !vocabHighlightEnabled.value; if (vocabHighlightEnabled.value) { const userVocabList = await getIndexed('vocabs', []); if (userVocabList.length === 0) message.warning("请先导入词汇库"); initObserver() } }
onBeforeUnmount(() => {
  observer?.disconnect(); clearTimeout(translationTimer)
  audio.pause(); audio.src = ''; abortController?.abort()
})
const togglePlay = () => {
  if (isPlaying.value) { audio.pause(); isPlaying.value = false } 
  else { if (currentPlayingIndex.value === -1 && paragraphs.value.length > 0) playParagraph(0); else audio.play().catch(e => console.error("Resume failed", e)) }
}
const pauseTTS = () => { audio.pause(); isPlaying.value = false }
const seekAudio = (e) => { 
  if (!totalTime.value) return
  const rect = e.target.getBoundingClientRect()
  audio.currentTime = currentTime.value = ((e.clientX - rect.left) / rect.width) * totalTime.value
}
const onAudioConfigChange = () => { if (currentPlayingIndex.value !== -1) playParagraph(currentPlayingIndex.value, false) }
const loadAndPlayAudio = async () => {
  const p = paragraphs.value[currentPlayingIndex.value]
  if (!p) return
  let textToRead = '', voice = ''
  if (readingPhase.value === 'en') { textToRead = p.enText; voice = currentEnVoice.value } 
  else { textToRead = p.cnText; voice = currentCnVoice.value }
  if (!textToRead) return
  isBuffering.value = true
  try {
    abortController?.abort()
    abortController = new AbortController()
    const url = await getAudioUrl(abortController, textToRead, voice, formatRate(ttsSpeed.value))
    if (url) { audio.src = url; audio.play().catch(e => { console.error("Auto play failed", e); isPlaying.value = false }) }
  } catch { message.error("TTS 请求失败"); isBuffering.value = false }
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
/* 英文阅读字体 - 使用具有文学感的衬线字体 */
.en-reading-text {
  font-family: 'Georgia', 'Cambria', 'Palatino Linotype', 'Palatino', 'Book Antiqua', 'Times New Roman', serif;
  font-feature-settings: 'kern' 1, 'liga' 1;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}
/* 意群分块 - 保持正常文本流，允许自然换行 */
.phrase-chunk {
  transition: background-color 0.2s ease, color 0.2s ease;
  border-radius: 3px;
  padding: 1px 3px;
  margin: -1px -3px;
}
.phrase-chunk:hover {
  background-color: rgba(99, 102, 241, 0.08);
  color: #312e81;
}
/* 意群分隔符 - 轻量视觉提示，不影响文本流 */
.phrase-sep {
  color: #cbd5e1;
  margin: 0 0.4em;
  font-weight: 300;
  font-size: 0.7em;
  vertical-align: middle;
  user-select: none;
  opacity: 0.7;
}
</style>