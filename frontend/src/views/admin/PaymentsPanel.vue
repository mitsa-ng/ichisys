<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import api from '../../api'

const payments = ref([])
const loading = ref(true)
const processLoading = ref(false)

const scannerInput = ref('')
const scanning = ref(false)
const scannerRef = ref(null)
let html5QrCode = null
let eventSource = null

async function loadPayments() {
  loading.value = true
  try {
    const res = await api.get('/payments/list', { params: { status: 'pending' } })
    payments.value = res.data
  } catch (_) {}
  finally { loading.value = false }
}

async function confirmPayment(id) {
  if (!confirm('確定要確認此筆付款？')) return
  processLoading.value = true
  try {
    await api.post(`/payments/${id}/confirm`)
    payments.value = payments.value.filter(p => p.id !== id)
  } catch (e) {
    alert(e.response?.data?.detail || '確認失敗')
  }
  finally { processLoading.value = false }
}

async function cancelPayment(id) {
  if (!confirm('確定要取消此筆訂單？')) return
  processLoading.value = true
  try {
    await api.post(`/payments/${id}/cancel`)
    payments.value = payments.value.filter(p => p.id !== id)
  } catch (e) {
    alert(e.response?.data?.detail || '取消失敗')
  }
  finally { processLoading.value = false }
}

async function handleScannerInput() {
  const id = scannerInput.value.trim()
  if (!id) return
  const payment = payments.value.find(p => p.id === id)
  if (!payment) {
    alert('找不到此付款編號，請確認條碼內容')
    scannerInput.value = ''
    return
  }
  scannerInput.value = ''
  await confirmPayment(payment.id)
}

function startScanner() {
  scanning.value = true
  import('html5-qrcode').then(async ({ Html5Qrcode }) => {
    html5QrCode = new Html5Qrcode("qr-reader")
    try {
      await html5QrCode.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 250, height: 250 } },
        async (decodedText) => {
          await html5QrCode.stop()
          scanning.value = false
          const payment = payments.value.find(p => p.id === decodedText)
          if (!payment) {
            alert('找不到此付款編號')
            return
          }
          await confirmPayment(payment.id)
        },
        () => {}
      )
    } catch (err) {
      alert('無法開啟相機：' + err)
      scanning.value = false
    }
  })
}

function stopScanner() {
  if (html5QrCode) {
    html5QrCode.stop().catch(() => {})
    html5QrCode = null
  }
  scanning.value = false
}

onMounted(() => {
  loadPayments()
  eventSource = new EventSource('/api/events')
  eventSource.onmessage = (e) => {
    if (!e.data) return
    try {
      const { event } = JSON.parse(e.data)
      if (['payment_confirmed', 'payment_cancelled', 'payment_created'].includes(event)) {
        loadPayments()
      }
    } catch (_) {}
  }
})
onUnmounted(() => {
  stopScanner()
  if (eventSource) eventSource.close()
})
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-lg font-semibold text-gray-900">付款確認</h2>
      <button @click="startScanner" v-if="!scanning"
        class="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-indigo-700">
        掃描 QR Code
      </button>
      <button @click="stopScanner" v-if="scanning"
        class="bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-red-700">
        關閉相機
      </button>
    </div>

    <div v-if="scanning" class="mb-4">
      <div id="qr-reader" class="max-w-xs mx-auto rounded-lg overflow-hidden"></div>
      <p class="text-center text-sm text-gray-500 mt-2">將 QR Code 置於畫面中</p>
    </div>

    <div class="mb-4 flex gap-2">
      <input v-model="scannerInput" placeholder="貼上付款編號（或掃描 QR Code）"
        class="flex-1 border rounded-lg px-3 py-2 text-sm"
        @keyup.enter="handleScannerInput" />
      <button @click="handleScannerInput"
        class="bg-gray-700 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-gray-800">
        查詢
      </button>
    </div>

    <div v-if="loading" class="text-gray-500">載入中...</div>
    <div v-else-if="payments.length === 0" class="text-gray-400 text-center py-12">尚無待確認付款</div>
    <div v-else class="space-y-3">
      <div v-for="p in payments" :key="p.id"
        class="bg-white rounded-xl shadow-sm border p-4">
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <div class="flex items-center gap-2 mb-1">
              <span class="font-mono text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">{{ p.id.slice(0, 8) }}...</span>
              <span class="text-sm font-semibold text-gray-900">{{ p.pool_name }}</span>
              <span class="text-xs bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded">待確認</span>
            </div>
            <div class="text-sm text-gray-600 space-y-0.5">
              <div>金額：<strong class="text-gray-900">${{ p.amount.toLocaleString() }}</strong></div>
              <div>方式：{{ p.method === 'onsite' ? '現場付款' : 'LinePay' }}</div>
              <div>選號：{{ p.serial_numbers }}</div>
              <div class="text-xs text-gray-400">建立時間：{{ new Date(p.created_at).toLocaleString('zh-TW') }}</div>
            </div>
          </div>
          <div class="flex gap-2 ml-4">
            <button @click="cancelPayment(p.id)" :disabled="processLoading"
              class="bg-red-100 text-red-700 px-4 py-2 rounded-lg text-sm font-semibold hover:bg-red-200 disabled:opacity-50 whitespace-nowrap">
              取消訂單
            </button>
            <button @click="confirmPayment(p.id)" :disabled="processLoading"
              class="bg-green-600 text-white px-5 py-2 rounded-lg text-sm font-semibold hover:bg-green-700 disabled:opacity-50 whitespace-nowrap">
              {{ processLoading ? '處理中...' : '確認收款' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
