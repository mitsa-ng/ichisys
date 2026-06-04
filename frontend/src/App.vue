<script setup>
import { RouterView, useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="min-h-screen bg-gray-50">
    <header class="bg-white shadow-sm border-b">
      <div class="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
        <a href="/" class="text-lg font-bold text-gray-800">一番賞</a>
        <nav class="flex gap-4 text-sm">
          <a href="/" class="text-gray-600 hover:text-gray-900">獎池列表</a>
          <a href="/admin/login" class="text-gray-600 hover:text-gray-900">管理後台</a>
        </nav>
      </div>
    </header>
    <main class="max-w-6xl mx-auto px-4 py-6">
      <RouterView />
    </main>
  </div>
</template>
