<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../../api'
import ImageUploader from '../../components/ImageUploader.vue'

const route = useRoute()
const router = useRouter()
const pool = ref(null)
const loading = ref(true)
let idleStart = null
const IDLE_THRESHOLD = 30000

const categoryPresets = ref(['卡牌', '公仔', '吊飾', '徽章', '立牌', '海報', '其他'])
const customCategoryItems = ref({})

async function loadCategories() {
  try {
    const res = await api.get('/categories')
    if (res.data?.length) {
      categoryPresets.value = res.data.map(c => c.name)
    }
  } catch (_) {}
}

const GRADE_LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

function gradeName(index) {
  return GRADE_LETTERS[index] + '賞'
}

function gradeIndex(name) {
  const m = name.match(/^([A-Z])賞$/)
  if (m) return GRADE_LETTERS.indexOf(m[1])
  return -1
}

async function verifyAuth() {
  try {
    await api.get('/auth/me')
    const res = await api.get(`/pools/${route.params.id}`)
    pool.value = res.data
  } catch (e) {
    console.error('Auth check failed:', e)
    router.push('/admin')
  } finally {
    loading.value = false
  }
}

function onPageShow(event) {
  if (event.persisted) {
    loading.value = true
    pool.value = null
    verifyAuth()
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
      pool.value = null
      verifyAuth()
    }
  }
}

const editing = ref(false)
const saving = ref(false)
const deleting = ref(false)
const publishing = ref(false)
const shuffling = ref(false)

const editForm = ref({
  name: '',
  banner_image: '',
  single_price: 0,
  total_tickets: null,
  allow_shipping: true,
  shipping_fee: 0,
  free_shipping_threshold: 0,
  payment_methods: [],
  grades: [],
})

const error = ref('')

onMounted(() => {
  loadCategories()
  window.addEventListener('pageshow', onPageShow)
  document.addEventListener('visibilitychange', onVisibilityChange)
})

