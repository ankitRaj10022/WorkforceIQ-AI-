import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "WorkforceIQ Secure Portal",
    short_name: "WorkforceIQ",
    description:
      "Secure workforce operations portal for desktop and mobile installation.",
    start_url: "/",
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
