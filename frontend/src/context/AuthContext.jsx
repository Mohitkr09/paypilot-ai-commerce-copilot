import React, {
  createContext,
  useContext,
  useEffect,
  useState,
} from "react";

const AuthContext =
  createContext(null);

const TOKEN_KEY =
  "access_token";

const MERCHANT_ID_KEY =
  "merchant_id";

const ROLE_KEY =
  "role";

const USER_KEY =
  "paypilot_user";

// =========================================================
// AUTH PROVIDER
// =========================================================

export const AuthProvider = ({
  children,
}) => {
  const [token, setToken] =
    useState(() =>
      localStorage.getItem(
        TOKEN_KEY
      )
    );

  const [user, setUser] =
    useState(() => {
      const storedUser =
        localStorage.getItem(
          USER_KEY
        );

      if (!storedUser) {
        return null;
      }

      try {
        return JSON.parse(
          storedUser
        );
      } catch {
        return null;
      }
    });

  const [loading, setLoading] =
    useState(true);

  // =======================================================
  // RESTORE AUTHENTICATION
  // =======================================================

  useEffect(() => {
    const storedToken =
      localStorage.getItem(
        TOKEN_KEY
      );

    const storedMerchantId =
      localStorage.getItem(
        MERCHANT_ID_KEY
      );

    const storedRole =
      localStorage.getItem(
        ROLE_KEY
      );

    const storedUser =
      localStorage.getItem(
        USER_KEY
      );

    if (storedToken) {
      setToken(storedToken);

      if (storedUser) {
        try {
          setUser(
            JSON.parse(
              storedUser
            )
          );
        } catch {
          setUser({
            merchant_id:
              storedMerchantId
                ? Number(
                    storedMerchantId
                  )
                : null,

            role:
              storedRole ||
              null,
          });
        }
      } else {
        setUser({
          merchant_id:
            storedMerchantId
              ? Number(
                  storedMerchantId
                )
              : null,

          role:
            storedRole ||
            null,
        });
      }
    }

    setLoading(false);
  }, []);

  // =======================================================
  // LISTEN FOR EXPIRED JWT
  // =======================================================

  useEffect(() => {
    const handleLogout =
      () => {
        setToken(null);
        setUser(null);
      };

    window.addEventListener(
      "paypilot:logout",
      handleLogout
    );

    return () => {
      window.removeEventListener(
        "paypilot:logout",
        handleLogout
      );
    };
  }, []);

  // =======================================================
  // LOGIN
  // =======================================================

  const login = (
    loginResponse
  ) => {
    if (
      !loginResponse?.access_token
    ) {
      throw new Error(
        "Login response does not contain an access token."
      );
    }

    const accessToken =
      loginResponse.access_token;

    const merchantId =
      loginResponse.merchant_id;

    const role =
      String(
        loginResponse.role ||
          "merchant"
      ).toLowerCase();

    const userData = {
      merchant_id:
        merchantId !==
          undefined &&
        merchantId !== null
          ? Number(
              merchantId
            )
          : null,

      role,

      name:
        loginResponse.name ||
        loginResponse.merchant_name ||
        null,

      email:
        loginResponse.email ||
        null,
    };

    localStorage.setItem(
      TOKEN_KEY,
      accessToken
    );

    if (
      merchantId !==
        undefined &&
      merchantId !== null
    ) {
      localStorage.setItem(
        MERCHANT_ID_KEY,
        String(
          merchantId
        )
      );
    }

    localStorage.setItem(
      ROLE_KEY,
      role
    );

    localStorage.setItem(
      USER_KEY,
      JSON.stringify(
        userData
      )
    );

    setToken(accessToken);
    setUser(userData);
  };

  // =======================================================
  // LOGOUT
  // =======================================================

  const logout = () => {
    localStorage.removeItem(
      TOKEN_KEY
    );

    localStorage.removeItem(
      MERCHANT_ID_KEY
    );

    localStorage.removeItem(
      ROLE_KEY
    );

    localStorage.removeItem(
      USER_KEY
    );

    setToken(null);
    setUser(null);
  };

  // =======================================================
  // ROLE HELPERS
  // =======================================================

  const hasRole = (
    requiredRole
  ) => {
    if (!user?.role) {
      return false;
    }

    return (
      String(
        user.role
      ).toLowerCase() ===
      String(
        requiredRole
      ).toLowerCase()
    );
  };

  const hasAnyRole = (
    roles = []
  ) => {
    if (!user?.role) {
      return false;
    }

    const currentRole =
      String(
        user.role
      ).toLowerCase();

    return roles.some(
      (role) =>
        String(
          role
        ).toLowerCase() ===
        currentRole
    );
  };

  // =======================================================
  // PROVIDER
  // =======================================================

  return (
    <AuthContext.Provider
      value={{
        token,

        user,

        loading,

        isAuthenticated:
          Boolean(token),

        merchantId:
          user?.merchant_id ??
          null,

        role:
          user?.role ??
          null,

        isAdmin:
          String(
            user?.role || ""
          ).toLowerCase() ===
          "admin",

        isMerchant:
          String(
            user?.role || ""
          ).toLowerCase() ===
          "merchant",

        login,

        logout,

        hasRole,

        hasAnyRole,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

// =========================================================
// AUTH HOOK
// =========================================================

export const useAuth = () => {
  const context =
    useContext(
      AuthContext
    );

  if (!context) {
    throw new Error(
      "useAuth must be used inside AuthProvider."
    );
  }

  return context;
};

export default AuthContext;