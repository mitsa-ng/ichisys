<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'

const route = useRoute()
const pool = ref(null)
const loading = ref(true)

async function loadPool() {
  try {
    const res = await api.get(`/pools/${route.params.id}`)
    pool.value = res.data
  } catch (e) {
    console.error('Failed to load pool:', e)
  }
}

onMounted(async () => {
  await loadPool()
  loading.value = false
})

const sortedGrades = computed(() => {
  if (!pool.value?.prize_grades) return []
  return [...pool.value.prize_grades].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
})

const leftColumn = computed(() => {
  const grades = sortedGrades.value
  const mid = Math.ceil(grades.length / 2)
  return grades.slice(0, mid)
})

const rightColumn = computed(() => {
  const grades = sortedGrades.value
  const mid = Math.ceil(grades.length / 2)
  return grades.slice(mid)
})

function itemProgress(item) {
  if (!item.stock) return 0
  return (item.remaining_stock / item.stock) * 100
}

function gradeProgress(g) {
  const total = g.prize_items?.reduce((s, i) => s + i.stock, 0) || 0
  const remaining = g.prize_items?.reduce((s, i) => s + i.remaining_stock, 0) || 0
  if (!total) return 0
  return (remaining / total) * 100
}

function gradeTotalStock(g) {
  return g.prize_items?.reduce((s, i) => s + i.stock, 0) || 0
}

function gradeRemainingStock(g) {
  return g.prize_items?.reduce((s, i) => s + i.remaining_stock, 0) || 0
}
</script>

