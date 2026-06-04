<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import api, { setAdminToken } from '../../api'
import DrawRecords from './DrawRecords.vue'
import PaymentsPanel from './PaymentsPanel.vue'

const router = useRouter()
const pools = ref([])
const admin = ref(null)
const loading = ref(true)
const activeTab = ref('pools')
let eventSource = null

async function loadPools() {
  try {
    const res = await api.get('/api/pools')
    pools.value = res.data
  } catch (_) {}
}

onMounted(async () => {
  try {
    const [adminRes, poolsRes] = await Promise.all([
      api.get('/api/auth/me'),
      api.get('/api/pools'),
    ])
    admin.value = adminRes.data
    pools.value = poolsRes.data
  } catch (e) {
    router.push('/admin/login')
  } finally {
    loading.value = false
  }

  eventSource = new EventSource('http://localhost:8000/api/events')
  eventSource.onmessage = (e) => {
    if (!e.data) return
    try {
      const { event } = JSON.parse(e.data)
      if (['pool_update', 'pool_deleted', 'draw_result'].includes(event)) {
        loadPools()
      }
    } catch (_) {}
  }
})

onUnmounted(() => {
  if (eventSource) eventSource.close()
})

function logout() {
  setAdminToken(null)
  router.push('/admin/login')
}

async function deletePool(id, name) {
  if (!confirm(`確定要刪除獎池「${name}」？此操作不可恢復。`)) return
  try {
    await api.delete(`/api/pools/${id}`)
    pools.value = pools.value.filter(p => p.id !== id)
  } catch (e) {
    alert(e.response?.data?.detail || '刪除失敗')
  }
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900">管理後台</h1>
      <div class="flex items-center gap-3">
        <span class="text-sm text-gray-500">{{ admin?.display_name }}</span>
        <button @click="logout" class="text-sm text-red-500 hover:text-red-700">登出</button>
      </div>
    </div>

    <div class="flex gap-4 mb-6 border-b">
      <button @click="activeTab = 'pools'"
        class="pb-3 px-1 text-sm font-medium border-b-2 transition"
        :class="activeTab === 'pools' ? 'text-indigo-600 border-indigo-600' : 'text-gray-500 border-transparent hover:text-gray-700'">
        獎池列表
      </button>
      <button @click="activeTab = 'payments'"
        class="pb-3 px-1 text-sm font-medium border-b-2 transition"
        :class="activeTab === 'payments' ? 'text-indigo-600 border-indigo-600' : 'text-gray-500 border-transparent hover:text-gray-700'">
        付款確認
      </button>
      <button @click="activeTab = 'draws'"
        class="pb-3 px-1 text-sm font-medium border-b-2 transition"
        :class="activeTab === 'draws' ? 'text-indigo-600 border-indigo-600' : 'text-gray-500 border-transparent hover:text-gray-700'">
        抽獎紀錄
      </button>
    </div>

    <div v-if="activeTab === 'pools'">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-lg font-semibold text-gray-900">獎池列表</h2>
        <a href="/admin/pools/new" class="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-indigo-700">新增獎池</a>
      </div>

      <div v-if="loading" class="text-gray-500">載入中...</div>
      <div v-else-if="pools.length === 0" class="text-gray-400 text-center py-12">還沒有獎池</div>
      <div v-else class="bg-white rounded-xl shadow-sm border overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 border-b">
            <tr>
              <th class="text-left px-4 py-3 font-medium text-gray-600">編號</th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">名稱</th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">狀態</th>
              <th class="text-right px-4 py-3 font-medium text-gray-600">單抽價</th>
              <th class="text-right px-4 py-3 font-medium text-gray-600">剩餘/總抽</th>
              <th class="text-right px-4 py-3 font-medium text-gray-600">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y">
            <tr v-for="pool in pools" :key="pool.id" class="hover:bg-gray-50">
              <td class="px-4 py-3 text-gray-500 font-mono text-xs">{{ pool.code }}</td>
              <td class="px-4 py-3 font-medium text-gray-900">{{ pool.name }}</td>
              <td class="px-4 py-3">
                <span
                  :class="[
                    'text-xs px-2 py-0.5 rounded-full',
                    pool.status === 'published' ? 'bg-green-100 text-green-700' :
                    pool.status === 'draft' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-gray-100 text-gray-600',
                  ]"
                >
                  {{ pool.status === 'published' ? '上架' : pool.status === 'draft' ? '草稿' : pool.status }}
                </span>
              </td>
              <td class="px-4 py-3 text-right text-gray-900">${{ pool.single_price }}</td>
              <td class="px-4 py-3 text-right text-gray-600">{{ pool.remaining_tickets }} / {{ pool.total_tickets }}</td>
              <td class="px-4 py-3 text-right flex items-center justify-end gap-2">
                <a :href="`/admin/pools/${pool.id}`" class="text-indigo-600 hover:text-indigo-800 text-xs font-medium">管理</a>
                <button @click="deletePool(pool.id, pool.name)" class="text-red-500 hover:text-red-700 text-xs font-medium">刪除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="activeTab === 'payments'">
      <PaymentsPanel />
    </div>

    <div v-if="activeTab === 'draws'">
      <DrawRecords />
    </div>
  </div>
</template>
