import type { Metadata } from "next";
import "./globals.css";
import { Toaster } from "@/components/ui/Toaster";
import { AuthProvider } from "@/lib/auth";

export const metadata: Metadata = {
  title: "Agentics – Job Crawl & Chat",
  description: "Crawl jobs and chat with your talent data",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <AuthProvider>
          {children}
        </AuthProvider>
        <Toaster />
      </body>
    </html>
  );
}
