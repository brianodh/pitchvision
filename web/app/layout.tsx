import type { Metadata, Viewport } from "next";
import "@fontsource-variable/inter";
import "@fontsource-variable/jetbrains-mono";
import "@fontsource/barlow-condensed/600.css";
import "@fontsource/barlow-condensed/700.css";
import "./globals.css";
import { AppHeader } from "@/components/AppHeader";

// Fonts are bundled from npm (@fontsource), so the app makes no network request at runtime — it has to
// work on conference wifi, or none.
export const metadata: Metadata = {
  title: { default: "PitchVision", template: "%s · PitchVision" },
  description: "Ball events from match video, on a searchable timeline.",
};

export const viewport: Viewport = { themeColor: "#0a0c0d", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-dvh">
        <AppHeader />
        {children}
      </body>
    </html>
  );
}
