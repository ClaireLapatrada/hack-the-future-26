import "./globals.css";
import type { ReactNode } from "react";
import { JetBrains_Mono } from "next/font/google";

export const metadata = {
  title: "Supply Chain Intelligence",
  description: "Disruption workspace and risk dashboard for supply ops",
};

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={jetbrainsMono.variable} suppressHydrationWarning>
      <body
        className="min-h-screen bg-background text-textPrimary antialiased font-sans"
        suppressHydrationWarning
      >
        {children}
      </body>
    </html>
  );
}

