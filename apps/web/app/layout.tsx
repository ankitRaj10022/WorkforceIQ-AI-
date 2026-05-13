import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { ServiceWorkerRegister } from "@/components/service-worker-register";

import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const isLocalPreview = process.env.NODE_ENV !== "production";

export const metadata: Metadata = {
  title: isLocalPreview ? "WorkforceIQ Dev Portal" : "WorkforceIQ Portal",
  description:
    "Enterprise workforce operations portal for WorkforceIQ on AWS Cognito and the WorkforceIQ API.",
  manifest: "/manifest.webmanifest",
  applicationName: isLocalPreview ? "WorkforceIQ Dev" : "WorkforceIQ",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: isLocalPreview ? "WorkforceIQ Dev" : "WorkforceIQ",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-background text-foreground font-sans">
        <ServiceWorkerRegister />
        {children}
      </body>
    </html>
  );
}
