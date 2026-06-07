<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import api, { setAdminToken } from '../../api'
import DrawRecords from './DrawRecords.vue'
import PaymentsPanel from './PaymentsPanel.vue'

const router = useRouter()
const pools = ref([])
const admin = ref(null)
const loading = ref(true)
const activeTab = ref('pools')
const admins = ref([])
let eventSource = null
let idleStart = null
const IDLE_THRESHOLD = 30000

// 2FA state
const otpQrCode = ref('')
const otpQrDataUri = ref('')
const otpSecret = ref('')
const otpCode = ref('')
const otpError = ref('')
const otpLoading = ref(false)

function svgToDataUri(svg) {
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
}

// Admin management state
const showAddAdmin = ref(false)
const newAdmin = ref({ email: '', password: '', display_name: '' })
const adminError = ref('')

async function loadPools() {
  try {
    const res = await api.get('/pools')
    pools.value = res.data
  } catch (e) {
    console.error('Failed to load pools:', e)
  }
}

async function loadAdmin() {
  try {
    const res = await api.get('/auth/me')
    admin.value = res.data
  } catch (e) {
    console.error('Failed to load admin:', e)
  }
}

async function loadAdmins() {
  try {
    const res = await api.get('/admin/accounts')
    admins.value = res.data
  } catch (e) {
    console.error('Failed to load admins:', e)
  }
}

async function verifyAuth() {
  try {
    const res = await api.get('/auth/me')
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
    const [adminRes, poolsRes, adminsRes] = await Promise.all([
      api.get('/auth/me'),
      api.get('/pools'),
      api.get('/admin/accounts'),
    ])
    admin.value = adminRes.data
    pools.value = poolsRes.data
    admins.value = adminsRes.data
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
    } catch (e) {
      console.error('EventSource message parse error:', e)
    }
  }
  eventSource.onerror = () => {
    console.warn('EventSource connection error, will auto-reconnect')
  }

  window.addEventListener('pageshow', onPageShow)
  document.addEventListener('visibilitychange', onVisibilityChange)
})

watch(activeTab, (tab) => {
  if (tab === 'admins') loadAdmins()
  if (tab === 'categories') loadCategories()
})

function onPageShow(event) {
  if (event.persisted) {
    loading.value = true
    admin.value = null
    verifyAuth()
  }
}

onUnmounted(() => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
  window.removeEventListener('pageshow', onPageShow)
  document.removeEventListener('visibilitychange', onVisibilityChange)
})

function logout() {
  setAdminToken(null)
  router.push('/admin/login')
}

const deletingPoolId = ref(null)

const categories = ref([])
const newCategoryName = ref('')
const categoryError = ref('')

function clearCategoryError() {
  setTimeout(() => { categoryError.value = '' }, 3000)
}

async function loadCategories() {
  try {
    const res = await api.get('/categories')
    categories.value = res.data
  } catch (e) {
    console.error('Failed to load categories:', e)
  }
}

async function addCategory() {
  const name = newCategoryName.value.trim()
  if (!name) return
  categoryError.value = ''
  try {
    await api.post('/categories', { name, sort_order: categories.value.length })
    newCategoryName.value = ''
    await loadCategories()
  } catch (e) {
    categoryError.value = e.response?.data?.detail || '新增失敗'
    clearCategoryError()
  }
}

async function deleteCategory(id) {
  categoryError.value = ''
  try {
    await api.delete(`/categories/${id}`)
    await loadCategories()
  } catch (e) {
    categoryError.value = e.response?.data?.detail || '刪除失敗'
    clearCategoryError()
  }
}

async function deletePool(id, name) {
  if (deletingPoolId.value) return
  if (!confirm(`確定要刪除獎池「${name}」？此操作不可恢復。`)) return
  deletingPoolId.value = id
  try {
    await api.delete(`/pools/${id}`)
    pools.value = pools.value.filter(p => p.id !== id)
  } catch (e) {
    alert(e.response?.data?.detail || '刪除失敗')
  } finally {
    deletingPoolId.value = null
  }
}

