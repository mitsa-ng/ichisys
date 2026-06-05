<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../api'

const route = useRoute()
const pool = ref(null)
const tickets = ref([])
const selectedNumbers = ref([])
const loading = ref(true)
const drawing = ref(false)
const showPayment = ref(false)
const selectedMethod = ref('onsite')
const payment = ref(null)
const drawResult = ref(null)
const error = ref('')
const waitingPayment = ref(false)
const userId = ref(localStorage.getItem('user_id') || 'user_' + Math.random().toString(36).slice(2, 8))
let eventSource = null

if (!localStorage.getItem('user_id')) {
  localStorage.setItem('user_id', userId.value)
}

async function loadPool() {
  try {
    const [poolRes, ticketRes] = await Promise.all([
      api.get(`/pools/${route.params.id}`),
      api.get(`/pools/${route.params.id}/tickets`),
    ])
    pool.value = poolRes.data
    tickets.value = ticketRes.data
    const methods = (poolRes.data.payment_methods || '').split(',').filter(Boolean)
    if (methods.length > 0) selectedMethod.value = methods[0]
  } catch (_) {}
}

const remaining = computed(() => pool.value?.remaining_tickets ?? 0)
const total = computed(() => pool.value?.total_tickets ?? 0)
const singlePrice = computed(() => pool.value?.single_price ?? 0)
const packagePrice = computed(() => remaining.value * singlePrice.value)
const totalPrice = computed(() => selectedNumbers.value.length * singlePrice.value)
const grades = computed(() => pool.value?.prize_grades ?? [])
const paymentMethods = computed(() => (pool.value?.payment_methods || '').split(',').filter(Boolean))

const methodLabels = { onsite: '現場付款', linepay: 'LinePay', draw_now: '抽就對了' }

onMounted(async () => {
  await loadPool()
  loading.value = false

  eventSource = new EventSource('/api/events')
  eventSource.onmessage = (e) => {
    if (!e.data) return
    try {
      const { event, data } = JSON.parse(e.data)
      if (event === 'payment_confirmed' && data.payment_id === payment.value?.id && data.user_id === userId.value) {
        doDraw()
      }
      if ((event === 'pool_update' && data.pool_id === route.params.id) || event === 'draw_result') {
        loadPool()
      }
    } catch (_) {}
  }
})

onUnmounted(() => {
  if (eventSource) eventSource.close()
})

function toggleNumber(n) {
  const idx = selectedNumbers.value.indexOf(n)
  if (idx >= 0) {
    selectedNumbers.value.splice(idx, 1)
  } else if (!isDrawn(n)) {
    selectedNumbers.value.push(n)
  }
}

function selectAll() {
  selectedNumbers.value = tickets.value.filter(t => !t.is_drawn).map(t => t.serial_number)
}

function clearSelection() {
  selectedNumbers.value = []
}

function isDrawn(n) {
  const ticket = tickets.value.find(t => t.serial_number === n)
  return ticket?.is_drawn ?? false
}

function getPrizeName(n) {
  const ticket = tickets.value.find(t => t.serial_number === n)
  return ticket?.prize_grade_name ?? ''
}

function openPayment() {
  if (selectedNumbers.value.length === 0) return
  error.value = ''
  showPayment.value = true
  drawResult.value = null
  payment.value = null
  waitingPayment.value = false
}

function cancelPayment() {
  showPayment.value = false
  payment.value = null
  error.value = ''
  waitingPayment.value = false
}

async function doDraw() {
  try {
    const res = await api.post(`/pools/${route.params.id}/draw`, {
      user_id: userId.value,
      serial_numbers: selectedNumbers.value,
      payment_id: payment.value.id,
    })
    drawResult.value = res.data.results
    selectedNumbers.value = []
    showPayment.value = false
    payment.value = null
    waitingPayment.value = false

    await loadPool()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '抽獎失敗'
  }
}

async function confirmPayment() {
  error.value = ''
  drawing.value = true
  try {
    const payRes = await api.post('/payments', {
      pool_id: route.params.id,
      user_id: userId.value,
      serial_numbers: selectedNumbers.value,
      method: selectedMethod.value,
    })
    payment.value = payRes.data

    if (selectedMethod.value === 'linepay') {
      await api.post(`/payments/${payRes.data.id}/confirm`)
      const confirmRes = await api.get(`/payments/${payRes.data.id}`)
      payment.value = confirmRes.data
      drawing.value = false
      await doDraw()
    }

    if (selectedMethod.value === 'draw_now') {
      drawing.value = false
      await doDraw()
    }

    if (selectedMethod.value === 'onsite') {
      drawing.value = false
      waitingPayment.value = true
    }
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '付款失敗'
    drawing.value = false
  }
}

function closeResult() {
  drawResult.value = null
}
</script>

