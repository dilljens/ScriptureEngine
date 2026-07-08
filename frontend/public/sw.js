/// <reference lib="webworker" />

const CACHE_NAME = 'scripture-engine-v3'
const BUILD_TIME = '1783474668'

self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(keys.map((key) => caches.delete(key)))
    })
  )
  self.clients.claim()
})

// Network-first: try network, fall back to cache
self.addEventListener('fetch', (event) => {
  // Only handle GET requests from supported schemes (http, https)
  if (event.request.method !== 'GET') return
  const url = new URL(event.request.url)
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return

  // Skip tracking/analytics
  if (url.hostname.includes('cloudflareinsights') || url.hostname.includes('beacon')) return

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.status === 200) {
          const clone = response.clone()
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone))
        }
        return response
      })
      .catch(() => caches.match(event.request))
  )
})

self.addEventListener('push', (event) => {
  if (!event.data) return
  try {
    const data = event.data.json()
    self.registration.showNotification(data.title || 'ScriptureEngine', {
      body: data.body || 'Time for your scripture review!',
      icon: '/icon-192.png',
      badge: '/icon-192.png',
      vibrate: [200, 100, 200],
      data: { url: data.url || '/' },
    })
  } catch {
    self.registration.showNotification('ScriptureEngine', {
      body: event.data.text(),
      icon: '/icon-192.png',
    })
  }
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = event.notification.data?.url || '/'
  event.waitUntil(
    clients.matchAll({ type: 'window' }).then((clientList) => {
      for (const client of clientList) {
        if (client.url === url && 'focus' in client) return client.focus()
      }
      if (clients.openWindow) clients.openWindow(url)
    })
  )
})
