<template>
  <div>
    <input 
      type="file" 
      ref="vocabInputRef" 
      class="hidden" 
      @change="handleVocabFileParse" 
      accept=".csv,.xlsx" 
    />
    <n-modal 
      v-model:show="showColumnSelector" 
      preset="card" 
      title="导入配置" 
      class="max-w-md w-[90vw]"
    >
      <div class="max-h-[60vh] overflow-y-auto pr-1 custom-scrollbar">
        <!-- 步骤指示器 -->
        <div class="flex items-center gap-2 mb-4">
          <div class="flex items-center">
            <div :class="['w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold', 
              selectionStep === 1 ? 'bg-indigo-500 text-white' : 'bg-indigo-100 text-indigo-600']">
              {{ selectionStep > 1 ? '✓' : '1' }}
            </div>
            <span class="ml-1.5 text-sm" :class="selectionStep === 1 ? 'text-indigo-600 font-medium' : 'text-slate-400'">
              单词列
            </span>
          </div>
          <div class="w-8 h-px bg-slate-300"></div>
          <div class="flex items-center">
            <div :class="['w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold', 
              selectionStep === 2 ? 'bg-indigo-500 text-white' : 'bg-slate-200 text-slate-400']">2</div>
            <span class="ml-1.5 text-sm" :class="selectionStep === 2 ? 'text-indigo-600 font-medium' : 'text-slate-400'">
              释义列
            </span>
          </div>
        </div>

        <!-- 已选择的单词列提示 -->
        <div v-if="selectionStep === 2" class="mb-3 p-2.5 bg-indigo-50 rounded-lg flex items-center justify-between">
          <span class="text-sm text-indigo-700">
            <span class="text-indigo-400">单词列：</span>
            {{ excelColumns[selectedWordColIndex]?.header || `第 ${selectedWordColIndex + 1} 列` }}
          </span>
          <button 
            @click="goBack" 
            class="text-xs text-indigo-500 hover:text-indigo-700 underline"
          >
            重新选择
          </button>
        </div>

        <p class="text-slate-500 text-sm mb-3">
          {{ selectionStep === 1 ? '请选择包含英文单词的一列：' : '请选择包含中文释义的一列：' }}
        </p>

        <div class="grid grid-cols-1 gap-2">
          <div 
            v-for="(col, idx) in excelColumns" 
            :key="idx"
            class="p-3 border rounded-lg transition-all flex flex-col"
            :class="getColumnClass(idx)"
            @click="handleColumnClick(idx)"
          >
            <div class="flex items-center justify-between">
              <span class="font-bold text-slate-700 text-sm">
                {{ col.header || `第 ${idx + 1} 列` }}
              </span>
              <span 
                v-if="selectedWordColIndex === idx && selectionStep === 2" 
                class="text-xs text-indigo-500 bg-indigo-100 px-2 py-0.5 rounded"
              >
                已选为单词列
              </span>
            </div>
            <span class="text-xs text-slate-400 mt-1 truncate">{{ col.preview }}</span>
          </div>
        </div>
      </div>
    </n-modal>
  </div>
</template>

<script setup>
import { ref, shallowRef } from 'vue'
import { NModal, createDiscreteApi } from 'naive-ui'
import { readExcelFile, extractColumnFromData, setItem } from './assets/common'

const themeOverrides = {
  common: { primaryColor: '#4f46e5', primaryColorHover: '#4338ca', borderRadius: '8px' }
}
const { message } = createDiscreteApi(['message'], { configProviderProps: { themeOverrides } })

const emit = defineEmits(['import-success'])

const vocabInputRef = ref(null)
const showColumnSelector = ref(false)
const excelSheetData = shallowRef([])
const excelColumns = ref([])
const selectionStep = ref(1) // 1: 选择单词列, 2: 选择释义列
const selectedWordColIndex = ref(-1)

// 暴露给父组件的方法，用于触发文件选择
const openFilePicker = () => {
  vocabInputRef.value?.click()
}

defineExpose({
  openFilePicker
})

// 获取列的样式类
const getColumnClass = (idx) => {
  if (selectionStep.value === 2 && selectedWordColIndex.value === idx) {
    return 'border-indigo-200 bg-indigo-50/50 opacity-60 cursor-not-allowed'
  }
  return 'border-slate-200 hover:border-indigo-500 hover:bg-indigo-50 cursor-pointer'
}

// 返回上一步
const goBack = () => {
  selectionStep.value = 1
  selectedWordColIndex.value = -1
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
      header, 
      preview: `${data[1]?.[idx] || '-'}, ${data[2]?.[idx] || '-'}` 
    }))
    // 重置状态
    selectionStep.value = 1
    selectedWordColIndex.value = -1
    showColumnSelector.value = true
  } catch { 
    message.error("Excel 解析失败") 
  }
}

const handleColumnClick = (colIndex) => {
  if (selectionStep.value === 1) {
    // 第一步：选择单词列
    selectedWordColIndex.value = colIndex
    selectionStep.value = 2
  } else {
    // 第二步：选择释义列（不能选择已选的单词列）
    if (colIndex === selectedWordColIndex.value) {
      message.warning('释义列不能与单词列相同')
      return
    }
    confirmSelection(colIndex)
  }
}

const confirmSelection = async (meaningColIndex) => {
  showColumnSelector.value = false
  try {
    const dataRows = excelSheetData.value.slice(1)
    const words = extractColumnFromData(dataRows, selectedWordColIndex.value)
    const meanings = extractColumnFromData(dataRows, meaningColIndex)

    // 整合数据，以单词为键去重
    const vocabMap = new Map()
    words.forEach((word, idx) => {
      const trimmedWord = String(word || '').trim()
      if (trimmedWord && !vocabMap.has(trimmedWord)) {
        vocabMap.set(trimmedWord, String(meanings[idx] || '').trim())
      }
    })

    // 转换为数组格式 [{ word, meaning }, ...]
    const vocabs = Array.from(vocabMap, ([word, meaning]) => ({ word, meaning }))

    if (!vocabs.length) {
      message.warning('没有有效数据')
      return
    }

    await setItem('vocabs', vocabs)
    message.success(`已导入 ${vocabs.length} 个词汇`)
    emit('import-success', vocabs)
  } catch (e) {
    console.error(e)
    message.error('保存词库失败')
  }
}
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 2px; }
</style>