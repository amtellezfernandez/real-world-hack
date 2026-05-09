import type { AlertProvider, ProviderIntegration } from "../api-client/types";
import { formatToken } from "./format-token";

const providerLabelOverrides: Partial<
  Record<AlertProvider | ProviderIntegration, string>
> = {
  elevenlabs: "ElevenLabs",
  gemini_robotics_er: "Gemini Robotics-ER",
  openai_foundry: "OpenAI/Foundry",
  runpod_yolo: "RunPod YOLO",
};

/** Format backend alert provider tokens for product UI. */
export function formatAlertProvider(provider: AlertProvider): string {
  return formatProviderToken(provider);
}

/** Format backend provider integration tokens for product UI. */
export function formatProviderIntegration(
  provider: ProviderIntegration,
): string {
  return formatProviderToken(provider);
}

function formatProviderToken(
  provider: AlertProvider | ProviderIntegration,
): string {
  return providerLabelOverrides[provider] ?? formatToken(provider);
}
