import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { PRODUCTION_URL } from "@/lib/constants";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const title = "Arcos Transparente — Consulte os dados públicos de Arcos (MG)";
const description =
  "Ferramenta gratuita para consultar contratos, salários e licitações da prefeitura de Arcos em linguagem natural.";

export const metadata: Metadata = {
  metadataBase: new URL(PRODUCTION_URL),
  title,
  description,
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title,
    description,
    url: PRODUCTION_URL,
    siteName: "Arcos Transparente",
    locale: "pt_BR",
    type: "website",
    images: [
      {
        url: "/opengraph-image",
        width: 1200,
        height: 630,
        alt: "Arcos Transparente — transparência pública que qualquer pessoa consegue usar.",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title,
    description,
  },
};

export const viewport: Viewport = {
  themeColor: "#1d4ed8",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR" className={inter.variable}>
      <body className="font-sans">{children}</body>
    </html>
  );
}
