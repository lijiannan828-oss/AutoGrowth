"use client";

import {
  createContext,
  startTransition,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signInWithRedirect,
  getRedirectResult,
  signOut,
  getAuth,
} from "firebase/auth";
import { ensureFirebase, getFirebaseApp } from "@/lib/firebase";
import { getStoredToken, setStoredToken } from "@/lib/api-client";

interface AuthUser {
  uid: string;
  email: string;
  displayName?: string | null;
  photoURL?: string | null;
}

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  error?: string;
  isFirebaseReady: boolean;
  signInWithGoogle: () => Promise<void>;
  logout: () => Promise<void>;
  loginWithDevToken: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const DEV_AUTH_TOKEN = "dev-token-123";
const DEV_LOGIN_FLAG_KEY = "autogrowth.devLogin";
const APP_ENV =
  process.env.NEXT_PUBLIC_APP_ENV ?? (process.env.NODE_ENV === "production" ? "production" : "development");
// 禁用开发环境自动登录，使用真实 Google 登录
const SHOULD_FORCE_DEV_TOKEN = false;
const DEV_USER: AuthUser = {
  uid: "dev-user",
  email: "Beckett@spoonlabs-partners.com",
  displayName: "Beckett",
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>();
  const isFirebaseReady = ensureFirebase();
  const devModeRef = useRef(false);
  const isSigningInRef = useRef(false);

  useEffect(() => {
    // 开发环境自动登录
    if (SHOULD_FORCE_DEV_TOKEN) {
      devModeRef.current = true;
      setStoredToken(DEV_AUTH_TOKEN);
      if (typeof window !== "undefined") {
        window.localStorage.setItem(DEV_LOGIN_FLAG_KEY, "1");
      }
      startTransition(() => {
        setUser(DEV_USER);
        setLoading(false);
      });
      return;
    }

    const existingToken = getStoredToken();
    const isDevLoginFlagged =
      typeof window !== "undefined" && window.localStorage.getItem(DEV_LOGIN_FLAG_KEY) === "1";
    if (isDevLoginFlagged && existingToken === DEV_AUTH_TOKEN) {
      devModeRef.current = true;
      startTransition(() => {
        setUser(DEV_USER);
        setLoading(false);
      });
      return;
    }

    devModeRef.current = false;

    if (!isFirebaseReady) {
      startTransition(() => setLoading(false));
      return;
    }

    const app = getFirebaseApp();
    const auth = getAuth(app);

    // 处理重定向登录结果
    getRedirectResult(auth)
      .then(async (result) => {
        if (result?.user) {
          const token = await result.user.getIdToken();
          setStoredToken(token);
        }
      })
      .catch((err) => {
        console.error("Redirect login error:", err);
      });

    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (devModeRef.current) {
        return;
      }

      if (firebaseUser) {
        if (typeof window !== "undefined") {
          window.localStorage.removeItem(DEV_LOGIN_FLAG_KEY);
        }
        const token = SHOULD_FORCE_DEV_TOKEN
          ? DEV_AUTH_TOKEN
          : await firebaseUser.getIdToken();
        setStoredToken(token);
        startTransition(() => {
          setUser({
            uid: firebaseUser.uid,
            email: firebaseUser.email ?? "",
            displayName: firebaseUser.displayName,
            photoURL: firebaseUser.photoURL,
          });
          setLoading(false);
        });
      } else {
        setStoredToken(null);
        startTransition(() => {
          setUser(null);
          setLoading(false);
        });
      }
    });

    return () => unsubscribe();
  }, [isFirebaseReady]);

  const signInWithGoogle = useCallback(async () => {
    if (!isFirebaseReady) {
      setError("Firebase 配置缺失，无法登录");
      return;
    }
    // 防止重复请求
    if (isSigningInRef.current) {
      return;
    }
    isSigningInRef.current = true;
    try {
      const auth = getAuth(getFirebaseApp());
      const provider = new GoogleAuthProvider();
      provider.setCustomParameters({ prompt: "select_account" });

      // 使用弹窗方式登录
      await signInWithPopup(auth, provider);
    } catch (err: unknown) {
      console.error("Login error:", err);
      // 忽略用户取消弹窗的错误
      if (err instanceof Error &&
          (err.message.includes("cancelled-popup-request") ||
           err.message.includes("popup-closed-by-user"))) {
        console.log("Popup was cancelled or closed, ignoring...");
      } else if (err instanceof Error) {
        setError(err.message);
      }
    } finally {
      isSigningInRef.current = false;
    }
  }, [isFirebaseReady]);

  const loginWithDevToken = useCallback(async () => {
    devModeRef.current = true;
    if (typeof window !== "undefined") {
      window.localStorage.setItem(DEV_LOGIN_FLAG_KEY, "1");
    }
    setStoredToken(DEV_AUTH_TOKEN);
    startTransition(() => {
      setUser(DEV_USER);
      setLoading(false);
    });
  }, []);

  const logout = useCallback(async () => {
    devModeRef.current = false;
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(DEV_LOGIN_FLAG_KEY);
    }
    setStoredToken(null);
    startTransition(() => setUser(null));
    if (isFirebaseReady) {
      const auth = getAuth(getFirebaseApp());
      await signOut(auth);
    }
  }, [isFirebaseReady]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      error,
      isFirebaseReady,
      signInWithGoogle,
      logout,
      loginWithDevToken,
    }),
    [user, loading, error, isFirebaseReady, signInWithGoogle, logout, loginWithDevToken],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuthContext() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuthContext must be used within AuthProvider");
  }
  return ctx;
}

