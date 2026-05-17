"use client";

import { useAuth } from "@clerk/nextjs";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export { API_BASE };

export function useApi() {
  const { getToken, isSignedIn } = useAuth();

  async function fetchWithAuth(
    path: string,
    options: RequestInit = {}
  ): Promise<Response> {
    const headers = new Headers(options.headers || {});
    headers.set("Content-Type", "application/json");

    if (isSignedIn) {
      const token = await getToken();
      if (token) {
        headers.set("Authorization", `Bearer ${token}`);
      }
    }

    return fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });
  }

  return { fetchWithAuth };
}
