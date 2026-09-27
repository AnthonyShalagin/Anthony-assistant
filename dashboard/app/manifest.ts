import type { MetadataRoute } from "next";

// Lets the site be added to the iPhone home screen and open full screen like an app
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Anthony Health",
    short_name: "Health",
    description: "Recovery, sleep, training and labs at a glance.",
    start_url: "/",
    display: "standalone",
    background_color: "#000000",
    theme_color: "#000000",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
  };
}
