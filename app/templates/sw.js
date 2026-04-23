{% load static %}
const CACHE_NAME = 'kiki-crm-v1';
const ASSETS = [
  '{% url "dashboard" %}',
  '{% static "css/crm.css" %}',
  '{% static "js/sidebar.js" %}',
  '{% static "images/icon-192.png" %}',
  '{% static "images/icon-512.png" %}'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(ASSETS);
    })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request);
    })
  );
});
