import { describe, expect, test } from "bun:test";

import type { ProductContract } from "../api-client/types";
import { createContractSummary } from "./operations-summary";

const contract = {
  primary_workflow: "robot_workcell_obstruction",
  observation_states: ["clear", "blocked", "uncertain", "camera_unavailable"],
  incident_states: ["clear", "dwell", "alert_pending", "closed"],
  severity_levels: ["high"],
  zone_types: ["emergency_exit"],
  provider_boundaries: [
    "perception",
    "incident_reporting",
    "voice",
    "verification",
    "review_export",
  ],
  voice_provider_statuses: [
    {
      provider: "local_audio",
      availability: "available",
      detail: "Local prebuilt alert audio is available.",
    },
    {
      provider: "mistral",
      availability: "unconfigured",
      detail: "Mistral credentials are not configured.",
    },
    {
      provider: "elevenlabs",
      availability: "unconfigured",
      detail: "ElevenLabs credentials are not configured.",
    },
  ],
  review_export_provider_statuses: [
    {
      provider: "local_review",
      availability: "available",
      detail: "Local review queue is available.",
    },
    {
      provider: "encord",
      availability: "unconfigured",
      detail:
        "Encord export unavailable: credentials are not configured; local review queue remains available.",
    },
  ],
  provider_integration_statuses: [
    {
      provider: "local_replay",
      boundary: "perception",
      availability: "available",
      detail: "Local replay perception is active for the demo.",
    },
    {
      provider: "runpod_yolo",
      boundary: "perception",
      availability: "unconfigured",
      detail:
        "RunPod YOLO boundary is scaffolded; endpoint client is not configured, so local replay remains active.",
    },
    {
      provider: "local_incident_report",
      boundary: "incident_reporting",
      availability: "available",
      detail:
        "Local deterministic incident report is active for opened incidents.",
    },
    {
      provider: "openai_foundry",
      boundary: "incident_reporting",
      availability: "unconfigured",
      detail:
        "OpenAI/Foundry scaffold is unavailable until credentials are configured.",
    },
    {
      provider: "gemini_robotics_er",
      boundary: "verification",
      availability: "unconfigured",
      detail:
        "Gemini Robotics-ER scaffold is unavailable until credentials are configured.",
    },
  ],
  reference_zone: {
    id: "zone-workcell-a2",
    name: "Robot Workcell A-2",
    zone_type: "emergency_exit",
    geometry: [
      { x: 0.14, y: 0.18 },
      { x: 0.58, y: 0.18 },
      { x: 0.58, y: 0.82 },
    ],
    policy: {
      dwell_threshold_seconds: 30,
      severity: "high",
      escalation_channel: "floor_supervisor",
    },
  },
  reference_evidence_frame: {
    id: "frame-reference-blocked",
    source: "replay",
    timestamp: "2026-05-08T12:00:00Z",
    image_ref: "assets/demo/reference-blocked.jpg",
    annotations: [{ label: "zone_overlap", confidence: 0.94 }],
  },
  reference_observation: {
    zone_id: "zone-workcell-a2",
    observed_state: "blocked",
    dwell_duration_seconds: 30,
    evidence_frame_id: "frame-reference-blocked",
    confidence: 0.94,
  },
  reference_incident: {
    id: "incident-reference",
    zone_id: "zone-workcell-a2",
    state: "alert_pending",
    severity: "high",
    before_evidence_frame_id: "frame-reference-blocked",
  },
} satisfies ProductContract;

describe("createContractSummary", () => {
  test("formats generated backend contract values for the operations shell", () => {
    const summary = createContractSummary(contract);

    expect(summary.primaryWorkflowLabel).toBe("Robot workcell obstruction");
    expect(summary.referenceZoneName).toBe("Robot Workcell A-2");
    expect(summary.referenceIncidentState).toBe("Alert pending");
    expect(summary.referenceEvidenceTimestamp).toBe("2026-05-08T12:00:00Z");
    expect(summary.observationStateLabels).toContain("Camera unavailable");
    expect(summary.providerBoundaryLabels).toEqual([
      "Perception",
      "Incident reporting",
      "Voice",
      "Verification",
      "Review export",
    ]);
    expect(summary.voiceProviderStatuses).toEqual([
      {
        availabilityLabel: "Available",
        detail: "Local prebuilt alert audio is available.",
        provider: "local_audio",
        providerLabel: "Local audio",
      },
      {
        availabilityLabel: "Unconfigured",
        detail: "Mistral credentials are not configured.",
        provider: "mistral",
        providerLabel: "Mistral",
      },
      {
        availabilityLabel: "Unconfigured",
        detail: "ElevenLabs credentials are not configured.",
        provider: "elevenlabs",
        providerLabel: "ElevenLabs",
      },
    ]);
    expect(summary.reviewExportProviderStatuses).toEqual([
      {
        availabilityLabel: "Available",
        detail: "Local review queue is available.",
        provider: "local_review",
        providerLabel: "Local review",
      },
      {
        availabilityLabel: "Unconfigured",
        detail:
          "Encord export unavailable: credentials are not configured; local review queue remains available.",
        provider: "encord",
        providerLabel: "Encord",
      },
    ]);
    expect(summary.providerIntegrationStatuses).toEqual([
      {
        availabilityLabel: "Available",
        boundaryLabel: "Perception",
        detail: "Local replay perception is active for the demo.",
        provider: "local_replay",
        providerLabel: "Local replay",
      },
      {
        availabilityLabel: "Unconfigured",
        boundaryLabel: "Perception",
        detail:
          "RunPod YOLO boundary is scaffolded; endpoint client is not configured, so local replay remains active.",
        provider: "runpod_yolo",
        providerLabel: "RunPod YOLO",
      },
      {
        availabilityLabel: "Available",
        boundaryLabel: "Incident reporting",
        detail:
          "Local deterministic incident report is active for opened incidents.",
        provider: "local_incident_report",
        providerLabel: "Local incident report",
      },
      {
        availabilityLabel: "Unconfigured",
        boundaryLabel: "Incident reporting",
        detail:
          "OpenAI/Foundry scaffold is unavailable until credentials are configured.",
        provider: "openai_foundry",
        providerLabel: "OpenAI/Foundry",
      },
      {
        availabilityLabel: "Unconfigured",
        boundaryLabel: "Verification",
        detail:
          "Gemini Robotics-ER scaffold is unavailable until credentials are configured.",
        provider: "gemini_robotics_er",
        providerLabel: "Gemini Robotics-ER",
      },
    ]);
  });
});
