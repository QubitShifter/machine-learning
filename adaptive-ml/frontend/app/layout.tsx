import type { Metadata } from "next";

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
