import type { Metadata } from "next";
import "./globals.css";
import { LanguageProvider } from "@/context/LanguageContext";
import CommandPalette from "@/components/CommandPalette";

export const metadata: Metadata = {
  title: "LightWeight — Run Large LLMs on Consumer Hardware",
  description: "Open-source AI inference engine for running large language models on limited resources.",
  icons: {
    icon: "/images/logo-light.png",
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
      className="h-full antialiased"
    >
      <body className="min-h-full flex flex-col">
        <LanguageProvider>
          {children}
          <CommandPalette />
        </LanguageProvider>
      </body>
    </html>
  );
}
