<script setup>
import { ref, watch } from 'vue'
import api from '../api'

const props = defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, default: '圖片' },
  accept: { type: String, default: 'image/jpeg,image/png,image/gif,image/webp' },
})

const emit = defineEmits(['update:modelValue'])

const uploading = ref(false)
const imgError = ref(false)
const inputRef = ref(null)

watch(() => props.modelValue, () => { imgError.value = false })

async function onFileSelect(e) {
  const file = e.target.files?.[0]
  if (!file) return

  uploading.value = true
  try {
    const form = new FormData()
    form.append('file', file)
    const res = await api.post('/upload', form)
    emit('update:modelValue', res.data.url)
    imgError.value = false
  } catch (err) {
    alert(err.response?.data?.detail || '上傳失敗')
  } finally {
    uploading.value = false
    if (inputRef.value) inputRef.value.value = ''
  }
}
</script>

<template>
  <div>
    <label class="block text-xs text-gray-500 mb-1">{{ label }}</label>
    <div class="flex gap-2">
      <input
        :value="modelValue"
        @input="$emit('update:modelValue', $event.target.value)"
        class="flex-1 min-w-0 border rounded-lg px-2 py-1.5 text-sm"
        placeholder="https://... 或選擇檔案上傳"
      />
      <label
        class="shrink-0 inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm cursor-pointer font-medium"
        :class="uploading ? 'bg-gray-200 text-gray-400' : 'bg-indigo-100 text-indigo-700 hover:bg-indigo-200'"
      >
        <svg v-if="uploading" class="animate-spin h-4 w-4" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <span v-else>上傳</span>
        <input
          ref="inputRef"
          type="file"
          :accept="accept"
          class="hidden"
          @change="onFileSelect"
          :disabled="uploading"
        />
      </label>
    </div>
    <div v-if="modelValue && !imgError" class="mt-2 relative">
      <img
        :src="modelValue"
        class="w-36 h-36 object-cover rounded border"
        @error="imgError = true"
      />
      <button
        type="button"
        @click="$emit('update:modelValue', ''); imgError = false"
        class="absolute -top-1.5 -right-1.5 w-5 h-5 bg-red-500 text-white rounded-full text-xs flex items-center justify-center hover:bg-red-600"
      >&times;</button>
    </div>
    <div v-else-if="modelValue && imgError" class="mt-2 flex items-center gap-2 text-xs text-red-500">
      <span>圖片無法載入</span>
      <button type="button" @click="$emit('update:modelValue', ''); imgError = false" class="underline">清除</button>
    </div>
  </div>
</template>