<template>
  <div v-if="loading" class="text-gray-500">載入中...</div>
  <div v-else-if="pool">
    <div v-if="pool.banner_image" class="h-48 rounded-xl overflow-hidden mb-6">
      <img :src="pool.banner_image" :alt="pool.name" class="w-full h-full object-cover" />
    </div>

    <div class="bg-white rounded-xl shadow-sm border p-6 mb-6">
      <h1 class="text-2xl font-bold text-gray-900">{{ pool.name }}</h1>

      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
        <div class="bg-indigo-50 rounded-lg p-3 text-center">
          <div class="text-sm text-gray-500">單抽價格</div>
          <div class="text-lg font-bold text-indigo-600">${{ singlePrice }}</div>
        </div>
        <div class="bg-orange-50 rounded-lg p-3 text-center">
          <div class="text-sm text-gray-500">剩餘 / 總抽數</div>
          <div class="text-lg font-bold text-orange-600">{{ remaining }} / {{ total }}</div>
        </div>
        <div class="bg-green-50 rounded-lg p-3 text-center">
          <div class="text-sm text-gray-500">包牌價</div>
          <div class="text-lg font-bold text-green-600">${{ packagePrice.toLocaleString() }}</div>
        </div>
        <div class="bg-gray-50 rounded-lg p-3 text-center">
          <div class="text-sm text-gray-500">已選號碼</div>
          <div class="text-lg font-bold text-gray-600">{{ selectedNumbers.length }}</div>
        </div>
      </div>
    </div>

    <div class="bg-white rounded-xl shadow-sm border p-6 mb-6">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">獎項配置</h2>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div v-for="g in grades" :key="g.id" class="border rounded-lg p-3 text-center">
          <div class="text-sm font-bold text-gray-900 mb-1">{{ g.grade_name }}</div>
          <div class="text-xs text-gray-500">{{ g.item_name }}</div>
          <div class="text-xs text-gray-400 mt-1">殘 {{ g.remaining_stock }} / 共 {{ g.initial_stock }}</div>
        </div>
      </div>
    </div>

    <div class="bg-white rounded-xl shadow-sm border p-6 mb-6">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-semibold text-gray-900">選號區</h2>
        <div class="flex gap-2">
          <button @click="selectAll" class="text-xs px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200">包牌</button>
          <button @click="clearSelection" class="text-xs px-3 py-1.5 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200">清除</button>
        </div>
      </div>
      <div class="grid grid-cols-8 sm:grid-cols-10 gap-2">
        <button
          v-for="t in tickets"
          :key="t.serial_number"
          @click="toggleNumber(t.serial_number)"
          :disabled="t.is_drawn || showPayment"
          :class="[
            'aspect-square rounded-lg text-xs font-medium transition border',
            t.is_drawn
              ? 'bg-gray-100 text-gray-300 cursor-not-allowed border-gray-200 line-through'
              : selectedNumbers.includes(t.serial_number)
                ? 'bg-indigo-500 text-white border-indigo-500'
                : 'bg-white text-gray-700 border-gray-300 hover:border-indigo-400 cursor-pointer',
          ]"
        >
          <div>{{ t.serial_number }}</div>
          <div v-if="t.is_drawn" class="text-[9px] truncate">{{ getPrizeName(t.serial_number) }}</div>
        </button>
      </div>
    </div>

    <!-- Payment Modal -->
    <div v-if="showPayment" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-2xl shadow-xl max-w-md w-full p-6">
        <div v-if="!waitingPayment">
          <h3 class="text-lg font-bold text-gray-900 mb-4">選擇付款方式</h3>

          <div class="text-sm text-gray-600 mb-4">
            選取 <strong>{{ selectedNumbers.length }}</strong> 張<template v-if="selectedMethod !== 'draw_now'">，
            總計 <strong class="text-indigo-600">${{ totalPrice.toLocaleString() }}</strong></template>
          </div>

          <div class="space-y-3 mb-6">
            <label v-for="m in paymentMethods" :key="m"
              class="flex items-center gap-3 p-3 border rounded-lg cursor-pointer"
              :class="[
                selectedMethod === m ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200',
                m === 'linepay' ? 'opacity-50' : '',
              ]"
            >
              <input v-model="selectedMethod" :value="m" type="radio"
                :disabled="m === 'linepay'"
                class="accent-indigo-600" />
              <div>
                <div class="flex items-center gap-2">
                  <span class="text-sm font-medium" :class="m === 'linepay' ? 'text-gray-400' : 'text-gray-900'">{{ methodLabels[m] || m }}</span>
                  <span v-if="m === 'linepay'" class="text-xs bg-gray-200 text-gray-500 px-1.5 py-0.5 rounded">暫不開放</span>
                </div>
                <div class="text-xs" :class="m === 'linepay' ? 'text-gray-300' : 'text-gray-400'">{{ m === 'linepay' ? '模擬線上付款' : m === 'draw_now' ? '免付款直接抽' : '到店付款' }}</div>
              </div>
            </label>
          </div>

          <div v-if="error" class="bg-red-50 text-red-600 text-sm p-3 rounded-lg mb-4">{{ error }}</div>

          <div class="flex gap-3">
            <button @click="cancelPayment" :disabled="drawing" class="flex-1 bg-gray-100 text-gray-700 py-2.5 rounded-lg text-sm font-semibold hover:bg-gray-200">
              取消
            </button>
            <button @click="confirmPayment" :disabled="drawing"
              class="flex-1 bg-indigo-600 text-white py-2.5 rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50"
            >
              {{ drawing ? '處理中...' : selectedMethod === 'draw_now' ? '確認抽獎' : '確認付款並抽獎' }}
            </button>
          </div>
        </div>

        <!-- Waiting for onsite payment -->
        <div v-else class="text-center py-4">
          <h3 class="text-lg font-bold text-gray-900 mb-4">請至櫃檯付款</h3>
          <p class="text-sm text-gray-500 mb-4">請出示以下條碼給店員掃描</p>
          <img
            :src="`/api/payments/qrcode/${payment.id}`"
            class="mx-auto w-48 h-48 mb-4"
            alt="付款 QR Code"
          />
          <p class="text-xs text-gray-400 font-mono mb-4">{{ payment.id }}</p>
          <div class="flex items-center justify-center gap-2 text-sm text-gray-500 mb-4">
            <div class="animate-spin h-4 w-4 border-2 border-indigo-500 border-t-transparent rounded-full"></div>
            等待櫃檯確認付款...
          </div>
          <button @click="cancelPayment" class="text-sm text-gray-400 hover:text-gray-600 underline">
            取消訂單
          </button>
        </div>
      </div>
    </div>

    <!-- Draw Result Modal -->
    <div v-if="drawResult" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-2xl shadow-xl max-w-md w-full p-6">
        <h3 class="text-lg font-bold text-green-600 mb-4">恭喜中獎！</h3>
        <div class="space-y-2 mb-6">
          <div v-for="r in drawResult" :key="r.serial_number"
            class="flex items-center justify-between p-3 bg-green-50 rounded-lg"
          >
            <span class="text-sm font-bold text-gray-700">#{{ r.serial_number }}</span>
            <span class="text-sm font-semibold text-green-700">{{ r.prize_grade_name }}</span>
            <span class="text-sm text-gray-500">{{ r.item_name }}（{{ r.item_type }}）</span>
          </div>
        </div>
        <button @click="closeResult" class="w-full bg-green-600 text-white py-2.5 rounded-lg text-sm font-semibold hover:bg-green-700">確定</button>
      </div>
    </div>

    <div class="flex gap-3">
      <div class="text-sm text-gray-500 flex items-center">
        已選 <strong class="text-gray-900 mx-1">{{ selectedNumbers.length }}</strong> 張，
        共 <strong class="text-gray-900 mx-1">${{ totalPrice.toLocaleString() }}</strong>
      </div>
      <button
        @click="openPayment"
        :disabled="selectedNumbers.length === 0 || showPayment"
        :class="[
          'ml-auto px-6 py-2.5 rounded-lg font-semibold text-sm transition',
          selectedNumbers.length > 0 && !showPayment
            ? 'bg-indigo-600 text-white hover:bg-indigo-700'
            : 'bg-gray-200 text-gray-400 cursor-not-allowed',
        ]"
      >
        結帳抽獎
      </button>
    </div>

    <div class="bg-white rounded-xl shadow-sm border p-6">
      <h2 class="text-lg font-semibold text-gray-900 mb-4">獎賞一覽</h2>
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b">
            <th class="text-left px-3 py-2 font-medium text-gray-600">獎賞等級與名稱</th>
            <th class="text-left px-3 py-2 font-medium text-gray-600">圖片</th>
            <th class="text-right px-3 py-2 font-medium text-gray-600">剩餘狀態</th>
          </tr>
        </thead>
        <tbody class="divide-y">
          <tr v-for="g in grades" :key="g.id">
            <td class="px-3 py-2">
              <span class="font-medium text-gray-900">{{ g.grade_name }}</span>
              <span class="text-gray-500 ml-1">{{ g.item_name }}</span>
            </td>
            <td class="px-3 py-2">
              <img v-if="g.image_url" :src="g.image_url" class="w-48 h-48 object-cover rounded" />
            </td>
            <td class="px-3 py-2 text-right">
              <span class="text-gray-700">剩 {{ g.remaining_stock }} / 共 {{ g.initial_stock }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
