<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api, { setAdminToken } from '../../api'

const router = useRouter()
const email = ref('')
const password = ref('')
const otpCode = ref('')
const showOTP = ref(false)
const error = ref('')
const checking = ref(true)

onMounted(async () => {
  try {
    const res = await api.get('/setup/status')
    if (res.data.needs_setup) {
      router.push('/admin/setup')
    }
  } catch (_) {}
  finally { checking.value = false }
})

async function login() {
  error.value = ''
  try {
    const res = await api.post('/auth/login', {
      email: email.value,
      password: password.value,
    })
    setAdminToken(res.data.access_token)
    router.push('/admin')
  } catch (e) {
    if (e.response?.data?.detail === 'OTP required') {
      showOTP.value = true
    } else {
      error.value = e.response?.data?.detail || '登入失敗'
    }
  }
}

async function verifyOTP() {
  error.value = ''
  try {
    const res = await api.post('/auth/verify-otp', {
      email: email.value,
      otp_code: otpCode.value,
    })
    setAdminToken(res.data.access_token)
    router.push('/admin')
  } catch (e) {
    error.value = e.response?.data?.detail || '驗證失敗'
  }
}
</script>

<template>
  <div v-if="checking" class="text-gray-500 text-center mt-16">檢查系統狀態...</div>
  <div v-else class="max-w-sm mx-auto mt-16">
    <h1 class="text-2xl font-bold text-gray-900 text-center mb-6">管理員登入</h1>
    <div class="bg-white rounded-xl shadow-sm border p-6">
      <div v-if="error" class="bg-red-50 text-red-600 text-sm p-3 rounded-lg mb-4">{{ error }}</div>
      <form @submit.prevent="showOTP ? verifyOTP() : login()">
        <div v-if="!showOTP">
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input v-model="email" type="email" required class="w-full border rounded-lg px-3 py-2 text-sm" />
          </div>
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-1">密碼</label>
            <input v-model="password" type="password" required class="w-full border rounded-lg px-3 py-2 text-sm" />
          </div>
          <button type="submit" class="w-full bg-indigo-600 text-white py-2 rounded-lg text-sm font-semibold hover:bg-indigo-700">登入</button>
        </div>
        <div v-else>
          <p class="text-sm text-gray-500 mb-4">請輸入 Google Authenticator 驗證碼</p>
          <div class="mb-4">
            <label class="block text-sm font-medium text-gray-700 mb-1">驗證碼</label>
            <input v-model="otpCode" type="text" required class="w-full border rounded-lg px-3 py-2 text-sm text-center tracking-widest" placeholder="000000" />
          </div>
          <button type="submit" class="w-full bg-indigo-600 text-white py-2 rounded-lg text-sm font-semibold hover:bg-indigo-700">驗證</button>
        </div>
      </form>
    </div>
  </div>
</template>
