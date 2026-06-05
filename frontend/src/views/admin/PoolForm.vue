<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api'
import ImageUploader from '../../components/ImageUploader.vue'

const router = useRouter()

const loading = ref(false)
let idleStart = null
const IDLE_THRESHOLD = 30000

async function verifyAuth() {
  try {
    await api.get('/auth/me')
  } catch (_) {
    router.push('/admin/login')
  } finally {
    loading.value = false
  }
}

function onPageShow(event) {
  if (event.persisted) {
    loading.value = true
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
      verifyAuth()
    }
  }
}

const form = ref({
  name: '',
  banner_image: '',
  single_price: 300,
  allow_shipping: true,
  shipping_fee: 60,
  free_shipping_threshold: 2000,
  last_one_prize_name: '',
  last_one_prize_image: '',
  payment_methods: ['onsite', 'linepay'],
  prize_grades: [
    { grade_name: 'A賞', item_name: '', item_type: '公仔', initial_stock: 2, cost: 300, market_price: 1200, image_url: '', sort_order: 0 },
    { grade_name: 'B賞', item_name: '', item_type: '吊飾', initial_stock: 8, cost: 150, market_price: 600, image_url: '', sort_order: 1 },
  ],
})

const error = ref('')

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
  return e.message || '建立失敗'
}

async function submit() {
  error.value = ''
  if (form.value.payment_methods.length === 0) {
    error.value = '至少需要選擇一種付款方式'
    return
  }
  try {
    const payload = { ...form.value, payment_methods: form.value.payment_methods.join(',') }
    const res = await api.post('/pools', payload)
    router.push(`/admin/pools/${res.data.id}`)
  } catch (e) {
    error.value = formatError(e)
  }
}

function addGrade() {
  const idx = form.value.prize_grades.length
  form.value.prize_grades.push({
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
  form.value.prize_grades.splice(i, 1)
}

const totalTickets = ref(0)

onMounted(() => {
  window.addEventListener('pageshow', onPageShow)
  document.addEventListener('visibilitychange', onVisibilityChange)
})

onUnmounted(() => {
  window.removeEventListener('pageshow', onPageShow)
  document.removeEventListener('visibilitychange', onVisibilityChange)
})
</script>

<template>
  <div v-if="loading" class="text-gray-500 text-center py-12">載入中...</div>
  <div v-else class="max-w-3xl mx-auto">
    <h1 class="text-2xl font-bold text-gray-900 mb-6">新增獎池</h1>
    <div v-if="error" class="bg-red-50 text-red-600 text-sm p-3 rounded-lg mb-4">{{ error }}</div>
    <form @submit.prevent="submit" class="space-y-6">
      <div class="bg-white rounded-xl shadow-sm border p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">基本資訊</h2>
        <div class="grid grid-cols-2 gap-4">
          <div class="col-span-2">
            <label class="block text-sm font-medium text-gray-700 mb-1">獎池名稱</label>
            <input v-model="form.name" required class="w-full border rounded-lg px-3 py-2 text-sm" />
          </div>
          <div class="col-span-2">
            <ImageUploader v-model="form.banner_image" label="橫幅圖片" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">單抽售價</label>
            <input v-model.number="form.single_price" type="number" required class="w-full border rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">最後賞名稱</label>
            <input v-model="form.last_one_prize_name" class="w-full border rounded-lg px-3 py-2 text-sm" placeholder="例如：最後賞 大布偶" />
          </div>
        </div>
      </div>

      <div class="bg-white rounded-xl shadow-sm border p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold text-gray-900">獎項設定</h2>
          <button type="button" @click="addGrade" class="text-sm text-indigo-600 hover:text-indigo-800">+ 新增獎項</button>
        </div>
        <div v-for="(g, i) in form.prize_grades" :key="i" class="border rounded-lg p-4 mb-3">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-medium text-gray-700">獎項 {{ i + 1 }}</span>
            <button v-if="form.prize_grades.length > 2" type="button" @click="removeGrade(i)" class="text-xs text-red-500">刪除</button>
          </div>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <label class="block text-xs text-gray-500 mb-1">獎項等級</label>
              <input v-model="g.grade_name" required class="w-full border rounded-lg px-2 py-1.5 text-sm" placeholder="A賞" />
            </div>
            <div>
              <label class="block text-xs text-gray-500 mb-1">獎品名稱</label>
              <input v-model="g.item_name" required class="w-full border rounded-lg px-2 py-1.5 text-sm" />
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
              <input v-model.number="g.initial_stock" type="number" required min="1" class="w-full border rounded-lg px-2 py-1.5 text-sm" />
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
              <ImageUploader v-model="g.image_url" label="獎賞圖片（可選）" />
            </div>
          </div>
        </div>
        <p class="text-sm text-gray-500 mt-2">總抽數：<strong>{{ form.prize_grades.reduce((s, g) => s + g.initial_stock, 0) }}</strong></p>
      </div>

      <div class="bg-white rounded-xl shadow-sm border p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">付款方式</h2>
        <div class="flex items-center gap-6">
          <label class="flex items-center gap-2 text-sm text-gray-700">
            <input v-model="form.payment_methods" value="onsite" type="checkbox" class="rounded" />
            現場付款
          </label>
          <label class="flex items-center gap-2 text-sm text-gray-700">
            <input v-model="form.payment_methods" value="linepay" type="checkbox" class="rounded" />
            LinePay
          </label>
        </div>
      </div>

      <div class="bg-white rounded-xl shadow-sm border p-6">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">物流設定</h2>
        <div class="flex items-center gap-2 mb-4">
          <input v-model="form.allow_shipping" type="checkbox" id="allow_shipping" class="rounded" />
          <label for="allow_shipping" class="text-sm text-gray-700">允許寄送</label>
        </div>
        <div v-if="form.allow_shipping" class="grid grid-cols-2 gap-4 ml-6">
          <div>
            <label class="block text-sm text-gray-500 mb-1">運費</label>
            <input v-model.number="form.shipping_fee" type="number" class="w-full border rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-sm text-gray-500 mb-1">免運門檻</label>
            <input v-model.number="form.free_shipping_threshold" type="number" class="w-full border rounded-lg px-3 py-2 text-sm" />
          </div>
        </div>
      </div>

      <button type="submit" class="w-full bg-indigo-600 text-white py-3 rounded-lg font-semibold hover:bg-indigo-700">建立獎池</button>
    </form>
  </div>
</template>
