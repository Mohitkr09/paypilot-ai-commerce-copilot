import React from "react";

import {
  ShieldX,
} from "lucide-react";

import {
  Link,
} from "react-router-dom";

const Unauthorized =
  () => {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 px-6">
        <div className="text-center">

          <div className="w-20 h-20 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-6">
            <ShieldX
              size={40}
              className="text-red-600"
            />
          </div>

          <h1 className="text-3xl font-bold text-slate-900">
            Access Denied
          </h1>

          <p className="text-slate-600 mt-3">
            You do not have permission
            to access this page.
          </p>

          <Link
            to="/dashboard"
            className="inline-block mt-6 px-5 py-3 rounded-lg bg-blue-600 text-white font-medium hover:bg-blue-700"
          >
            Back to Dashboard
          </Link>

        </div>
      </div>
    );
  };

export default Unauthorized;