onMounted(async () => {
  try {
    const res = await api.get(`/pools/${route.params.id}`)
    pool.value = res.data
  } catch (e) {
    router.push('/admin')
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  window.removeEventListener('pageshow', onPageShow)
  document.removeEventListener('visibilitychange', onVisibilityChange)
})

function onCategorySelect(event, gi, ii) {
  if (event.target.value === '__custom__') {
    customCategoryItems.value[gi + '-' + ii] = true
  }
}

function startEdit() {
  const p = pool.value
  editForm.value = {
    name: p.name,
    banner_image: p.banner_image || '',
    single_price: p.single_price,
    total_tickets: p.total_tickets,
    allow_shipping: p.allow_shipping,
    shipping_fee: p.shipping_fee,
    free_shipping_threshold: p.free_shipping_threshold,
    payment_methods: (p.payment_methods || '').split(',').filter(Boolean),
    grades: (p.prize_grades || []).map(g => ({
      id: g.id,
      prize_items: (g.prize_items || []).map(item => ({
        id: item.id,
        name: item.name,
        stock: item.stock,
        category: item.category,
        cost: item.cost,
        market_price: item.market_price,
        image_url: item.image_url || '',
      })),
    })),
  }
  customCategoryItems.value = {}
  p.prize_grades?.forEach((g, gi) =>
    g.prize_items?.forEach((item, ii) => {
      if (!categoryPresets.value.includes(item.category)) {
        customCategoryItems.value[gi + '-' + ii] = true
      }
    })
  )
  error.value = ''
  editing.value = true
}

function cancelEdit() {
  editing.value = false
  error.value = ''
}

function formatError(e) {
  if (e.response?.data?.detail) {
    const detail = e.response.data.detail
    if (Array.isArray(detail)) {
      return detail.map(err => {
        const field = err.loc?.filter(p => p !== 'body').join('.') || ''
        return field ? `${field}: ${err.msg}` : err.msg
      }).join('；')
    }
    return detail
  }
  return e.message || '操作失敗'
}

async function saveEdit() {
  saving.value = true
  error.value = ''
  if (editForm.value.payment_methods.length === 0) {
    error.value = '至少需要選擇一種付款方式'
    saving.value = false
    return
  }
  try {
    if (pool.value.status === 'draft') {
      const payload = {
        name: editForm.value.name,
        banner_image: editForm.value.banner_image || null,
        single_price: editForm.value.single_price,
        total_tickets: editForm.value.total_tickets || null,
        allow_shipping: editForm.value.allow_shipping,
        shipping_fee: editForm.value.shipping_fee,
        free_shipping_threshold: editForm.value.free_shipping_threshold,
        payment_methods: editForm.value.payment_methods.join(','),
        prize_grades: editForm.value.grades.map((g, i) => ({
          grade_name: gradeName(i),
          sort_order: i,
          prize_items: g.prize_items.map((item, j) => ({
            name: item.name,
            stock: Number(item.stock) || 0,
            category: item.category || '卡牌',
            cost: Number(item.cost) || 0,
            market_price: Number(item.market_price) || 0,
            image_url: item.image_url || null,
            sort_order: j,
          })),
        })),
      }
      const res = await api.patch(`/pools/${route.params.id}`, payload)
      pool.value = res.data
    } else {
      const poolPayload = {
        name: editForm.value.name,
        banner_image: editForm.value.banner_image || null,
        single_price: editForm.value.single_price,
        total_tickets: editForm.value.total_tickets || null,
        allow_shipping: editForm.value.allow_shipping,
        shipping_fee: editForm.value.shipping_fee,
        free_shipping_threshold: editForm.value.free_shipping_threshold,
        payment_methods: editForm.value.payment_methods.join(','),
      }
      const [poolRes] = await Promise.all([
        api.patch(`/pools/${route.params.id}`, poolPayload),
      ])
      pool.value = poolRes.data
    }
    editing.value = false
  } catch (e) {
    error.value = formatError(e)
  } finally {
    saving.value = false
  }
}

async function deletePool() {
  if (deleting.value) return
  if (!confirm('確定要刪除此獎池？此操作不可恢復。')) return
  deleting.value = true
  try {
    await api.delete(`/pools/${route.params.id}`)
    router.push('/admin')
  } catch (e) {
    alert(e.response?.data?.detail || '刪除失敗')
    deleting.value = false
  }
}

async function publishPool() {
  if (publishing.value) return
  if (!confirm('確定要上架此獎池？將自動進行洗牌並開放抽獎。')) return
  publishing.value = true
  try {
    await api.post(`/pools/${route.params.id}/publish`)
    const res = await api.get(`/pools/${route.params.id}`)
    pool.value = res.data
  } catch (e) {
    alert(e.response?.data?.detail || '上架失敗')
  } finally {
    publishing.value = false
  }
}

async function shufflePool() {
  if (shuffling.value) return
  if (!confirm('確定要重新洗牌？這將重置所有抽獎券。')) return
  shuffling.value = true
  try {
    await api.post(`/pools/${route.params.id}/shuffle`)
    const res = await api.get(`/pools/${route.params.id}`)
    pool.value = res.data
  } catch (e) {
    alert(e.response?.data?.detail || '洗牌失敗')
  } finally {
    shuffling.value = false
  }
}

function addGrade() {
  editForm.value.grades.push({ prize_items: [{ name: '', stock: 1, category: '卡牌', cost: 0, market_price: 0, image_url: '' }] })
}

function removeGrade(i) {
  if (editForm.value.grades.length <= 2) return
  editForm.value.grades.splice(i, 1)
}

function addItem(gradeIndex) {
  editForm.value.grades[gradeIndex].prize_items.push({ name: '', stock: 1, category: '卡牌', cost: 0, market_price: 0, image_url: '' })
}

function removeItem(gradeIndex, itemIndex) {
  editForm.value.grades[gradeIndex].prize_items.splice(itemIndex, 1)
}

const stockTotal = computed(() =>
  editForm.value.grades.reduce((s, g) => s + g.prize_items.reduce((si, item) => si + (Number(item.stock) || 0), 0), 0)
)

const effectiveTotalTickets = computed(() =>
  editForm.value.total_tickets != null ? Number(editForm.value.total_tickets) : stockTotal.value
)

const ticketWarning = computed(() =>
  editForm.value.total_tickets != null && effectiveTotalTickets.value > stockTotal.value
    ? `總抽數 (${effectiveTotalTickets.value}) 大於獎品總庫存 (${stockTotal.value})，超出部分將成為無對應獎品的抽獎券`
    : ''
)

const isDraft = computed(() => pool.value?.status === 'draft')
</script>

<template>
  <div v-if="loading" class="text-gray-500">載入中...</div>
  <div v-else-if="pool">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <a href="/admin" class="text-gray-400 hover:text-gray-600">&larr; 返回</a>
        <h1 class="text-2xl font-bold text-gray-900">{{ pool.name }}</h1>
        <span
          :class="[
            'text-xs px-2 py-0.5 rounded-full',
            pool.status === 'published' ? 'bg-green-100 text-green-700' :
            pool.status === 'draft' ? 'bg-yellow-100 text-yellow-700' :
            'bg-gray-100 text-gray-600',
          ]"
        >
          {{ pool.status === 'published' ? '已上架' : pool.status === 'draft' ? '草稿' : pool.status }}
        </span>
      </div>
      <div class="flex gap-2">
        <button
          v-if="!editing"
          @click="startEdit"
          class="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-indigo-700"
        >
          編輯
        </button>
        <button
          @click="deletePool"
          :disabled="deleting"
          class="bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span v-if="deleting" class="inline-flex items-center gap-1">
            <svg class="animate-spin h-3.5 w-3.5" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
            刪除中...
          </span>
          <span v-else>刪除</span>
        </button>
      </div>
    </div>

    <!-- Stats Cards -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <div class="bg-white rounded-xl shadow-sm border p-4">
        <div class="text-sm text-gray-500">單抽價格</div>
        <div class="text-xl font-bold text-gray-900">${{ pool.single_price }}</div>
      </div>
      <div class="bg-white rounded-xl shadow-sm border p-4">
        <div class="text-sm text-gray-500">剩餘 / 總抽</div>
        <div class="text-xl font-bold text-gray-900">{{ pool.remaining_tickets }} / {{ pool.total_tickets }}</div>
      </div>
      <div class="bg-white rounded-xl shadow-sm border p-4">
        <div class="text-sm text-gray-500">預期營收</div>
        <div class="text-xl font-bold text-gray-900">${{ (pool.total_tickets * pool.single_price).toLocaleString() }}</div>
      </div>
      <div class="bg-white rounded-xl shadow-sm border p-4">
        <div class="text-sm text-gray-500">獎項種類</div>
        <div class="text-xl font-bold text-gray-900">{{ pool.prize_grades?.length || 0 }}</div>
      </div>
    </div>

    <!-- Edit Mode -->
    <div v-if="editing" class="bg-white rounded-xl shadow-sm border p-6 mb-6">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">編輯獎池</h2>
      <div v-if="error" class="bg-red-50 text-red-600 text-sm p-3 rounded-lg mb-4">{{ error }}</div>

      <div class="grid grid-cols-2 gap-4 mb-6">
        <div class="col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">獎池名稱</label>
          <input v-model="editForm.name" class="w-full border rounded-lg px-3 py-2 text-sm" />
        </div>
        <div class="col-span-2">
          <ImageUploader v-model="editForm.banner_image" label="橫幅圖片" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">單抽售價</label>
          <input v-model.number="editForm.single_price" type="number" class="w-full border rounded-lg px-3 py-2 text-sm" />
        </div>
      </div>

      <!-- Prize Grades Edit -->
      <div class="border-t pt-4 mb-4">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-md font-semibold text-gray-900">獎項設定</h3>
          <button type="button" @click="addGrade" class="text-sm text-indigo-600 hover:text-indigo-800">+ 新增賞別</button>
        </div>
        <div v-for="(g, gi) in editForm.grades" :key="gi" class="border rounded-xl p-4 mb-3"
          :class="gradeName(gi) === 'A賞' ? 'border-indigo-200 bg-indigo-50/30' : gradeName(gi) === 'B賞' ? 'border-purple-200 bg-purple-50/30' : 'border-gray-200'">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-bold"
              :class="gradeName(gi) === 'A賞' ? 'text-indigo-700' : gradeName(gi) === 'B賞' ? 'text-purple-700' : 'text-gray-700'">
              賞別 {{ gi + 1 }} - {{ gradeName(gi) }}
            </span>
            <div class="flex gap-2">
              <button type="button" @click="addItem(gi)" class="text-xs text-indigo-500">+ 子獎項</button>
              <button v-if="editForm.grades.length > 2" type="button" @click="removeGrade(gi)" class="text-xs text-red-500">刪除此賞</button>
            </div>
          </div>
          <div class="space-y-2 ml-2">
            <div v-for="(item, ii) in g.prize_items" :key="ii"
              class="bg-white border border-gray-200 rounded-lg p-3"
            >
              <div class="flex items-center justify-between mb-1">
                <span class="text-xs text-gray-500">子獎項 #{{ ii + 1 }}</span>
                <button v-if="g.prize_items.length > 1" type="button" @click="removeItem(gi, ii)" class="text-xs text-red-400">刪除</button>
              </div>
              <div class="grid grid-cols-2 md:grid-cols-5 gap-2">
                <div>
                  <label class="block text-xs text-gray-500 mb-1">品名</label>
                  <input v-model="item.name" class="w-full border rounded-lg px-2 py-1.5 text-sm" />
                </div>
                <div>
                  <label class="block text-xs text-gray-500 mb-1">類別</label>
                  <div class="flex gap-1">
                    <select v-if="!customCategoryItems[gi + '-' + ii]" v-model="item.category" class="flex-1 border rounded-lg px-2 py-1.5 text-sm" @change="onCategorySelect($event, gi, ii)">
                      <option v-for="cat in categoryPresets" :key="cat" :value="cat">{{ cat }}</option>
                      <option value="__custom__">自訂...</option>
                    </select>
                    <input v-else v-model="item.category" class="flex-1 border rounded-lg px-2 py-1.5 text-sm" placeholder="自訂類別" />
                    <button type="button" @click="customCategoryItems[gi + '-' + ii] = !customCategoryItems[gi + '-' + ii]" class="text-xs text-indigo-500 whitespace-nowrap">
                      {{ customCategoryItems[gi + '-' + ii] ? '預設' : '自訂' }}
                    </button>
                  </div>
                </div>
                <div>
                  <label class="block text-xs text-gray-500 mb-1">庫存</label>
                  <input v-model.number="item.stock" type="number" min="1" class="w-full border rounded-lg px-2 py-1.5 text-sm" />
                </div>
                <div>
                  <label class="block text-xs text-gray-500 mb-1">成本</label>
                  <input v-model.number="item.cost" type="number" class="w-full border rounded-lg px-2 py-1.5 text-sm" />
                </div>
                <div>
                  <label class="block text-xs text-gray-500 mb-1">市價</label>
                  <input v-model.number="item.market_price" type="number" class="w-full border rounded-lg px-2 py-1.5 text-sm" />
                </div>
                <div class="col-span-2 md:col-span-5">
                  <ImageUploader v-model="item.image_url" label="獎品圖片（可選）" />
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="mt-3 space-y-1 text-sm">
          <p class="text-gray-500">獎品總庫存：<strong>{{ stockTotal }}</strong></p>
          <div class="flex items-center gap-3">
            <label class="text-gray-500 whitespace-nowrap">總抽數設定：</label>
            <input v-model.number="editForm.total_tickets" type="number" min="1" placeholder="留空則等同獎品總庫存" class="w-40 border rounded-lg px-2 py-1.5" />
            <span v-if="editForm.total_tickets" class="text-gray-500">→ <strong class="text-gray-900">{{ effectiveTotalTickets }}</strong> 張</span>
          </div>
          <p v-if="ticketWarning" class="bg-amber-50 text-amber-700 p-3 rounded-lg">{{ ticketWarning }}</p>
        </div>
      </div>

      <!-- Payment Methods -->
      <div class="border-t pt-4 mb-4">
        <h3 class="text-md font-semibold text-gray-900 mb-3">付款方式</h3>
        <div class="flex items-center gap-6">
          <label class="flex items-center gap-2 text-sm text-gray-700">
            <input v-model="editForm.payment_methods" value="onsite" type="checkbox" class="rounded" />
            現場付款
          </label>
          <label class="flex items-center gap-2 text-sm text-gray-700">
            <input v-model="editForm.payment_methods" value="linepay" type="checkbox" class="rounded" />
            LinePay
          </label>
          <label class="flex items-center gap-2 text-sm text-gray-700">
            <input v-model="editForm.payment_methods" value="draw_now" type="checkbox" class="rounded" />
            抽就對了（免付款）
          </label>
        </div>
      </div>

      <!-- Shipping Settings -->
      <div class="border-t pt-4 mb-6">
        <h3 class="text-md font-semibold text-gray-900 mb-3">物流設定</h3>
        <div class="flex items-center gap-2 mb-4">
          <input v-model="editForm.allow_shipping" type="checkbox" id="edit_allow_shipping" class="rounded" />
          <label for="edit_allow_shipping" class="text-sm text-gray-700">允許寄送</label>
        </div>
        <div v-if="editForm.allow_shipping" class="grid grid-cols-2 gap-4 ml-6">
          <div>
            <label class="block text-sm text-gray-500 mb-1">運費</label>
            <input v-model.number="editForm.shipping_fee" type="number" class="w-full border rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm text-gray-500 mb-1">免運門檻</label>
            <input v-model.number="editForm.free_shipping_threshold" type="number" class="w-full border rounded-lg px-3 py-2 text-sm" />
          </div>
        </div>
      </div>

      <div class="flex gap-3">
        <button @click="saveEdit" :disabled="saving" class="bg-indigo-600 text-white px-6 py-2.5 rounded-lg font-semibold text-sm hover:bg-indigo-700 disabled:opacity-50">
          {{ saving ? '儲存中...' : '儲存變更' }}
        </button>
        <button @click="cancelEdit" class="bg-gray-100 text-gray-700 px-6 py-2.5 rounded-lg font-semibold text-sm hover:bg-gray-200">取消</button>
      </div>
    </div>

    <!-- View Mode: Prize Grades Table -->
    <div v-if="!editing" class="bg-white rounded-xl shadow-sm border p-6 mb-6">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">獎項配置</h2>
      <div v-for="g in pool.prize_grades" :key="g.id" class="mb-4 last:mb-0">
        <div class="flex items-center gap-2 mb-2">
          <span class="text-sm font-bold text-gray-900">{{ g.grade_name }}</span>
          <span class="text-xs text-gray-400">剩餘 {{ g.remaining_stock }}</span>
        </div>
        <table class="w-full text-sm">
          <thead class="bg-gray-50 border-b">
            <tr>
              <th class="text-left px-3 py-1.5 font-medium text-gray-600">品名</th>
              <th class="text-left px-3 py-1.5 font-medium text-gray-600">類別</th>
              <th class="text-left px-3 py-1.5 font-medium text-gray-600">圖片</th>
              <th class="text-right px-3 py-1.5 font-medium text-gray-600">庫存</th>
              <th class="text-right px-3 py-1.5 font-medium text-gray-600">成本</th>
              <th class="text-right px-3 py-1.5 font-medium text-gray-600">市價</th>
            </tr>
          </thead>
          <tbody class="divide-y">
            <tr v-for="item in g.prize_items" :key="item.id">
              <td class="px-3 py-1.5 text-gray-800">{{ item.name }}</td>
              <td class="px-3 py-1.5 text-gray-500">{{ item.category }}</td>
              <td class="px-3 py-1.5">
                <img v-if="item.image_url" :src="item.image_url" class="w-16 h-16 object-cover rounded" />
              </td>
              <td class="px-3 py-1.5 text-right">{{ item.remaining_stock }} / {{ item.stock }}</td>
              <td class="px-3 py-1.5 text-right">${{ item.cost }}</td>
              <td class="px-3 py-1.5 text-right">${{ item.market_price }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Actions -->
    <div v-if="!editing" class="flex gap-3">
      <button
        v-if="isDraft"
        @click="publishPool"
        :disabled="publishing"
        class="bg-green-600 text-white px-6 py-2.5 rounded-lg font-semibold text-sm hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <span v-if="publishing" class="inline-flex items-center gap-2">
          <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
          上架中...
        </span>
        <span v-else>上架並洗牌</span>
      </button>
      <button
        v-if="pool.status === 'published'"
        @click="shufflePool"
        :disabled="shuffling"
        class="bg-orange-600 text-white px-6 py-2.5 rounded-lg font-semibold text-sm hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <span v-if="shuffling" class="inline-flex items-center gap-2">
          <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
          洗牌中...
        </span>
        <span v-else>重新洗牌</span>
      </button>
    </div>
  </div>
</template>
