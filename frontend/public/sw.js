const CACHE_NAME = "boranizm-pwa-v3";
const APP_SHELL = ["/", "/index.html", "/manifest.webmanifest"];

function isCacheableResponse(response) {
  return Boolean(response) && response.status === 200 && response.type === "basic";
}

async function networkFirst(request, fallbackUrl = "") {
  try {
    const response = await fetch(request);
    if (isCacheableResponse(response)) {
      const cache = await caches.open(CACHE_NAME);
      await cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    if (fallbackUrl) {
      const fallback = await caches.match(fallbackUrl);
      if (fallback) return fallback;
    }
    const cached = await caches.match(request);
    if (cached) return cached;
    throw error;
  }
}

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  const response = await fetch(request);
  if (isCacheableResponse(response)) {
    const cache = await caches.open(CACHE_NAME);
    await cache.put(request, response.clone());
  }
  return response;
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  const sameOrigin = url.origin === self.location.origin;
  if (!sameOrigin) return;

  if (req.mode === "navigate") {
    event.respondWith(networkFirst(req, "/index.html"));
    return;
  }

  if (url.pathname.startsWith("/admin")) {
    event.respondWith(networkFirst(req));
    return;
  }

  const isVersionedAsset = url.pathname.startsWith("/assets/");
  const isStaticAsset = ["script", "style", "worker", "font"].includes(req.destination);
  if (isVersionedAsset || isStaticAsset) {
    event.respondWith(networkFirst(req));
    return;
  }

  event.respondWith(cacheFirst(req));
});
