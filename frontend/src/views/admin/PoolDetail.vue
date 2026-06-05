<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../../api'

const route = useRoute()
const router = useRouter()
const pool = ref(null)
const loading = ref(true)
let idleStart = null
const IDLE_THRESHOLD = 30000

async function verifyAuth() {
  try {
    await api.get('/auth/me')
    const res = await api.get(`/pools/${route.params.id}`)
    pool.value = res.data
  } catch (_) {
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

const editForm = ref({
  name: '',
  banner_image: '',
  single_price: 0,
  allow_shipping: true,
  shipping_fee: 0,
  free_shipping_threshold: 0,
  last_one_prize_name: '',
  last_one_prize_image: '',
  payment_methods: [],
  prize_grades: [],
})

const error = ref('')

onMounted(() => {
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

function startEdit() {
  const p = pool.value
  editForm.value = {
    name: p.name,
    banner_image: p.banner_image || '',
    single_price: p.single_price,
    allow_shipping: p.allow_shipping,
    shipping_fee: p.shipping_fee,
    free_shipping_threshold: p.free_shipping_threshold,
    last_one_prize_name: p.last_one_prize_name || '',
    last_one_prize_image: p.last_one_prize_image || '',
    payment_methods: (p.payment_methods || '').split(',').filter(Boolean),
    prize_grades: p.prize_grades.map(g => ({
      id: g.id,
      grade_name: g.grade_name,
      item_name: g.item_name,
      item_type: g.item_type,
      initial_stock: g.initial_stock,
      cost: g.cost,
      market_price: g.market_price,
      image_url: g.image_url || '',
      sort_order: g.sort_order,
    })),
  }
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
      const payload = { ...editForm.value, payment_methods: editForm.value.payment_methods.join(',') }
      const res = await api.patch(`/pools/${route.params.id}`, payload)
      pool.value = res.data
    } else {
      const poolPayload = {
        name: editForm.value.name,
        banner_image: editForm.value.banner_image || null,
        single_price: editForm.value.single_price,
        allow_shipping: editForm.value.allow_shipping,
        shipping_fee: editForm.value.shipping_fee,
        free_shipping_threshold: editForm.value.free_shipping_threshold,
        last_one_prize_name: editForm.value.last_one_prize_name || null,
        last_one_prize_image: editForm.value.last_one_prize_image || null,
        payment_methods: editForm.value.payment_methods.join(','),
      }
      const gradePayload = editForm.value.prize_grades.map(g => ({
        id: g.id,
        grade_name: g.grade_name,
        item_name: g.item_name,
        item_type: g.item_type,
        image_url: g.image_url || null,
        cost: g.cost,
        market_price: g.market_price,
        sort_order: g.sort_order,
      }))
      const [poolRes] = await Promise.all([
        api.patch(`/pools/${route.params.id}`, poolPayload),
        api.patch(`/pools/${route.params.id}/grades`, gradePayload),
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
  if (!confirm('確定要刪除此獎池？此操作不可恢復。')) return
  try {
    await api.delete(`/pools/${route.params.id}`)
    router.push('/admin')
  } catch (e) {
    alert(e.response?.data?.detail || '刪除失敗')
  }
}

async function publishPool() {
  if (!confirm('確定要上架此獎池？將自動進行洗牌並開放抽獎。')) return
  try {
    await api.post(`/pools/${route.params.id}/publish`)
    const res = await api.get(`/pools/${route.params.id}`)
    pool.value = res.data
  } catch (e) {
    alert(e.response?.data?.detail || '上架失敗')
  }
}

async function shufflePool() {
  if (!confirm('確定要重新洗牌？這將重置所有抽獎券。')) return
  try {
    await api.post(`/pools/${route.params.id}/shuffle`)
    const res = await api.get(`/pools/${route.params.id}`)
    pool.value = res.data
  } catch (e) {
    alert(e.response?.data?.detail || '洗牌失敗')
  }
}

function addGrade() {
  const idx = editForm.value.prize_grades.length
  editForm.value.prize_grades.push({
    grade_name: '',
    item_name: '',
    item_type: '其他',
    initial_stock: 1,
    cost: 0,
    market_price: 0,
    image_url: '',
    sort_order: idx,
  })
}

function removeGrade(i) {
  if (editForm.value.prize_grades.length <= 2) return
  editForm.value.prize_grades.splice(i, 1)
}

const totalTickets = computed(() =>
  editForm.value.prize_grades.reduce((s, g) => s + (Number(g.initial_stock) || 0), 0)
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
          class="bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-red-700"
        >
          刪除
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
          <label class="block text-sm font-medium text-gray-700 mb-1">橫幅圖片網址</label>
          <input v-model="editForm.banner_image" class="w-full border rounded-lg px-3 py-2 text-sm" placeholder="https://..." />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">單抽售價</label>
          <input v-model.number="editForm.single_price" type="number" class="w-full border rounded-lg px-3 py-2 text-sm" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">最後賞名稱</label>
          <input v-model="editForm.last_one_prize_name" class="w-full border rounded-lg px-3 py-2 text-sm" placeholder="例如：最後賞 大布偶" />
        </div>
        <div class="col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-1">最後賞圖片</label>
          <input v-model="editForm.last_one_prize_image" class="w-full border rounded-lg px-3 py-2 text-sm" placeholder="https://..." />
        </div>
      </div>

      <!-- Prize Grades Edit -->
      <div class="border-t pt-4 mb-4">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-md font-semibold text-gray-900">獎項設定</h3>
          <button type="button" @click="addGrade" class="text-sm text-indigo-600 hover:text-indigo-800">+ 新增獎項</button>
        </div>
        <div v-for="(g, i) in editForm.prize_grades" :key="i" class="border rounded-lg p-4 mb-3">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-medium text-gray-700">獎項 {{ i + 1 }}</span>
            <button v-if="editForm.prize_grades.length > 2" type="button" @click="removeGrade(i)" class="text-xs text-red-500">刪除</button>
          </div>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <label class="block text-xs text-gray-500 mb-1">獎項等級</label>
              <input v-model="g.grade_name" class="w-full border rounded-lg px-2 py-1.5 text-sm" placeholder="A賞" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">獎品名稱</label>
              <input v-model="g.item_name" class="w-full border rounded-lg px-2 py-1.5 text-sm" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">類型</label>
              <select v-model="g.item_type" class="w-full border rounded-lg px-2 py-1.5 text-sm">
                <option>公仔</option>
                <option>吊飾</option>
                <option>徽章</option>
                <option>立牌</option>
                <option>海報</option>
                <option>其他</option>
              </select>
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">庫存</label>
              <input v-model.number="g.initial_stock" type="number" min="1" class="w-full border rounded-lg px-2 py-1.5 text-sm" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">成本</label>
              <input v-model.number="g.cost" type="number" class="w-full border rounded-lg px-2 py-1.5 text-sm" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">市價</label>
              <input v-model.number="g.market_price" type="number" class="w-full border rounded-lg px-2 py-1.5 text-sm" />
            </div>
            <div class="col-span-2 md:col-span-4">
              <label class="block text-xs text-gray-500 mb-1">獎賞圖片網址（可選）</label>
              <input v-model="g.image_url" class="w-full border rounded-lg px-2 py-1.5 text-sm" placeholder="https://..." />
            </div>
          </div>
        </div>
        <p class="text-sm text-gray-500 mt-2">總抽數：<strong>{{ totalTickets }}</strong></p>
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
      <table class="w-full text-sm">
        <thead class="bg-gray-50 border-b">
          <tr>
            <th class="text-left px-3 py-2 font-medium text-gray-600">等級</th>
            <th class="text-left px-3 py-2 font-medium text-gray-600">品名</th>
            <th class="text-left px-3 py-2 font-medium text-gray-600">圖片</th>
            <th class="text-left px-3 py-2 font-medium text-gray-600">類型</th>
            <th class="text-right px-3 py-2 font-medium text-gray-600">庫存</th>
            <th class="text-right px-3 py-2 font-medium text-gray-600">成本</th>
            <th class="text-right px-3 py-2 font-medium text-gray-600">市價</th>
          </tr>
        </thead>
        <tbody class="divide-y">
          <tr v-for="g in pool.prize_grades" :key="g.id">
            <td class="px-3 py-2 font-medium">{{ g.grade_name }}</td>
            <td class="px-3 py-2 text-gray-600">{{ g.item_name }}</td>
            <td class="px-3 py-2">
              <img v-if="g.image_url" :src="g.image_url" class="w-24 h-24 object-cover rounded" />
            </td>
            <td class="px-3 py-2 text-gray-500">{{ g.item_type }}</td>
            <td class="px-3 py-2 text-right">{{ g.remaining_stock }} / {{ g.initial_stock }}</td>
            <td class="px-3 py-2 text-right">${{ g.cost }}</td>
            <td class="px-3 py-2 text-right">${{ g.market_price }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Actions -->
    <div v-if="!editing" class="flex gap-3">
      <button
        v-if="isDraft"
        @click="publishPool"
        class="bg-green-600 text-white px-6 py-2.5 rounded-lg font-semibold text-sm hover:bg-green-700"
      >
        上架並洗牌
      </button>
      <button
        v-if="pool.status === 'published'"
        @click="shufflePool"
        class="bg-orange-600 text-white px-6 py-2.5 rounded-lg font-semibold text-sm hover:bg-orange-700"
      >
        重新洗牌
      </button>
    </div>
  </div>
</template>
