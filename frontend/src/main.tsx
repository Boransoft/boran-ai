import React from "react";
import ReactDOM from "react-dom/client";

import App from "./App";
import "./styles.css";

if (window.matchMedia("(display-mode: standalone)").matches) {
  document.body.classList.add("standalone");
}

const SW_CACHE_PREFIX = "boranizm-pwa-";
const SW_RESET_RELOAD_KEY = "boran:sw-reset-reload";
const isAdminPath =
  window.location.pathname === "/admin" || window.location.pathname.startsWith("/admin/");
const shouldRegisterServiceWorker = import.meta.env.PROD && !isAdminPath;

async function unregisterServiceWorkersAndCleanupCaches() {
  try {
    const registrations = await navigator.serviceWorker.getRegistrations();
    await Promise.all(registrations.map((registration) => registration.unregister()));
  } catch (error) {
    console.warn("Service worker unregister failed:", error);
  }

  if ("caches" in window) {
    try {
      const keys = await caches.keys();
      await Promise.all(
        keys.filter((key) => key.startsWith(SW_CACHE_PREFIX)).map((key) => caches.delete(key)),
      );
    } catch (error) {
      console.warn("Service worker cache cleanup failed:", error);
    }
  }

  if (navigator.serviceWorker.controller) {
    const alreadyReloaded = sessionStorage.getItem(SW_RESET_RELOAD_KEY) === "1";
    if (!alreadyReloaded) {
      sessionStorage.setItem(SW_RESET_RELOAD_KEY, "1");
      window.location.reload();
      return;
    }
  }

  sessionStorage.removeItem(SW_RESET_RELOAD_KEY);
}

if ("serviceWorker" in navigator) {
  if (shouldRegisterServiceWorker) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("/sw.js", { updateViaCache: "none" }).catch((error) => {
        console.warn("Service worker registration failed:", error);
      });
    });
  } else {
    void unregisterServiceWorkersAndCleanupCaches();
  }
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
