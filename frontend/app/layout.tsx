import type { Metadata } from "next";
import { JetBrains_Mono, Onest, Schibsted_Grotesk } from "next/font/google";
import "./globals.css";

const schibsted = Schibsted_Grotesk({
  variable: "--font-schibsted",
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
    "A portfolio project that turns supplier catalogs, invoices, shipment notes and claims into validated, structured records.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${schibsted.variable} ${onest.variable} ${jetbrains.variable}`}
    >
      <body>{children}</body>
    </html>
  );
}
