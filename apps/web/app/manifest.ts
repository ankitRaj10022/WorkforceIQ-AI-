import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  const isLocalPreview = process.env.NODE_ENV !== "production";

  return {
    id: isLocalPreview ? "/?app=workforceiq-dev" : "/?app=workforceiq",
    name: isLocalPreview
      ? "WorkforceIQ Dev Portal"
      : "WorkforceIQ Secure Portal",
    short_name: isLocalPreview ? "WFIQ Dev" : "WorkforceIQ",
    description:
      isLocalPreview
        ? "Local preview build for WorkforceIQ. Do not install this build for production use."
        : "Secure workforce operations portal for desktop and mobile installation.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    background_color: "#f2ede3",
    theme_color: "#0f766e",
    orientation: "portrait-primary",
    icons: [
      {
        src: "/icons/icon-192.svg",
        sizes: "192x192",
        type: "image/svg+xml",
        purpose: "any",
      },
      {
        src: "/icons/icon-512.svg",
        sizes: "512x512",
        type: "image/svg+xml",
        purpose: "any",
      },
    ],
  };
}
