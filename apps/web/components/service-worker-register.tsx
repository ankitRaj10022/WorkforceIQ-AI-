"use client";

import { useEffect } from "react";

export function ServiceWorkerRegister() {
  useEffect(() => {
    if (!("serviceWorker" in navigator)) {
      return;
    }

    const isLoopback =
      window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1";

    if (isLoopback) {
      navigator.serviceWorker.getRegistrations().then((registrations) => {
        void Promise.all(registrations.map((registration) => registration.unregister()));
      });
      return;
    }

    navigator.serviceWorker
      .register("/sw.js")
      .then((registration) => registration.update().catch(() => undefined))
      .catch(() => {
        // The app remains fully usable without offline shell registration.
      });
  }, []);

  return null;
}
