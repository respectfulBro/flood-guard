import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ShieldCheck, AlertCircle } from "lucide-react";
import AuthLayout from "@/components/AuthLayout";

export default function OAuthConsent() {
  const [error] = useState("This feature requires a backend MCP server and is not available in local development mode.");

  return (
    <AuthLayout
      icon={ShieldCheck}
      title="Authorize access"
      subtitle="MCP Authorization"
    >
      <div className="p-3 rounded-lg bg-amber-50 text-amber-800 text-sm mb-4 flex items-start gap-2">
        <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
        <div>
          <p className="font-medium">Local Development Mode</p>
          <p>{error}</p>
        </div>
      </div>
      
      <p className="text-sm text-muted-foreground mb-6">
        This page is designed for OAuth consent flow with AI clients via an MCP server.
        In local development, this flow is not available.
      </p>

      <div className="flex gap-3">
        <Button
          variant="outline"
          className="flex-1 h-12 font-medium"
          onClick={() => window.location.href = "/"}
        >
          Go Home
        </Button>
        <Button
          className="flex-1 h-12 font-medium"
          onClick={() => window.location.href = "/login"}
        >
          Log In
        </Button>
      </div>
    </AuthLayout>
  );
}