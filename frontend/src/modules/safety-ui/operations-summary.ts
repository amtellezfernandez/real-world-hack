import type { ProductContract } from "../api-client/types";
import { formatToken } from "./format-token";
import {
  formatAlertProvider,
  formatProviderIntegration,
} from "./provider-labels";

type VoiceProviderToken =
  ProductContract["voice_provider_statuses"][number]["provider"];
type ReviewExportProviderToken =
  ProductContract["review_export_provider_statuses"][number]["provider"];
type ProviderIntegrationToken =
  ProductContract["provider_integration_statuses"][number]["provider"];

/** UI-ready status for a voice output provider. */
export type VoiceProviderStatusSummary = {
  availabilityLabel: string;
  detail: string;
  provider: VoiceProviderToken;
  providerLabel: string;
};

/** UI-ready status for a review export provider. */
export type ReviewExportProviderStatusSummary = {
  availabilityLabel: string;
  detail: string;
  provider: ReviewExportProviderToken;
  providerLabel: string;
};

/** UI-ready status for a concrete provider integration. */
export type ProviderIntegrationStatusSummary = {
  availabilityLabel: string;
  boundaryLabel: string;
  detail: string;
  provider: ProviderIntegrationToken;
  providerLabel: string;
};

/** UI-ready summary derived from generated backend product contracts. */
export type ContractSummary = {
  incidentStateLabels: string[];
  observationStateLabels: string[];
  referenceEvidenceTimestamp: string;
  primaryWorkflowLabel: string;
  providerBoundaryLabels: string[];
  referenceIncidentState: string;
  referenceObservationState: string;
  referenceZoneName: string;
  providerIntegrationStatuses: ProviderIntegrationStatusSummary[];
  reviewExportProviderStatuses: ReviewExportProviderStatusSummary[];
  voiceProviderStatuses: VoiceProviderStatusSummary[];
};

/** Convert generated backend contract tokens into operations-shell labels. */
export function createContractSummary(
  contract: ProductContract,
): ContractSummary {
  return {
    incidentStateLabels: contract.incident_states.map(formatToken),
    observationStateLabels: contract.observation_states.map(formatToken),
    primaryWorkflowLabel: formatToken(contract.primary_workflow),
    providerBoundaryLabels: contract.provider_boundaries.map(formatToken),
    providerIntegrationStatuses: contract.provider_integration_statuses.map(
      (status) => ({
        availabilityLabel: formatToken(status.availability),
        boundaryLabel: formatToken(status.boundary),
        detail: status.detail,
        provider: status.provider,
        providerLabel: formatProviderIntegration(status.provider),
      }),
    ),
    referenceEvidenceTimestamp: contract.reference_evidence_frame.timestamp,
    referenceIncidentState: formatToken(contract.reference_incident.state),
    referenceObservationState: formatToken(
      contract.reference_observation.observed_state,
    ),
    referenceZoneName: contract.reference_zone.name,
    reviewExportProviderStatuses: contract.review_export_provider_statuses.map(
      (status) => ({
        availabilityLabel: formatToken(status.availability),
        detail: status.detail,
        provider: status.provider,
        providerLabel: formatToken(status.provider),
      }),
    ),
    voiceProviderStatuses: contract.voice_provider_statuses.map((status) => ({
      availabilityLabel: formatToken(status.availability),
      detail: status.detail,
      provider: status.provider,
      providerLabel: formatAlertProvider(status.provider),
    })),
  };
}
