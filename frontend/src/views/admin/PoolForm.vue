<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
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

const categoryPresets = ['卡牌', '公仔', '吊飾', '徽章', '立牌', '海報', '其他']
const customCategoryItems = ref({})

const GRADE_LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

function gradeName(index) {
  return GRADE_LETTERS[index] + '賞'
}

const form = ref({
  name: '',
  banner_image: '',
  single_price: 300,
  allow_shipping: true,
  shipping_fee: 60,
  free_shipping_threshold: 2000,
  payment_methods: ['onsite', 'linepay', 'draw_now'],
  grades: [
    { prize_items: [{ name: '', stock: 1, category: '卡牌', cost: 300, market_price: 1200, image_url: '' }] },
    { prize_items: [{ name: '', stock: 8, category: '卡牌', cost: 150, market_price: 600, image_url: '' }] },
  ],
})

const error = ref('')

const totalTickets = computed(() =>
  form.value.grades.reduce((s, g) => s + g.prize_items.reduce((si, item) => si + (Number(item.stock) || 0), 0), 0)
)

const distributionValid = computed(() => {
  const warnings = []
  for (let i = 0; i < form.value.grades.length; i++) {
    const g = form.value.grades[i]
    for (const item of g.prize_items) {
      if (Number(item.stock) > 999) {
        warnings.push(`${gradeName(i)} - ${item.name || '未命名'} 庫存設定過高`)
      }
    }
  }
  return warnings
})

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
  for (let i = 0; i < form.value.grades.length; i++) {
    const items = form.value.grades[i].prize_items
    if (items.length === 0) {
      error.value = `${gradeName(i)} 至少需要一個子獎項`
      return
    }
    for (const item of items) {
      if (!item.name) {
        error.value = `${gradeName(i)} 下有未填寫名稱的子獎項`
        return
      }
    }
  }
  try {
    const payload = {
      name: form.value.name,
      banner_image: form.value.banner_image || null,
      single_price: form.value.single_price,
      payment_methods: form.value.payment_methods.join(','),
      allow_shipping: form.value.allow_shipping,
      shipping_fee: form.value.shipping_fee,
      free_shipping_threshold: form.value.free_shipping_threshold,
      prize_grades: form.value.grades.map((g, i) => ({
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
    const res = await api.post('/pools', payload)
    router.push(`/admin/pools/${res.data.id}`)
  } catch (e) {
    error.value = formatError(e)
  }
}

function addGrade() {
  form.value.grades.push({ prize_items: [{ name: '', stock: 1, category: '卡牌', cost: 0, market_price: 0, image_url: '' }] })
}

function removeGrade(i) {
  form.value.grades.splice(i, 1)
}

function addItem(gradeIndex) {
  form.value.grades[gradeIndex].prize_items.push({ name: '', stock: 1, category: '卡牌', cost: 0, market_price: 0, image_url: '' })
}

function removeItem(gradeIndex, itemIndex) {
  form.value.grades[gradeIndex].prize_items.splice(itemIndex, 1)
}

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
  <div v-else class="max-w-4xl mx-auto">
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
        </div>
      </div>

      <div class="bg-white rounded-xl shadow-sm border p-6">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold text-gray-900">獎項設定</h2>
          <button type="button" @click="addGrade" class="text-sm text-indigo-600 hover:text-indigo-800">+ 新增賞別</button>
        </div>

        <div v-if="distributionValid.length" class="bg-amber-50 text-amber-700 text-sm p-3 rounded-lg mb-4">
          <div v-for="w in distributionValid" :key="w">{{ w }}</div>
        </div>

        <div class="space-y-4">
          <div v-for="(g, gi) in form.grades" :key="gi" class="border rounded-xl p-5"
            :class="gradeName(gi) === 'A賞' ? 'border-indigo-300 bg-indigo-50/30' : gradeName(gi) === 'B賞' ? 'border-purple-300 bg-purple-50/30' : 'border-gray-200'"
          >
            <div class="flex items-center justify-between mb-3">
              <span class="text-sm font-bold" :class="gradeName(gi) === 'A賞' ? 'text-indigo-700' : gradeName(gi) === 'B賞' ? 'text-purple-700' : 'text-gray-700'">
                {{ gradeName(gi) }}
              </span>
              <div class="flex gap-2">
                <button type="button" @click="addItem(gi)" class="text-xs text-indigo-500 hover:text-indigo-700">+ 子獎項</button>
                <button v-if="form.grades.length > 2" type="button" @click="removeGrade(gi)" class="text-xs text-red-500 hover:text-red-700">刪除此賞</button>
              </div>
            </div>

            <div class="space-y-3">
              <div v-for="(item, ii) in g.prize_items" :key="ii"
                class="bg-white border border-gray-200 rounded-lg p-3"
              >
                <div class="flex items-center justify-between mb-2">
                  <span class="text-xs font-medium text-gray-500">子獎項 #{{ ii + 1 }}</span>
                  <button v-if="g.prize_items.length > 1" type="button" @click="removeItem(gi, ii)" class="text-xs text-red-400 hover:text-red-600">刪除</button>
                </div>
                <div class="grid grid-cols-2 md:grid-cols-5 gap-2">
                  <div>
                    <label class="block text-xs text-gray-500 mb-1">品名</label>
                    <input v-model="item.name" required class="w-full border rounded-lg px-2 py-1.5 text-sm" placeholder="品名" />
                  </div>
                  <div>
                    <label class="block text-xs text-gray-500 mb-1">類別</label>
                    <div class="flex gap-1">
                      <select v-if="!customCategoryItems[gi + '-' + ii]" v-model="item.category" class="flex-1 border rounded-lg px-2 py-1.5 text-sm">
                        <option v-for="cat in categoryPresets" :key="cat" :value="cat">{{ cat }}</option>
                        <option value="__custom__">自訂...</option>
                      </select>
                      <input v-else v-model="item.category" class="flex-1 border rounded-lg px-2 py-1.5 text-sm" placeholder="自訂類別" />
                      <button type="button" @click="customCategoryItems[gi + '-' + ii] = !customCategoryItems[gi + '-' + ii]; if (customCategoryItems[gi + '-' + ii]) item.category = ''" class="text-xs text-indigo-500 whitespace-nowrap">
                        {{ customCategoryItems[gi + '-' + ii] ? '預設' : '自訂' }}
                      </button>
                    </div>
                  </div>
                  <div>
                    <label class="block text-xs text-gray-500 mb-1">庫存</label>
                    <input v-model.number="item.stock" type="number" required min="1" class="w-full border rounded-lg px-2 py-1.5 text-sm" />
                  </div>
                  <div>
                    <label class="block text-xs text-gray-500 mb-1">成本</label>
                    <input v-model.number="item.cost" type="number" class="w-full border rounded-lg px-2 py-1.5 text-sm" placeholder="$" />
                  </div>
                  <div>
                    <label class="block text-xs text-gray-500 mb-1">市價</label>
                    <input v-model.number="item.market_price" type="number" class="w-full border rounded-lg px-2 py-1.5 text-sm" placeholder="$" />
                  </div>
                  <div class="col-span-2 md:col-span-5">
                    <ImageUploader v-model="item.image_url" label="獎品圖片（可選）" />
                  </div>
                </div>
              </div>
            </div>

            <div class="mt-2 text-xs text-gray-400">
              此賞小計：{{ g.prize_items.reduce((s, item) => s + (Number(item.stock) || 0), 0) }} 張
            </div>
          </div>
        </div>

        <div class="mt-4 flex items-center gap-4 text-sm">
          <span class="text-gray-500">總抽數：<strong class="text-gray-900">{{ totalTickets }}</strong></span>
          <span v-if="totalTickets === 0" class="text-red-500">請設定至少 1 張獎券</span>
        </div>
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
          <label class="flex items-center gap-2 text-sm text-gray-700">
            <input v-model="form.payment_methods" value="draw_now" type="checkbox" class="rounded" />
            抽就對了（免付款）
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
