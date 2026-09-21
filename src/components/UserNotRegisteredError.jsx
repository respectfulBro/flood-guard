import { Link } from "react-router-dom";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function UserNotRegisteredError() {
  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-slate-50">
      <div className="max-w-md w-full text-center space-y-6">
        <div className="w-16 h-16 rounded-full bg-rose-100 flex items-center justify-center mx-auto">
          <AlertCircle className="w-8 h-8 text-rose-600" />
        </div>
        
        <div className="space-y-3">
          <h1 className="text-2xl font-semibold text-slate-900">Access Restricted</h1>
          <p className="text-slate-600 leading-relaxed">
            Your account is not registered for this application. Please contact an administrator or sign up for access.
          </p>
        </div>
        
        <div className="space-y-3">
          <Button asChild size="lg" className="bg-teal-800 hover:bg-teal-900 w-full">
            <Link to="/signup">
              Sign Up for Access
            </Link>
          </Button>
          <Button asChild variant="outline" className="w-full">
            <Link to="/login">
              Log In with Different Account
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}