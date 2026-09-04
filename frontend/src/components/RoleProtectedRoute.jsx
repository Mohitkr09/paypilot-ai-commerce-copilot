import React from "react";
import {
  Navigate,
  Outlet,
} from "react-router-dom";

import { useAuth } from "../context/AuthContext";

const RoleProtectedRoute = ({
  allowedRoles = [],
}) => {
  const {
    isAuthenticated,
    loading,
    role,
  } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <p className="text-slate-600">
          Checking permissions...
        </p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        replace
      />
    );
  }

  const currentRole =
    String(role || "").toLowerCase();

  const authorized =
    allowedRoles.length === 0 ||
    allowedRoles.some(
      (allowedRole) =>
        String(allowedRole).toLowerCase() ===
        currentRole
    );

  if (!authorized) {
    return (
      <Navigate
        to="/unauthorized"
        replace
      />
    );
  }

  return <Outlet />;
};

export default RoleProtectedRoute;