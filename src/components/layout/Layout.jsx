import { usePilot } from "@/api/pilot";
import { Outlet } from "react-router-dom";
import { LanguageProvider } from "@/lib/LanguageContext";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";

export default function Layout() {
  const session = usePilot("/session");
  return (
    <LanguageProvider>
      <div className="min-h-screen flex flex-col bg-white">
        <Navbar />
        {session.data?.demo && <p role="status" className="bg-amber-100 text-amber-950 px-5 py-3 text-sm">Offline demo · historical data · observations saved to a separate demo database.</p>}
        <main className="flex-1">
          <Outlet />
        </main>
        <Footer />
      </div>
    </LanguageProvider>
  );
}