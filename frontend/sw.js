self.addEventListener('install', (e) => {
  console.log('KAIA Service Worker Installed');
});

self.addEventListener('fetch', (e) => {
  // هذا الكود يضمن تشغيل التطبيق بسلاسة
  e.respondWith(fetch(e.request));
});