// Service Worker for Smart Library PWA
const CACHE_NAME = 'smart-library-v1';

// Install event
self.addEventListener('install', (event) => {
    self.skipWaiting();
});

// Activate event
self.addEventListener('activate', (event) => {
    event.waitUntil(clients.claim());
});

// Fetch event — network first, fall back to cache
self.addEventListener('fetch', (event) => {
    event.respondWith(
        fetch(event.request)
            .then((response) => {
                return response;
            })
            .catch(() => {
                return caches.match(event.request);
            })
    );
});

// ── Web Push Notifications ──────────────────────────────────────

self.addEventListener('push', function (event) {
    if (!event.data) {
        console.log('Push event but no data');
        return;
    }

    try {
        const payload = event.data.json();
        const options = {
            body: payload.body || 'You have a new update.',
            icon: payload.icon || '/static/icon-512.png',
            badge: '/static/icon-512.png',
            vibrate: [200, 100, 200],
            data: {
                url: payload.url || '/'
            }
        };

        event.waitUntil(
            self.registration.showNotification(payload.title || 'Smart Library', options)
        );
    } catch (e) {
        console.error('Push payload rendering error:', e);
        // Fallback if payload isn't JSON
        event.waitUntil(
            self.registration.showNotification('Smart Library', {
                body: event.data.text()
            })
        );
    }
});

self.addEventListener('notificationclick', function (event) {
    event.notification.close();

    // Attempt to extract URL from the notification data payload
    const urlToOpen = (event.notification.data && event.notification.data.url) ? event.notification.data.url : '/';

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function (clientList) {
            // Check if there is already a window/tab open with the target URL
            for (let i = 0; i < clientList.length; i++) {
                let client = clientList[i];
                if (client.url === urlToOpen && 'focus' in client) {
                    return client.focus();
                }
            }
            // If not open, open a new window
            if (clients.openWindow) {
                return clients.openWindow(urlToOpen);
            }
        })
    );
});
