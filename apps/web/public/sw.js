const CACHE_NAME = "workforceiq-static-v2";
const STATIC_ASSETS = [
  "/",
  "/manifest.webmanifest",
  "/favicon.ico",
  "/icon.svg",
  "/icons/icon-192.svg",
  "/icons/icon-512.svg",
];

function isSameOrigin(url) {
  return url.origin === self.location.origin;
}

function shouldBypass(url) {
  return (
    !isSameOrigin(url) ||
    url.pathname.startsWith("/api/") ||
    url.pathname.startsWith("/auth/")
  );
}

function isStaticAsset(url) {
  return (
    url.pathname === "/" ||
    url.pathname === "/manifest.webmanifest" ||
    url.pathname === "/favicon.ico" ||
    url.pathname === "/icon.svg" ||
    url.pathname.startsWith("/icons/") ||
    url.pathname.startsWith("/_next/static/")
  );
}

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS)),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key)),
      ),
    ).then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") {
    return;
  }

  const url = new URL(event.request.url);
  if (shouldBypass(url)) {
    return;
  }

  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request).catch(() => caches.match("/")),
    );
    return;
  }

  if (!isStaticAsset(url)) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => {
      const networkFetch = fetch(event.request)
        .then((response) => {
          if (response.ok) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then((cache) => {
              void cache.put(event.request, responseClone);
            });
          }
          return response;
        })
        .catch(() => cached);

      return cached || networkFetch;
    }),
  );
});
