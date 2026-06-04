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
let idleStart = null
const IDLE_THRESHOLD = 30000

// 2FA state
const otpQrCode = ref('')
const otpSecret = ref('')
const otpCode = ref('')
const otpError = ref('')
const otpLoading = ref(false)

async function loadPools() {
  try {
    const res = await api.get('/api/pools')
    pools.value = res.data
  } catch (_) {}
}

async function loadAdmin() {
  try {
    const res = await api.get('/api/auth/me')
    admin.value = res.data
  } catch (_) {}
}

async function verifyAuth() {
  try {
    const res = await api.get('/api/auth/me')
    admin.value = res.data
  } catch (_) {
    router.push('/admin/login')
  } finally {
    loading.value = false
  }
}

function onVisibilityChange() {
  if (document.hidden) {
    idleStart = Date.now()
  } else if (idleStart) {
    const elapsed = Date.now() - idleStart
    idleStart = null
    if (elapsed > IDLE_THRESHOLD) {
      loading.value = true
      admin.value = null
      verifyAuth()
    }
  }
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

  eventSource = new EventSource('/api/events')
  eventSource.onmessage = (e) => {
    if (!e.data) return
    try {
      const { event } = JSON.parse(e.data)
      if (['pool_update', 'pool_deleted', 'draw_result'].includes(event)) {
        loadPools()
      }
    } catch (_) {}
  }

  window.addEventListener('pageshow', onPageShow)
  document.addEventListener('visibilitychange', onVisibilityChange)
})

function onPageShow(event) {
  if (event.persisted) {
    loading.value = true
    admin.value = null
    verifyAuth()
  }
}

onUnmounted(() => {
  if (eventSource) eventSource.close()
  window.removeEventListener('pageshow', onPageShow)
  document.removeEventListener('visibilitychange', onVisibilityChange)
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

async function setupOTP() {
  otpError.value = ''
  otpLoading.value = true
  try {
    const res = await api.post('/api/auth/setup-otp')
    otpQrCode.value = res.data.qr_code
    otpSecret.value = res.data.otp_secret
    otpCode.value = ''
  } catch (e) {
    otpError.value = e.response?.data?.detail || '設定失敗'
  } finally {
    otpLoading.value = false
  }
}

async function confirmOTP() {
  otpError.value = ''
  if (!otpCode.value) { otpError.value = '請輸入驗證碼'; return }
  otpLoading.value = true
  try {
    const res = await api.post('/api/auth/confirm-otp', { otp_code: otpCode.value })
    admin.value = res.data
    otpQrCode.value = ''
    otpSecret.value = ''
    otpCode.value = ''
  } catch (e) {
    otpError.value = e.response?.data?.detail || '驗證失敗'
  } finally {
    otpLoading.value = false
  }
}

async function disableOTP() {
  if (!confirm('確定要停用兩步驟驗證？')) return
  otpLoading.value = true
  try {
    const res = await api.post('/api/auth/disable-otp')
    admin.value = res.data
  } catch (e) {
    alert(e.response?.data?.detail || '停用失敗')
  } finally {
    otpLoading.value = false
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
      <button @click="activeTab = 'security'"
        class="pb-3 px-1 text-sm font-medium border-b-2 transition"
        :class="activeTab === 'security' ? 'text-indigo-600 border-indigo-600' : 'text-gray-500 border-transparent hover:text-gray-700'">
        安全設定
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

    <div v-if="activeTab === 'security'">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">安全設定</h2>

      <div class="bg-white rounded-xl shadow-sm border p-6 max-w-lg">
        <div class="flex items-center justify-between mb-4">
          <div>
            <div class="text-sm font-medium text-gray-900">兩步驟驗證 (2FA)</div>
            <div class="text-xs text-gray-500 mt-1">使用 Google Authenticator 等 TOTP 應用程式</div>
          </div>
          <span v-if="admin?.is_otp_enabled"
            class="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">已啟用</span>
          <span v-else
            class="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full font-medium">未啟用</span>
        </div>

        <div v-if="!admin?.is_otp_enabled && !otpQrCode">
          <button @click="setupOTP" :disabled="otpLoading"
            class="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
            {{ otpLoading ? '處理中...' : '啟用兩步驟驗證' }}
          </button>
        </div>

        <div v-if="otpQrCode" class="border-t pt-4 mt-4">
          <p class="text-sm text-gray-700 mb-3">請使用 Google Authenticator 掃描以下 QR Code</p>
          <div v-html="otpQrCode" class="mb-3 w-48 h-48 mx-auto"></div>
          <p class="text-xs text-gray-400 text-center mb-3">或手動輸入密鑰：<code class="font-mono bg-gray-100 px-1">{{ otpSecret }}</code></p>
          <div v-if="otpError" class="bg-red-50 text-red-600 text-sm p-2 rounded-lg mb-3">{{ otpError }}</div>
          <div class="flex gap-2">
            <input v-model="otpCode" type="text" placeholder="輸入驗證碼"
              class="flex-1 border rounded-lg px-3 py-2 text-sm text-center tracking-widest" />
            <button @click="confirmOTP" :disabled="otpLoading"
              class="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-green-700 disabled:opacity-50">
              驗證
            </button>
          </div>
        </div>

        <div v-if="admin?.is_otp_enabled" class="border-t pt-4 mt-4">
          <p class="text-sm text-gray-500 mb-3">已啟用兩步驟驗證，登入時需額外輸入 Google Authenticator 驗證碼。</p>
          <button @click="disableOTP" :disabled="otpLoading"
            class="bg-red-100 text-red-700 px-4 py-2 rounded-lg text-sm font-semibold hover:bg-red-200 disabled:opacity-50">
            停用兩步驟驗證
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