<template>
  <div v-if="loading" class="text-gray-500 text-center py-12">載入中...</div>
  <div v-else-if="pool">
    <div class="flex items-center gap-3 mb-6">
      <a :href="`/pool/${pool.id}`" class="text-gray-400 hover:text-gray-600">&larr; 返回獎池</a>
      <h1 class="text-xl font-bold text-gray-900">{{ pool.name }} - 獎賞剩餘</h1>
    </div>

    <!-- Stats bar -->
    <div class="bg-white rounded-xl shadow-sm border p-4 mb-6">
      <div class="grid grid-cols-3 gap-4 text-center text-sm">
        <div>
          <span class="text-gray-500">總抽數</span>
          <div class="text-lg font-bold text-gray-900">{{ pool.total_tickets }}</div>
        </div>
        <div>
          <span class="text-gray-500">已抽</span>
          <div class="text-lg font-bold text-indigo-600">{{ pool.total_tickets - pool.remaining_tickets }}</div>
        </div>
        <div>
          <span class="text-gray-500">剩餘</span>
          <div class="text-lg font-bold text-orange-600">{{ pool.remaining_tickets }}</div>
        </div>
      </div>
    </div>

    <!-- Two-column remaining prize display -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <!-- Left column -->
      <div class="space-y-3">
        <div v-for="g in leftColumn" :key="g.id"
          class="bg-white rounded-xl shadow-sm border p-4"
          :class="
            gradeRemainingStock(g) === 0 ? 'opacity-50' :
            g.grade_name === 'A賞' ? 'border-indigo-300 bg-indigo-50/30' :
            g.grade_name === 'B賞' ? 'border-purple-300 bg-purple-50/30' : ''
          "
        >
          <div class="flex items-center gap-3 mb-2">
            <span class="font-bold text-gray-900">{{ g.grade_name }}</span>
            <span class="text-xs text-gray-400">總計 {{ gradeTotalStock(g) }} 張</span>
          </div>

          <!-- Grade-level progress bar -->
          <div class="flex items-center gap-3 mb-2">
            <div class="flex-1 bg-gray-200 rounded-full h-2">
              <div class="h-2 rounded-full transition-all"
                :class="
                  gradeRemainingStock(g) === 0 ? 'bg-gray-400' :
                  gradeProgress(g) <= 0.25 ? 'bg-red-500' :
                  gradeProgress(g) <= 0.5 ? 'bg-amber-500' : 'bg-green-500'
                "
                :style="{ width: `${gradeProgress(g)}%` }"
              />
            </div>
            <span class="text-xs font-semibold whitespace-nowrap"
              :class="gradeRemainingStock(g) === 0 ? 'text-gray-400' : 'text-gray-700'"
            >
              {{ gradeRemainingStock(g) }} / {{ gradeTotalStock(g) }}
            </span>
          </div>

          <!-- Sub-items -->
          <div class="space-y-2 mt-3">
            <div v-for="item in g.prize_items" :key="item.id"
              class="flex items-center gap-3 bg-white/80 rounded-lg p-2"
            >
              <div v-if="item.image_url" class="shrink-0">
                <img :src="item.image_url" class="w-12 h-12 object-cover rounded-lg" />
              </div>
              <div v-else class="shrink-0 w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center text-lg font-bold text-gray-300">
                {{ item.name?.charAt(0) || '?' }}
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium text-gray-800 truncate">{{ item.name }}</div>
                <div class="text-xs text-gray-400">{{ item.category }}</div>
                <div class="flex items-center gap-2 mt-1">
                  <div class="flex-1 bg-gray-200 rounded-full h-1.5">
                    <div class="h-1.5 rounded-full transition-all"
                      :class="
                        item.remaining_stock === 0 ? 'bg-gray-400' :
                        itemProgress(item) <= 0.25 ? 'bg-red-500' :
                        itemProgress(item) <= 0.5 ? 'bg-amber-500' : 'bg-green-500'
                      "
                      :style="{ width: `${itemProgress(item)}%` }"
                    />
                  </div>
                  <span class="text-xs font-medium whitespace-nowrap text-gray-600">
                    {{ item.remaining_stock }}/{{ item.stock }}
                  </span>
                </div>
                <div v-if="item.remaining_stock === 0" class="text-xs text-red-400 font-medium mt-0.5">已售完</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right column -->
      <div class="space-y-3">
        <div v-for="g in rightColumn" :key="g.id"
          class="bg-white rounded-xl shadow-sm border p-4"
          :class="
            gradeRemainingStock(g) === 0 ? 'opacity-50' :
            g.grade_name === 'A賞' ? 'border-indigo-300 bg-indigo-50/30' :
            g.grade_name === 'B賞' ? 'border-purple-300 bg-purple-50/30' : ''
          "
        >
          <div class="flex items-center gap-3 mb-2">
            <span class="font-bold text-gray-900">{{ g.grade_name }}</span>
            <span class="text-xs text-gray-400">總計 {{ gradeTotalStock(g) }} 張</span>
          </div>

          <!-- Grade-level progress bar -->
          <div class="flex items-center gap-3 mb-2">
            <div class="flex-1 bg-gray-200 rounded-full h-2">
              <div class="h-2 rounded-full transition-all"
                :class="
                  gradeRemainingStock(g) === 0 ? 'bg-gray-400' :
                  gradeProgress(g) <= 0.25 ? 'bg-red-500' :
                  gradeProgress(g) <= 0.5 ? 'bg-amber-500' : 'bg-green-500'
                "
                :style="{ width: `${gradeProgress(g)}%` }"
              />
            </div>
            <span class="text-xs font-semibold whitespace-nowrap"
              :class="gradeRemainingStock(g) === 0 ? 'text-gray-400' : 'text-gray-700'"
            >
              {{ gradeRemainingStock(g) }} / {{ gradeTotalStock(g) }}
            </span>
          </div>

          <!-- Sub-items -->
          <div class="space-y-2 mt-3">
            <div v-for="item in g.prize_items" :key="item.id"
              class="flex items-center gap-3 bg-white/80 rounded-lg p-2"
            >
              <div v-if="item.image_url" class="shrink-0">
                <img :src="item.image_url" class="w-12 h-12 object-cover rounded-lg" />
              </div>
              <div v-else class="shrink-0 w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center text-lg font-bold text-gray-300">
                {{ item.name?.charAt(0) || '?' }}
              </div>
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium text-gray-800 truncate">{{ item.name }}</div>
                <div class="text-xs text-gray-400">{{ item.category }}</div>
                <div class="flex items-center gap-2 mt-1">
                  <div class="flex-1 bg-gray-200 rounded-full h-1.5">
                    <div class="h-1.5 rounded-full transition-all"
                      :class="
                        item.remaining_stock === 0 ? 'bg-gray-400' :
                        itemProgress(item) <= 0.25 ? 'bg-red-500' :
                        itemProgress(item) <= 0.5 ? 'bg-amber-500' : 'bg-green-500'
                      "
                      :style="{ width: `${itemProgress(item)}%` }"
                    />
                  </div>
                  <span class="text-xs font-medium whitespace-nowrap text-gray-600">
                    {{ item.remaining_stock }}/{{ item.stock }}
                  </span>
                </div>
                <div v-if="item.remaining_stock === 0" class="text-xs text-red-400 font-medium mt-0.5">已售完</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
