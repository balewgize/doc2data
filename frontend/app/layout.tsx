import type { Metadata } from "next";
import { JetBrains_Mono, Onest, Syne } from "next/font/google";
import "./globals.css";

const syne = Syne({
  variable: "--font-syne",
  subsets: ["latin"],
  display: "swap",
});

const onest = Onest({
  variable: "--font-onest",
  subsets: ["latin"],
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Doc2Data: documents to clean data",
  description:
    "Turn supplier catalogs, invoices, shipment notes and claims into validated, structured records.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${syne.variable} ${onest.variable} ${jetbrains.variable}`}
    >
      <body>{children}</body>
    </html>
  );
}
