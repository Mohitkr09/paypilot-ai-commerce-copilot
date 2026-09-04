import React, {
  useState,
} from "react";

import {
  useNavigate,
  useLocation,
} from "react-router-dom";

import {
  useAuth,
} from "../context/AuthContext";

import {
  login as loginApi,
  getApiErrorMessage,
} from "../services/api";

const Login = () => {
  const navigate =
    useNavigate();

  const location =
    useLocation();

  const {
    login,
    isAuthenticated,
  } = useAuth();

  const [email, setEmail] =
    useState("");

  const [password, setPassword] =
    useState("");

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  // -------------------------------------------------------
  // Already authenticated
  // -------------------------------------------------------

  React.useEffect(() => {
    if (isAuthenticated) {
      navigate(
        "/dashboard",
        {
          replace: true,
        }
      );
    }
  }, [
    isAuthenticated,
    navigate,
  ]);

  // -------------------------------------------------------
  // LOGIN
  // -------------------------------------------------------

  const handleSubmit =
    async (event) => {
      event.preventDefault();

      setError("");

      if (!email.trim()) {
        setError(
          "Email is required."
        );
        return;
      }

      if (!password) {
        setError(
          "Password is required."
        );
        return;
      }

      try {
        setLoading(true);

        const response =
          await loginApi(
            email.trim(),
            password
          );

        // Save token + merchant + role
        login(response);

        // If user originally tried to
        // access a protected page,
        // send them there.
        const destination =
          location.state?.from ||
          "/dashboard";

        navigate(
          destination,
          {
            replace: true,
          }
        );
      } catch (err) {
        console.error(
          "Login failed:",
          err
        );

        setError(
          getApiErrorMessage(
            err
          )
        );
      } finally {
        setLoading(false);
      }
    };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-6">

      <div className="w-full max-w-md">

        <div className="bg-white rounded-2xl shadow-lg border border-slate-200 p-8">

          <div className="text-center mb-8">

            <h1 className="text-3xl font-bold text-slate-900">
              PayPilot
            </h1>

            <p className="text-slate-500 mt-2">
              AI Risk Engine
            </p>

          </div>

          {error && (
            <div className="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <form
            onSubmit={
              handleSubmit
            }
            className="space-y-5"
          >

            <div>

              <label className="block text-sm font-medium text-slate-700 mb-2">
                Email
              </label>

              <input
                type="email"
                value={email}
                onChange={(event) =>
                  setEmail(
                    event.target.value
                  )
                }
                placeholder="Enter your email"
                autoComplete="email"
                className="w-full px-4 py-3 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={loading}
              />

            </div>

            <div>

              <label className="block text-sm font-medium text-slate-700 mb-2">
                Password
              </label>

              <input
                type="password"
                value={password}
                onChange={(event) =>
                  setPassword(
                    event.target.value
                  )
                }
                placeholder="Enter your password"
                autoComplete="current-password"
                className="w-full px-4 py-3 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={loading}
              />

            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-semibold transition"
            >
              {loading
                ? "Signing in..."
                : "Sign In"}
            </button>

          </form>

        </div>

      </div>

    </div>
  );
};

export default Login;