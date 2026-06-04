<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const pools = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const res = await api.get('/pools?status_filter=published')
    pools.value = res.data
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <div>
    <h1 class="text-2xl font-bold text-gray-900 mb-6">一番賞獎池</h1>
    <div v-if="loading" class="text-gray-500">載入中...</div>
    <div v-else-if="pools.length === 0" class="text-gray-400 text-center py-12">
      目前沒有開放的獎池
    </div>
    <div v-else class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      <a
        v-for="pool in pools"
        :key="pool.id"
        :href="`/pool/${pool.id}`"
        class="block bg-white rounded-xl shadow-sm border hover:shadow-md transition overflow-hidden"
      >
        <div v-if="pool.banner_image" class="h-40 bg-gray-100">
          <img :src="pool.banner_image" :alt="pool.name" class="w-full h-full object-cover" />
        </div>
        <div v-else class="h-40 bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
          <span class="text-white text-lg font-bold">{{ pool.name }}</span>
        </div>
        <div class="p-4">
          <div class="flex items-center gap-2 mb-2">
            <span class="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">上架中</span>
          </div>
          <h3 class="font-semibold text-gray-900">{{ pool.name }}</h3>
          <p class="text-sm text-gray-500 mt-1">{{ pool.grade_count }} 種獎項</p>
          <div class="flex justify-between items-center mt-3 text-sm">
            <span class="text-gray-500">剩餘 <strong class="text-gray-900">{{ pool.remaining_tickets }}</strong> / {{ pool.total_tickets }} 抽</span>
            <span class="font-semibold text-indigo-600">${{ pool.single_price }} / 抽</span>
          </div>
          <div class="mt-2 w-full bg-gray-200 rounded-full h-1.5">
            <div
              class="bg-indigo-500 h-1.5 rounded-full"
              :style="{ width: `${((pool.total_tickets - pool.remaining_tickets) / pool.total_tickets) * 100}%` }"
            />
          </div>
        </div>
      </a>
    </div>
  </div>
</template>
