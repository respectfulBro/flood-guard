import { Outlet } from "react-router-dom";
import { LanguageProvider } from "@/lib/LanguageContext";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";

export default function Layout() {
  return (
    <LanguageProvider>
      <div className="min-h-screen flex flex-col bg-white">
        <Navbar />
        <main className="flex-1">
          <Outlet />
        </main>
        <Footer />
      </div>
    </LanguageProvider>
  );
}