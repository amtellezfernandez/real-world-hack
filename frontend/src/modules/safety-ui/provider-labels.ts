import type { ProviderIntegration } from "../api-client/types";
import { formatToken } from "./format-token";

const providerLabelOverrides: Partial<Record<ProviderIntegration, string>> = {
  gemini_robotics_er: "Gemini Robotics-ER",
  openai_foundry: "OpenAI/Foundry",
  runpod_yolo: "RunPod YOLO",
};

/** Format backend provider integration tokens for product UI. */
export function formatProviderIntegration(
  provider: ProviderIntegration,
): string {
  return providerLabelOverrides[provider] ?? formatToken(provider);
}
