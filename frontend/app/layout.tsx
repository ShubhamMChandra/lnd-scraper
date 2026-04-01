import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Chicago L&D Finder",
  description: "Find Chicago companies with Learning & Development budgets and HR contacts",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.className}>
      <body className="bg-gray-950 text-gray-100 min-h-screen">
        <nav className="sticky top-0 z-50 bg-gray-900/80 backdrop-blur-xl border-b border-gray-800">
          <div className="max-w-7xl mx-auto px-6 flex items-center justify-between h-14">
            <Link href="/" className="flex items-center gap-2 text-lg font-bold text-white hover:text-white">
              <span className="text-violet-500 text-xl">&#9670;</span>
              Chicago L&D Finder
            </Link>
            <div className="flex items-center gap-5 text-sm">
              <Link href="/" className="text-gray-400 hover:text-white transition-colors">Dashboard</Link>
              <Link href="/api/export" className="text-gray-400 hover:text-white transition-colors">Export Companies</Link>
              <Link href="/api/export-contacts" className="text-gray-400 hover:text-white transition-colors">Export Contacts</Link>
              <Link href="/api/results" className="text-gray-400 hover:text-white transition-colors">API</Link>
            </div>
          </div>
        </nav>
        <main className="max-w-7xl mx-auto px-6 py-6">
          {children}
        </main>
        <footer className="text-center py-6 mt-10 border-t border-gray-800 text-gray-600 text-xs">
          Chicago L&D Company Finder &mdash; SerpAPI, Built In, Glassdoor, Crain&apos;s, Great Place to Work, Apollo, Hunter
        </footer>
      </body>
    </html>
  );
}
