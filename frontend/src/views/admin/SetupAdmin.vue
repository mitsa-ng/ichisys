<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api'

const router = useRouter()
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const displayName = ref('')
const error = ref('')
const loading = ref(true)
const submitting = ref(false)

onMounted(async () => {
  try {
    const res = await api.get('/setup/status')
    if (!res.data.needs_setup) {
      router.push('/admin/login')
    }
  } catch (e) {
    console.error('Setup status check failed:', e)
    router.push('/admin/login')
  }
  finally { loading.value = false }
})

async function submit() {
  error.value = ''
  if (!email.value.trim()) { error.value = '請輸入 Email'; return }
  if (password.value.length < 6) { error.value = '密碼長度至少 6 碼'; return }
  if (password.value !== confirmPassword.value) { error.value = '兩次密碼輸入不一致'; return }
  if (!displayName.value.trim()) { error.value = '請輸入顯示名稱'; return }

  submitting.value = true
  try {
    await api.post('/setup/admin', {
      email: email.value,
      password: password.value,
      display_name: displayName.value,
    })
    alert('管理員建立成功，請登入')
    router.push('/admin/login')
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '設定失敗'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div v-if="loading" class="text-gray-500 text-center mt-16">檢查系統狀態...</div>
  <div v-else class="max-w-sm mx-auto mt-16">
    <h1 class="text-2xl font-bold text-gray-900 text-center mb-2">初始設定</h1>
    <p class="text-sm text-gray-500 text-center mb-6">建立管理員帳戶以開始使用</p>
    <div class="bg-white rounded-xl shadow-sm border p-6">
      <div v-if="error" class="bg-red-50 text-red-600 text-sm p-3 rounded-lg mb-4">{{ error }}</div>
      <form @submit.prevent="submit">
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">顯示名稱</label>
          <input v-model="displayName" type="text" required class="w-full border rounded-lg px-3 py-2 text-sm" placeholder="管理員" />
        </div>
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">Email</label>
          <input v-model="email" type="email" required class="w-full border rounded-lg px-3 py-2 text-sm" placeholder="admin@example.com" />
        </div>
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">密碼</label>
          <input v-model="password" type="password" required class="w-full border rounded-lg px-3 py-2 text-sm" placeholder="至少 6 碼" />
        </div>
        <div class="mb-6">
          <label class="block text-sm font-medium text-gray-700 mb-1">確認密碼</label>
          <input v-model="confirmPassword" type="password" required class="w-full border rounded-lg px-3 py-2 text-sm" />
        </div>
        <button type="submit" :disabled="submitting"
          class="w-full bg-indigo-600 text-white py-2.5 rounded-lg text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50">
          {{ submitting ? '建立中...' : '建立管理員' }}
        </button>
      </form>
    </div>
  </div>
</template>
