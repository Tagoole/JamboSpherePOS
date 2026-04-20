const STATIC_CACHE = 'jambopos-static-v4';
const DYNAMIC_CACHE = 'jambopos-dynamic-v4';

const APP_SHELL = [
  '/',
  '/dashboard/',
  '/products/',
  '/sales/',
  '/reports/daily/',
  '/static/js/offline-sync.js',
];

const AUTH_PAGES = ['/login/', '/signup/'];

self.addEventListener('install', function (event) {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(function (cache) {
      return cache.addAll(APP_SHELL);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(
        keys
          .filter(function (key) {
            return key !== STATIC_CACHE && key !== DYNAMIC_CACHE;
          })
          .map(function (key) {
            return caches.delete(key);
          })
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', function (event) {
  if (event.request.method !== 'GET') {
    return;
  }

  const requestUrl = new URL(event.request.url);

  // Never cache auth pages; they must always return fresh CSRF tokens.
  if (requestUrl.origin === self.location.origin && AUTH_PAGES.includes(requestUrl.pathname)) {
    event.respondWith(fetch(event.request));
    return;
  }

  // Cache-first for app shell routes.
  if (requestUrl.origin === self.location.origin && APP_SHELL.includes(requestUrl.pathname)) {
    event.respondWith(
      caches.match(event.request).then(function (cached) {
        return (
          cached ||
          fetch(event.request).then(function (response) {
            const responseClone = response.clone();
            caches.open(DYNAMIC_CACHE).then(function (cache) {
              cache.put(event.request, responseClone);
            });
            return response;
          })
        );
      })
    );
    return;
  }

  // Network-first for other same-origin requests, with cache fallback.
  if (requestUrl.origin === self.location.origin) {
    event.respondWith(
      fetch(event.request)
        .then(function (response) {
          const responseClone = response.clone();
          caches.open(DYNAMIC_CACHE).then(function (cache) {
            cache.put(event.request, responseClone);
          });
          return response;
        })
        .catch(function () {
          return caches.match(event.request).then(function (cached) {
            if (cached) {
              return cached;
            }

            if (event.request.mode === 'navigate') {
              return caches.match('/dashboard/').then(function (fallback) {
                return fallback || caches.match('/login/') || caches.match('/');
              });
            }

            return new Response('Offline', {
              status: 503,
              statusText: 'Offline',
            });
          });
        })
    );
  }
});

self.addEventListener('sync', function (event) {
  if (event.tag !== 'jambopos-sync') {
    return;
  }

  event.waitUntil(
    self.clients.matchAll({ includeUncontrolled: true, type: 'window' }).then(function (clients) {
      clients.forEach(function (client) {
        client.postMessage({ type: 'JAMBOPOS_SYNC_REQUESTED' });
      });
    })
  );
});