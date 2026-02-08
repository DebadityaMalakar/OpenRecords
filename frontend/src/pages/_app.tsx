import "@/styles/globals.css";
import type { AppProps } from "next/app";
import { useEffect } from "react";

import { useAuthStore } from "@/lib/store/auth";

export default function App({ Component, pageProps }: AppProps) {
  const loadUser = useAuthStore((state) => state.loadUser);

  useEffect(() => {
    void loadUser();
  }, [loadUser]);

  useEffect(() => {
    if (typeof document === "undefined") return;
    const stored = window.localStorage.getItem("openrecords-theme") || "bi-dark";
    document.documentElement.setAttribute("data-theme", stored);
    document.documentElement.style.colorScheme = stored === "bi-light" ? "light" : "dark";
  }, []);

  return <Component {...pageProps} />;
}
