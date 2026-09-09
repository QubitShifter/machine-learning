import type { Metadata } from "next";

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
      <body>{children}</body>
    </html>
  );
}
