const CACHE_NAME = 'focusos-v2';
const ASSETS = [
    '/dashboard',
    '/login',
    '/register',
    '/static/css/style.css',
    '/static/js/tracker.js',
    '/static/js/charts.js',
    '/static/js/heatmap.js',
    '/static/js/rewards.js',
    '/static/manifest.json',
    '/static/img/icon-192.png',
    '/static/img/icon-512.png',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    'https://cdn.jsdelivr.net/npm/chart.js'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            return Promise.allSettled(ASSETS.map(url => cache.add(url)));
        })
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key)));
        })
    );
});

self.addEventListener('fetch', event => {
    if (event.request.method !== 'GET') return;

    // For HTML pages: Network First
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request).catch(() => caches.match(event.request))
        );
        return;
    }

    // For assets: Cache First
    event.respondWith(
        caches.match(event.request).then(cached => {
            return cached || fetch(event.request).then(response => {
                // Optionally cache new assets discovered
                return response;
            });
        }).catch(() => {
            if (event.request.url.indexOf('.png') > -1) {
                return caches.match('/static/img/icon-512.png');
            }
        })
    );
});
