import createClient from "openapi-fetch";

import type { paths } from "./openapi";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

/** Resolve the backend API URL from frontend-safe Vite configuration. */
export function getApiBaseUrl(): string {
  const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL;

  if (configuredBaseUrl === undefined || configuredBaseUrl.length === 0) {
    return DEFAULT_API_BASE_URL;
  }

  return configuredBaseUrl;
}

/** Typed OpenAPI client for RobotOps Sentinel backend contracts. */
export const apiClient = createClient<paths>({
  baseUrl: getApiBaseUrl(),
});