async function setupOTP() {
  otpError.value = ''
  otpLoading.value = true
  try {
    const res = await api.post('/auth/setup-otp')
    otpQrCode.value = res.data.qr_code
    otpQrDataUri.value = svgToDataUri(res.data.qr_code)
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
    const res = await api.post('/auth/confirm-otp', { otp_code: otpCode.value })
    admin.value = res.data
    otpQrCode.value = ''
    otpQrDataUri.value = ''
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
    const res = await api.post('/auth/disable-otp')
    admin.value = res.data
  } catch (e) {
    alert(e.response?.data?.detail || '停用失敗')
  } finally {
    otpLoading.value = false
  }
}

async function createAdmin() {
  adminError.value = ''
  if (!newAdmin.value.email || !newAdmin.value.password) {
    adminError.value = '請填寫 Email 與密碼'
    return
  }
  try {
    await api.post('/admin/accounts', newAdmin.value)
    newAdmin.value = { email: '', password: '', display_name: '' }
    showAddAdmin.value = false
    await loadAdmins()
  } catch (e) {
    adminError.value = e.response?.data?.detail || '建立失敗'
  }
}

async function deleteAdmin(id) {
  if (!confirm('確定要刪除此管理員帳號？')) return
  try {
    await api.delete(`/admin/accounts/${id}`)
    admins.value = admins.value.filter(a => a.id !== id)
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

    <div class="flex gap-4 mb-6 border-b overflow-x-auto">
      <button @click="activeTab = 'pools'"
        class="pb-3 px-1 text-sm font-medium border-b-2 transition whitespace-nowrap"
        :class="activeTab === 'pools' ? 'text-indigo-600 border-indigo-600' : 'text-gray-500 border-transparent hover:text-gray-700'">
        獎池列表
      </button>
      <button @click="activeTab = 'payments'"
        class="pb-3 px-1 text-sm font-medium border-b-2 transition whitespace-nowrap"
        :class="activeTab === 'payments' ? 'text-indigo-600 border-indigo-600' : 'text-gray-500 border-transparent hover:text-gray-700'">
        付款確認
      </button>
      <button @click="activeTab = 'draws'"
        class="pb-3 px-1 text-sm font-medium border-b-2 transition whitespace-nowrap"
        :class="activeTab === 'draws' ? 'text-indigo-600 border-indigo-600' : 'text-gray-500 border-transparent hover:text-gray-700'">
        抽獎紀錄
      </button>
      <button @click="activeTab = 'admins'"
        class="pb-3 px-1 text-sm font-medium border-b-2 transition whitespace-nowrap"
        :class="activeTab === 'admins' ? 'text-indigo-600 border-indigo-600' : 'text-gray-500 border-transparent hover:text-gray-700'">
        管理員帳號
      </button>
      <button @click="activeTab = 'categories'"
        class="pb-3 px-1 text-sm font-medium border-b-2 transition whitespace-nowrap"
        :class="activeTab === 'categories' ? 'text-indigo-600 border-indigo-600' : 'text-gray-500 border-transparent hover:text-gray-700'">
        類別管理
      </button>
      <button @click="activeTab = 'security'"
        class="pb-3 px-1 text-sm font-medium border-b-2 transition whitespace-nowrap"
        :class="activeTab === 'security' ? 'text-indigo-600 border-indigo-600' : 'text-gray-500 border-transparent hover:text-gray-700'">
        安全設定
      </button>
    </div>

    <div v-if="activeTab === 'pools'">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-lg font-semibold text-gray-900">獎池列表</h2>
        <button @click="router.push('/admin/pools/new')" class="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-indigo-700 cursor-pointer">新增獎池</button>
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
                <button @click="deletePool(pool.id, pool.name)" :disabled="deletingPoolId === pool.id" class="text-red-500 hover:text-red-700 text-xs font-medium disabled:opacity-50 disabled:cursor-not-allowed">
  <span v-if="deletingPoolId === pool.id" class="inline-flex items-center gap-1">
    <svg class="animate-spin h-3 w-3" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
    刪除中
  </span>
  <span v-else>刪除</span>
</button>
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

    <div v-if="activeTab === 'admins'">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-gray-900">管理員帳號管理</h2>
        <button @click="showAddAdmin = !showAddAdmin; adminError = ''"
          class="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-indigo-700">
          {{ showAddAdmin ? '取消' : '新增管理員' }}
        </button>
      </div>

      <div v-if="showAddAdmin" class="bg-white rounded-xl shadow-sm border p-4 mb-4">
        <h3 class="text-sm font-semibold text-gray-900 mb-3">新增管理員帳號</h3>
        <div v-if="adminError" class="bg-red-50 text-red-600 text-sm p-2 rounded-lg mb-3">{{ adminError }}</div>
        <div class="grid grid-cols-3 gap-3 mb-3">
          <div>
            <label class="block text-xs text-gray-500 mb-1">Email</label>
            <input v-model="newAdmin.email" type="email" class="w-full border rounded-lg px-2 py-1.5 text-sm" />
          </div>
          <div>
            <label class="block text-xs text-gray-500 mb-1">密碼</label>
            <input v-model="newAdmin.password" type="password" class="w-full border rounded-lg px-2 py-1.5 text-sm" />
          </div>
          <div>
            <label class="block text-xs text-gray-500 mb-1">顯示名稱</label>
            <input v-model="newAdmin.display_name" class="w-full border rounded-lg px-2 py-1.5 text-sm" placeholder="Admin" />
          </div>
        </div>
        <button @click="createAdmin" class="bg-green-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-green-700">建立</button>
      </div>

      <div class="bg-white rounded-xl shadow-sm border overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 border-b">
            <tr>
              <th class="text-left px-4 py-3 font-medium text-gray-600">Email</th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">顯示名稱</th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">2FA</th>
              <th class="text-left px-4 py-3 font-medium text-gray-600">建立時間</th>
              <th class="text-right px-4 py-3 font-medium text-gray-600">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y">
            <tr v-for="a in admins" :key="a.id" class="hover:bg-gray-50">
              <td class="px-4 py-3 text-gray-900">{{ a.email }}</td>
              <td class="px-4 py-3 text-gray-600">{{ a.display_name }}</td>
              <td class="px-4 py-3">
                <span v-if="a.is_otp_enabled" class="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">已啟用</span>
                <span v-else class="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">未啟用</span>
              </td>
              <td class="px-4 py-3 text-gray-500 text-xs">{{ new Date(a.created_at).toLocaleString('zh-TW') }}</td>
              <td class="px-4 py-3 text-right">
                <button v-if="a.id !== admin?.id" @click="deleteAdmin(a.id)" class="text-red-500 hover:text-red-700 text-xs font-medium">刪除</button>
                <span v-else class="text-xs text-gray-400">目前帳號</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="activeTab === 'categories'">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">類別管理</h2>
      <div class="bg-white rounded-xl shadow-sm border p-4 mb-4 max-w-lg">
        <div class="flex gap-2">
          <input v-model="newCategoryName" @keyup.enter="addCategory" placeholder="新增類別名稱"
            class="flex-1 border rounded-lg px-3 py-2 text-sm" />
          <button @click="addCategory" class="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-indigo-700">新增</button>
        </div>
        <p v-if="categoryError" class="text-red-500 text-xs mt-2">{{ categoryError }}</p>
      </div>
      <div class="bg-white rounded-xl shadow-sm border overflow-hidden max-w-lg">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 border-b">
            <tr>
              <th class="text-left px-4 py-3 font-medium text-gray-600">名稱</th>
              <th class="text-right px-4 py-3 font-medium text-gray-600">操作</th>
            </tr>
          </thead>
          <tbody class="divide-y">
            <tr v-for="cat in categories" :key="cat.id" class="hover:bg-gray-50">
              <td class="px-4 py-3 text-gray-900">{{ cat.name }}</td>
              <td class="px-4 py-3 text-right">
                <button @click="deleteCategory(cat.id)" class="text-red-500 hover:text-red-700 text-xs font-medium">刪除</button>
              </td>
            </tr>
            <tr v-if="categories.length === 0">
              <td colspan="2" class="px-4 py-8 text-center text-gray-400">尚無類別</td>
            </tr>
          </tbody>
        </table>
      </div>
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
          <img :src="otpQrDataUri" class="mb-3 w-48 h-48 mx-auto" alt="OTP QR Code" />
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
