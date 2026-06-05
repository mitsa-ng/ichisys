<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api'

const records = ref([])
const loading = ref(true)
const filterPoolId = ref('')
const pools = ref([])

const stats = computed(() => {
  const totalRevenue = records.value.reduce((s, r) => s + r.amount, 0)
  const totalCost = records.value.reduce((s, r) => s + r.cost, 0)
  const totalProfit = records.value.reduce((s, r) => s + r.profit, 0)
  return { totalRevenue, totalCost, totalProfit, count: records.value.length }
})

function exportCSV() {
  const params = new URLSearchParams()
  if (filterPoolId.value) params.set('pool_id', filterPoolId.value)
  const token = localStorage.getItem('admin_token')
  const url = `/api/admin/draws/export?${params.toString()}`
  const a = document.createElement('a')
  a.href = url
  a.download = 'draw_records.csv'
  fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
    .then(res => res.blob())
    .then(blob => {
      const obj = URL.createObjectURL(blob)
      a.href = obj
      a.click()
      URL.revokeObjectURL(obj)
    })
}

async function loadDrawRecords() {
  loading.value = true
  try {
    const params = {}
    if (filterPoolId.value) params.pool_id = filterPoolId.value
    const res = await api.get('/admin/draws', { params })
    records.value = res.data
  } catch (_) {}
  finally { loading.value = false }
}

async function loadPools() {
  try {
    const res = await api.get('/pools')
    pools.value = res.data
  } catch (_) {}
}

onMounted(async () => {
  await Promise.all([loadDrawRecords(), loadPools()])
})

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei' })
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-semibold text-gray-900">抽獎紀錄</h2>
      <div class="flex items-center gap-3">
        <button @click="exportCSV"
          class="bg-green-600 text-white px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-green-700">
          匯出 CSV
        </button>
        <select v-model="filterPoolId" @change="loadDrawRecords"
          class="border rounded-lg px-3 py-1.5 text-sm text-gray-700">
          <option value="">全部獎池</option>
          <option v-for="p in pools" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
      </div>
    </div>

    <div v-if="loading" class="text-gray-500">載入中...</div>
    <div v-else-if="records.length === 0" class="text-gray-400 text-center py-12">尚無抽獎紀錄</div>
    <div v-else>
      <div class="bg-white rounded-xl shadow-sm border overflow-hidden mb-4">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 border-b">
            <tr>
              <th class="text-left px-3 py-2 font-medium text-gray-600">時間</th>
              <th class="text-left px-3 py-2 font-medium text-gray-600">獎池</th>
              <th class="text-right px-3 py-2 font-medium text-gray-600">號碼</th>
              <th class="text-left px-3 py-2 font-medium text-gray-600">獎項</th>
              <th class="text-right px-3 py-2 font-medium text-gray-600">售價</th>
              <th class="text-right px-3 py-2 font-medium text-gray-600">成本</th>
              <th class="text-right px-3 py-2 font-medium text-gray-600">利潤</th>
              <th class="text-left px-3 py-2 font-medium text-gray-600">付款</th>
              <th class="text-left px-3 py-2 font-medium text-gray-600">備註</th>
            </tr>
          </thead>
          <tbody class="divide-y">
            <tr v-for="r in records" :key="r.serial_number + '_' + r.drawn_at"
              class="hover:bg-gray-50">
              <td class="px-3 py-2 text-gray-500 text-xs whitespace-nowrap">{{ formatDate(r.drawn_at) }}</td>
              <td class="px-3 py-2 font-medium text-gray-900">
                <span class="font-mono text-xs text-gray-400">{{ r.pool_code }}</span>
                {{ r.pool_name }}
              </td>
              <td class="px-3 py-2 text-right font-mono text-sm">{{ r.serial_number }}</td>
              <td class="px-3 py-2">
                <span v-if="r.grade_name" class="text-gray-900">{{ r.grade_name }}</span>
                <span v-if="r.item_name" class="text-gray-500 text-xs ml-1">/ {{ r.item_name }}</span>
                <span v-else class="text-gray-400">未中獎</span>
              </td>
              <td class="px-3 py-2 text-right text-gray-900">${{ r.single_price.toLocaleString() }}</td>
              <td class="px-3 py-2 text-right text-gray-600">${{ r.cost.toLocaleString() }}</td>
              <td class="px-3 py-2 text-right font-semibold"
                :class="r.profit >= 0 ? 'text-green-600' : 'text-red-600'">
                ${{ r.profit.toLocaleString() }}
              </td>
              <td class="px-3 py-2 text-gray-600">{{ r.payment_method === 'onsite' ? '現場' : r.payment_method === 'linepay' ? 'LinePay' : r.payment_method === 'draw_now' ? '抽就對了' : r.payment_method }}</td>
              <td class="px-3 py-2">
                <span v-if="r.is_multi_draw" class="text-xs bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded">
                  同筆訂單 {{ r.amount > 0 ? '$' + r.amount.toLocaleString() : '' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="bg-gray-50 rounded-xl border p-4 grid grid-cols-4 gap-4 text-sm">
        <div>
          <span class="text-gray-500">總筆數</span>
          <div class="text-lg font-bold text-gray-900">{{ stats.count }}</div>
        </div>
        <div>
          <span class="text-gray-500">總營收</span>
          <div class="text-lg font-bold text-green-600">${{ stats.totalRevenue.toLocaleString() }}</div>
        </div>
        <div>
          <span class="text-gray-500">總成本</span>
          <div class="text-lg font-bold text-red-600">${{ stats.totalCost.toLocaleString() }}</div>
        </div>
        <div>
          <span class="text-gray-500">總利潤</span>
          <div class="text-lg font-bold text-indigo-600">${{ stats.totalProfit.toLocaleString() }}</div>
        </div>
      </div>
    </div>
  </div>
</template>
