import type { components } from "./openapi";

/** Backend readiness response. */
export type HealthResponse = components["schemas"]["HealthResponse"];

/** Backend-generated product contract shared with the frontend. */
export type ProductContract = components["schemas"]["ProductContract"];

/** Concrete provider integration token from backend contracts. */
export type ProviderIntegration = components["schemas"]["ProviderIntegration"];

/** Controlled backend replay source for the operations view. */
export type DemoReplay = components["schemas"]["DemoReplay"];

/** Observed state token for a monitored critical zone. */
export type ObservedState = components["schemas"]["ObservedState"];

/** Evidence-backed observation state from the backend contract. */
export type Observation = components["schemas"]["Observation"];

/** Incident-relevant object detected in a camera frame. */
export type GeminiObjectDetection =
  components["schemas"]["GeminiObjectDetection"];

/** Gemini-backed object detection response from the perception endpoint. */
export type GeminiObjectDetectionResponse =
  components["schemas"]["GeminiObjectDetectionResponse"];

/** Gemini-backed semantic path status for a camera frame. */
export type GeminiSemanticStatusResult =
  components["schemas"]["GeminiSemanticStatusResult"];
