import axios from "axios";

const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";
const AUTH_TOKEN_STORAGE_KEY = "autogrowth.idToken";

const normalizeBaseUrl = (input: string): string => {
  let url = (input || "").trim();
  // Strip accidental leading '@' copied from chat
  if (url.startsWith("@")) {
    url = url.slice(1);
  }
  if (!url) {
    return DEFAULT_API_BASE_URL;
  }
  // Remove trailing slashes to avoid double slashes
  url = url.replace(/\/+$/, "");
  // Ensure it ends with /api/v1
  if (!url.endsWith("/api/v1")) {
    // If it ends with /api, add /v1
    if (url.endsWith("/api")) {
      url = `${url}/v1`;
    } else {
      url = `${url}/api/v1`;
    }
  }
  return url;
};

const apiClient = axios.create({
  baseURL: normalizeBaseUrl(process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_BASE_URL),
  withCredentials: true,
  timeout: 30000, // 30秒超时，因为 Google Sheets 读取可能需要较长时间
});

export const getStoredToken = (): string | null => {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
};

export const setStoredToken = (token: string | null): void => {
  if (typeof window === "undefined") {
    return;
  }

  if (token) {
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
  } else {
    window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
  }
};

apiClient.interceptors.request.use((config) => {
  // Only access localStorage on client side
  if (typeof window !== "undefined") {
    const token = getStoredToken();

    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }

  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Normalize error message to simplify UI handling
    if (error.response?.data?.message) {
      error.message = error.response.data.message;
    }

    return Promise.reject(error);
  },
);

export { apiClient, AUTH_TOKEN_STORAGE_KEY };
export default apiClient;

