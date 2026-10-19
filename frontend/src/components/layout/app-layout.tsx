"use client";

import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { MedicalDisclaimer } from "@/components/medical-disclaimer";

interface AppLayoutProps {
  children: React.ReactNode;
  title?: string;
}

export function AppLayout({ children, title }: AppLayoutProps) {
  return (
    <div className="min-h-screen bg-slate-950">
      <Sidebar />
      <div className="lg:pl-64">
        <Header title={title} />
        <main className="p-4 sm:p-6 lg:p-8">{children}</main>
        <footer className="border-t border-slate-800 px-4 py-5 sm:px-6 lg:px-8">
          <MedicalDisclaimer className="max-w-4xl" />
        </footer>
      </div>
    </div>
  );
}
