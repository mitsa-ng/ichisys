import { ref, onMounted, onUnmounted } from 'vue'

const listeners = {}

export function useEventSource(url) {
  const connected = ref(false)
  let es = null

  function connect() {
    es = new EventSource(url)
    es.onopen = () => { connected.value = true }
    es.onerror = () => { connected.value = false }
    es.onmessage = (e) => {
      if (!e.data) return
      try {
        const { event, data } = JSON.parse(e.data)
        if (listeners[event]) {
          listeners[event].forEach(fn => fn(data))
        }
      } catch (_) {}
    }
  }

  function disconnect() {
    if (es) {
      es.close()
      es = null
      connected.value = false
    }
  }

  function on(event, fn) {
    if (!listeners[event]) listeners[event] = []
    listeners[event].push(fn)
  }

  function off(event, fn) {
    if (!listeners[event]) return
    listeners[event] = listeners[event].filter(f => f !== fn)
  }

  onMounted(connect)
  onUnmounted(disconnect)

  return { connected, on, off }
}
