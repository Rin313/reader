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

// 暴露给父组件的方法，用于触发文件选择
const openFilePicker = () => {
  vocabInputRef.value?.click()
}

defineExpose({
  openFilePicker
})

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
    showColumnSelector.value = true
  } catch { 
    message.error("Excel 解析失败") 
  }
}

const confirmColumnSelection = async (colIndex) => {
  showColumnSelector.value = false
  try {
    const dataRows = excelSheetData.value.slice(1)
    const words = [...(new Set(extractColumnFromData(dataRows, colIndex)))]
    if (!words.length) { 
      message.warning("该列没有有效数据")
      return 
    }
    await setItem('vocabs', words)
    message.success(`已导入 ${words.length} 个词汇`)
    emit('import-success', words)
  } catch (e) { 
    console.error(e)
    message.error("保存词库失败") 
  }
}
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 2px; }
</style>