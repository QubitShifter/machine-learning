import type { Metadata } from "next";

import { AppHeader } from "@/components/AppHeader";
import { LanguageProvider } from "@/components/LanguageProvider";
import { StudentProfileProvider } from "@/components/StudentProfileProvider";
import "../node_modules/katex/dist/katex.min.css";
import "../node_modules/mathlive/mathlive-fonts.css";
import "../node_modules/mathlive/mathlive-static.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "MAT-PAL",
  description:
    "Math And Physics Adaptive Learning",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <StudentProfileProvider>
          <LanguageProvider>
            <AppHeader />
            {children}
          </LanguageProvider>
        </StudentProfileProvider>
      </body>
    </html>
  );
}
