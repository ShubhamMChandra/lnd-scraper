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
      <body className="bg-gray-950 text-gray-100 min-h-screen flex flex-col">
        <a href="#main-content" className="absolute -top-10 left-4 bg-violet-600 text-white px-4 py-2 rounded z-[200] focus:top-4 transition-all">
          Skip to main content
        </a>
        <header className="sticky top-0 z-50 bg-gray-950/70 backdrop-blur-2xl border-b border-white/[0.06]">
          <nav className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16" aria-label="Main navigation">
            <Link href="/" className="flex items-center gap-2.5 group">
              <span className="flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-indigo-600 text-white text-sm font-black shadow-lg shadow-violet-500/20 group-hover:shadow-violet-500/40 transition-shadow" aria-hidden="true">L</span>
              <span className="text-base font-bold text-white tracking-tight">Chicago L&D</span>
            </Link>
            <div className="hidden sm:flex items-center gap-1 text-sm">
              <Link href="/" className="text-gray-400 hover:text-white hover:bg-white/[0.06] px-3 py-1.5 rounded-lg transition-all">Dashboard</Link>
              <Link href="/api/export" className="text-gray-400 hover:text-white hover:bg-white/[0.06] px-3 py-1.5 rounded-lg transition-all">Export</Link>
              <Link href="/api/export-contacts" className="text-gray-400 hover:text-white hover:bg-white/[0.06] px-3 py-1.5 rounded-lg transition-all">Contacts</Link>
              <Link href="/api/results" className="text-gray-400 hover:text-white hover:bg-white/[0.06] px-3 py-1.5 rounded-lg transition-all">API</Link>
            </div>
          </nav>
        </header>
        <main id="main-content" className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 py-6">
          {children}
        </main>
        <footer className="border-t border-white/[0.04] mt-auto">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="flex items-center justify-center w-5 h-5 rounded bg-gradient-to-br from-violet-500 to-indigo-600 text-white text-[10px] font-black" aria-hidden="true">L</span>
              <span className="text-xs text-gray-500 font-medium">Chicago L&D Finder</span>
            </div>
            <div className="flex items-center gap-4 text-[11px] text-gray-600">
              <span>SerpAPI</span>
              <span className="text-gray-800">&middot;</span>
              <span>Built In</span>
              <span className="text-gray-800">&middot;</span>
              <span>Glassdoor</span>
              <span className="text-gray-800">&middot;</span>
              <span>Apollo</span>
              <span className="text-gray-800">&middot;</span>
              <span>Hunter</span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
