<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'

const route = useRoute()
const items = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await api.get(`/warehouse/${route.params.userId}`)
    items.value = res.data
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 mb-6">我的賞物架</h1>
    <div v-if="loading" class="text-gray-500">載入中...</div>
    <div v-else-if="items.length === 0" class="text-gray-400 text-center py-12">
      還沒有抽中的獎品
    </div>
    <div v-else class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <div v-for="item in items" :key="item.id" class="bg-white rounded-xl shadow-sm border p-4">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">{{ item.grade_name }}</span>
          <span class="text-xs text-gray-400">#{{ item.serial_number }}</span>
        </div>
        <p class="font-semibold text-gray-900">{{ item.item_name }}</p>
        <p class="text-sm text-gray-500">{{ item.pool_name }}</p>
        <div class="mt-2 text-xs text-gray-400">
          <span v-if="item.status === 'unclaimed'" class="text-amber-600">未領取</span>
          <span v-else-if="item.status === 'shipping_requested'" class="text-blue-600">申請出貨中</span>
          <span v-else-if="item.status === 'picked_up'" class="text-green-600">已領取</span>
          <span v-else>{{ item.status }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
