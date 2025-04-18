// static/sw.js

const CACHE_NAME = 'red-notebook-cache-v1';
// Add paths to your core static assets here
const urlsToCache = [
  // We cache the root path cautiously. If it changes frequently or requires
  // authentication state not available offline, caching it might cause issues.
  // '/', // Let's skip caching root for now to avoid complexity
  '/static/css/style.css', '/static/js/script.js',
  // Add paths to any other essential local static assets (e.g., logo if not
  // inline)
  // '/static/images/icon-192x192.png', // Example: Cache icons if desired
  // '/static/images/icon-512x512.png'
];

// Install event: Cache core assets
self.addEventListener('install', event => {
  console.log('[Service Worker] Installing...');
  event.waitUntil(
      caches.open(CACHE_NAME)
          .then(cache => {
            console.log('[Service Worker] Opened cache:', CACHE_NAME);
            // AddAll will fail if any single request fails.
            // Consider adding assets individually with error handling for
            // robustness.
            return cache.addAll(urlsToCache);
          })
          .then(() => {
            console.log('[Service Worker] Core assets cached successfully.');
            // Force the waiting service worker to become the active service
            // worker.
            return self.skipWaiting();
          })
          .catch(error => {
            console.error('[Service Worker] Cache installation failed:', error);
          }));
});

// Activate event: Clean up old caches
self.addEventListener('activate', event => {
  console.log('[Service Worker] Activating...');
  const cacheWhitelist = [CACHE_NAME];  // Only keep the current cache version
  event.waitUntil(
      caches.keys()
          .then(cacheNames => {
            return Promise.all(cacheNames.map(cacheName => {
              if (cacheWhitelist.indexOf(cacheName) === -1) {
                console.log('[Service Worker] Deleting old cache:', cacheName);
                return caches.delete(cacheName);
              }
            }));
          })
          .then(() => {
            console.log('[Service Worker] Claiming clients...');
            // Take control of all open clients immediately.
            return self.clients.claim();
          }));
});

// Fetch event: Serve cached static assets, go to network for others
self.addEventListener('fetch', event => {
  const requestUrl = new URL(event.request.url);

  // Strategy: Cache falling back to network for local static assets
  if (urlsToCache.includes(requestUrl.pathname)) {
    event.respondWith(caches.match(event.request).then(response => {
      // Cache hit - return response
      if (response) {
        // console.log(`[Service Worker] Serving from cache:
        // ${requestUrl.pathname}`);
        return response;
      }
      // Not in cache - fetch from network
      // console.log(`[Service Worker] Fetching from network:
      // ${requestUrl.pathname}`);
      return fetch(event.request)
          .then(networkResponse => {
            // Optional: Cache the newly fetched static asset? Be careful with
            // updates. For simplicity, we are only caching on install here.
            return networkResponse;
          })
          .catch(error => {
            console.error(
                `[Service Worker] Fetch failed for ${requestUrl.pathname}:`,
                error);
            // Optional: Return a generic offline fallback for assets if needed
          });
    }));
  }
  // Strategy: Network only for all other requests (HTML pages, API calls,
  // external CDNs) Let the browser handle offline behavior for these.
  else {
    // console.log(`[Service Worker] Network request (not caching):
    // ${requestUrl.pathname}`); Don't intercept, just let it go to the network.
    // event.respondWith(fetch(event.request)); // Explicitly fetching
    return;  // Or simply return to let browser handle it normally
  }
});
