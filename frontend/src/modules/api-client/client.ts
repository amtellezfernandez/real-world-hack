import createClient from "openapi-fetch";

import type { paths } from "./openapi";

const DEFAULT_API_BASE_URL = "/api";

/** Resolve the backend API URL from frontend-safe Vite configuration. */
export function getApiBaseUrl(): string {
  const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL;

  if (configuredBaseUrl === undefined || configuredBaseUrl.length === 0) {
    return DEFAULT_API_BASE_URL;
  }

  return configuredBaseUrl;
}

/** Typed OpenAPI client for URDF Zone backend contracts. */
export const apiClient = createClient<paths>({
  baseUrl: getApiBaseUrl(),
});
