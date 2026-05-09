import { describe, expect, test } from "bun:test";

import type { DemoReplay, ObservedState } from "../api-client/types";
import {
  createReplayImageAlt,
  createReplayViewModel,
  selectNextReplayFrameId,
  selectReplayFrame,
} from "./replay-view";

const replay = {
  id: "blocked-workcell-a2",
  name: "Blocked workcell replay",
  zone: {
    id: "zone-workcell-a2",
    name: "Robot Workcell A-2",
    zone_type: "emergency_exit",
    geometry: [
      { x: 0.14, y: 0.18 },
      { x: 0.58, y: 0.18 },
      { x: 0.58, y: 0.82 },
      { x: 0.14, y: 0.82 },
    ],
    policy: {
      dwell_threshold_seconds: 30,
      severity: "high",
      escalation_channel: "floor_supervisor",
    },
  },
  timing: {
    default_mode: "stage",
    options: [
      {
        mode: "stage",
        label: "Stage timing",
        frame_interval_ms: 900,
        playback_dwell_seconds: 3,
        playback_clearance_seconds: 2,
        requires_external_providers: false,
      },
      {
        mode: "real_time",
        label: "Real-time timing",
        frame_interval_ms: 5000,
        playback_dwell_seconds: 30,
        playback_clearance_seconds: 15,
        requires_external_providers: false,
      },
    ],
  },
  frames: [
    {
      id: "replay-frame-clear",
      label: "Clear exit",
      evidence_frame: {
        id: "frame-workcell-clear",
        source: "replay",
        timestamp: "2026-05-08T12:00:00Z",
        image_ref: "assets/demo/workcell-clear.svg",
        annotations: [{ label: "zone_clear", confidence: 0.98 }],
      },
      observation: {
        zone_id: "zone-workcell-a2",
        observed_state: "clear",
        dwell_duration_seconds: 0,
        evidence_frame_id: "frame-workcell-clear",
        confidence: 0.98,
      },
      assessment: {
        incident_state: "clear",
        policy_reason: "Zone is clear.",
        incident: null,
      },
    },
    {
      id: "replay-frame-blocked",
      label: "Transient blockage",
      evidence_frame: {
        id: "frame-workcell-blocked",
        source: "replay",
        timestamp: "2026-05-08T12:00:08Z",
        image_ref: "assets/demo/workcell-blocked.svg",
        annotations: [{ label: "zone_overlap", confidence: 0.94 }],
      },
      observation: {
        zone_id: "zone-workcell-a2",
        observed_state: "blocked",
        dwell_duration_seconds: 8,
        evidence_frame_id: "frame-workcell-blocked",
        confidence: 0.94,
      },
      assessment: {
        incident_state: "dwell",
        policy_reason: "Blocked for 8.0s of 30.0s dwell threshold.",
        incident: null,
      },
    },
    {
      id: "replay-frame-incident",
      label: "Sustained blockage",
      evidence_frame: {
        id: "frame-workcell-sustained-blocked",
        source: "replay",
        timestamp: "2026-05-08T12:00:30Z",
        image_ref: "assets/demo/workcell-blocked.svg",
        annotations: [{ label: "zone_overlap", confidence: 0.94 }],
      },
      observation: {
        zone_id: "zone-workcell-a2",
        observed_state: "blocked",
        dwell_duration_seconds: 30,
        evidence_frame_id: "frame-workcell-sustained-blocked",
        confidence: 0.94,
      },
      assessment: {
        incident_state: "incident_open",
        policy_reason: "Blocked for 30.0s, meeting the 30.0s dwell threshold.",
        incident: {
          id: "incident-zone-workcell-a2-frame-workcell-sustained-blocked",
          zone_id: "zone-workcell-a2",
          state: "incident_open",
          severity: "high",
          before_evidence_frame_id: "frame-workcell-sustained-blocked",
          incident_report: {
            hazard: "Blocked robot workcell",
            severity: "high",
            evidence_summary:
              "frame-workcell-sustained-blocked shows Robot Workcell A-2 blocked for 30.0s.",
            rationale:
              "Robot Workcell A-2 has been blocked for 30.0s, meeting the 30.0s dwell threshold.",
            recommended_action:
              "Dispatch a floor supervisor to clear the obstruction.",
            alert_text_candidate:
              "Robotics notice: clear the obstruction at Robot Workcell A-2.",
          },
          alert_events: [],
          verification: null,
          audit_packet: null,
        },
      },
    },
    {
      id: "replay-frame-alert-broadcast",
      label: "Approved alert",
      evidence_frame: {
        id: "frame-workcell-sustained-blocked",
        source: "replay",
        timestamp: "2026-05-08T12:00:30Z",
        image_ref: "assets/demo/workcell-blocked.svg",
        annotations: [{ label: "zone_overlap", confidence: 0.94 }],
      },
      observation: {
        zone_id: "zone-workcell-a2",
        observed_state: "blocked",
        dwell_duration_seconds: 30,
        evidence_frame_id: "frame-workcell-sustained-blocked",
        confidence: 0.94,
      },
      assessment: {
        incident_state: "alert_broadcast",
        policy_reason: "Supervisor approved the local floor alert.",
        incident: {
          id: "incident-zone-workcell-a2-frame-workcell-sustained-blocked",
          zone_id: "zone-workcell-a2",
          state: "alert_broadcast",
          severity: "high",
          before_evidence_frame_id: "frame-workcell-sustained-blocked",
          incident_report: {
            hazard: "Blocked robot workcell",
            severity: "high",
            evidence_summary:
              "frame-workcell-sustained-blocked shows Robot Workcell A-2 blocked for 30.0s.",
            rationale:
              "Robot Workcell A-2 has been blocked for 30.0s, meeting the 30.0s dwell threshold.",
            recommended_action:
              "Dispatch a floor supervisor to clear the obstruction.",
            alert_text_candidate:
              "Robotics notice: clear the obstruction at Robot Workcell A-2.",
          },
          alert_events: [
            {
              incident_id: "incident-zone-workcell-a2-frame-workcell-sustained-blocked",
              approval_actor: "demo-supervisor",
              alert_text:
                "Robotics notice: clear the obstruction at Robot Workcell A-2.",
              provider: "local_audio",
              timestamp: "2026-05-08T12:00:35+00:00",
              audio_ref: "assets/audio/local-alert.wav",
            },
          ],
          verification: null,
          audit_packet: null,
        },
      },
    },
    {
      id: "replay-frame-uncertain",
      label: "Low light",
      evidence_frame: {
        id: "frame-workcell-uncertain",
        source: "replay",
        timestamp: "2026-05-08T12:00:12Z",
        image_ref: "assets/demo/workcell-clear.svg",
        annotations: [{ label: "low_light", confidence: 0.52 }],
      },
      observation: {
        zone_id: "zone-workcell-a2",
        observed_state: "uncertain",
        dwell_duration_seconds: 0,
        evidence_frame_id: "frame-workcell-uncertain",
        confidence: 0.52,
      },
      assessment: {
        incident_state: "uncertain",
        policy_reason: "Observation is uncertain.",
        incident: null,
      },
    },
  ],
} satisfies DemoReplay;

type ReplayFixtureFrame = DemoReplay["frames"][number];
type ReplayFixtureIncident = NonNullable<
  ReplayFixtureFrame["assessment"]["incident"]
>;
type IncidentState = ReplayFixtureFrame["assessment"]["incident_state"];
type AuditPacket = NonNullable<ReplayFixtureIncident["audit_packet"]>;
type ReviewSample = NonNullable<ReplayFixtureIncident["review_sample"]>;
type VerificationVerdict = NonNullable<
  ReplayFixtureIncident["verification"]
>["verdict"];

describe("createReplayViewModel", () => {
  test("maps a backend replay into clear and blocked operations view states", () => {
    const replayView = createReplayViewModel(replay);
    const clearFrame = selectReplayFrame(replayView, "replay-frame-clear");
    const blockedFrame = selectReplayFrame(replayView, "replay-frame-blocked");

    expect(clearFrame.label).toBe("Clear exit");
    expect(clearFrame.observationLabel).toBe("Clear");
    expect(clearFrame.incidentStateLabel).toBe("Clear");
    expect(clearFrame.observedState).toBe("clear");
    expect(blockedFrame.label).toBe("Transient blockage");
    expect(blockedFrame.observationLabel).toBe("Blocked");
    expect(blockedFrame.incidentStateLabel).toBe("Dwell");
    expect(blockedFrame.observedState).toBe("blocked");
    expect(replayView.zoneBox).toEqual({
      height: "64%",
      left: "14%",
      top: "18%",
      width: "44%",
    });
    expect(createReplayImageAlt(replayView, blockedFrame)).toBe(
      "Transient blockage replay frame for Robot Workcell A-2",
    );
  });

  test("exposes demo timing options without changing replay state order", () => {
    const replayView = createReplayViewModel(replay);

    expect(replayView.defaultTimingMode).toBe("stage");
    expect(replayView.timingOptions).toEqual([
      {
        clearanceLabel: "2s clearance",
        dwellLabel: "3s dwell",
        frameIntervalLabel: "900ms/frame",
        frameIntervalMs: 900,
        label: "Stage timing",
        mode: "stage",
        providerRequirementLabel: "Local fallback ready",
      },
      {
        clearanceLabel: "15s clearance",
        dwellLabel: "30s dwell",
        frameIntervalLabel: "5000ms/frame",
        frameIntervalMs: 5000,
        label: "Real-time timing",
        mode: "real_time",
        providerRequirementLabel: "Local fallback ready",
      },
    ]);
    expect(
      replayView.frameOptions.map((frame) => frame.incidentStateLabel),
    ).toEqual([
      "Clear",
      "Dwell",
      "Incident open",
      "Alert broadcast",
      "Uncertain",
    ]);
    expect(selectNextReplayFrameId(replayView, "replay-frame-clear")).toBe(
      "replay-frame-blocked",
    );
    expect(
      selectNextReplayFrameId(replayView, "replay-frame-uncertain"),
    ).toBeNull();
  });

  test("preserves uncertain observations instead of treating them as clear", () => {
    const replayView = createReplayViewModel(replay);
    const uncertainFrame = selectReplayFrame(
      replayView,
      "replay-frame-uncertain",
    );

    expect(uncertainFrame.observedState).toBe("uncertain");
    expect(uncertainFrame.observationLabel).toBe("Uncertain");
  });

  test("exposes sustained-blockage incident details for the incident rail", () => {
    const replayView = createReplayViewModel(replay);
    const incidentFrame = selectReplayFrame(
      replayView,
      "replay-frame-incident",
    );

    expect(incidentFrame.incidentStateLabel).toBe("Incident open");
    expect(incidentFrame.policyReason).toContain("meeting the 30.0s");
    expect(incidentFrame.incidentSeverity).toBe("high");
    expect(incidentFrame.incidentReport).toEqual({
      hazard: "Blocked robot workcell",
      recommendedAction:
        "Dispatch a floor supervisor to clear the obstruction.",
    });
  });

  test("exposes approved local alert transcript and provider", () => {
    const replayView = createReplayViewModel(replay);
    const alertFrame = selectReplayFrame(
      replayView,
      "replay-frame-alert-broadcast",
    );

    expect(alertFrame.incidentStateLabel).toBe("Alert broadcast");
    expect(alertFrame.alert).toEqual({
      audioRef: "assets/audio/local-alert.wav",
      providerLabel: "Local audio",
      transcript: "Robotics notice: clear the obstruction at Robot Workcell A-2.",
    });
  });

  test("exposes clearance verification for still-blocked and closed frames", () => {
    const replayView = createReplayViewModel(createReplayWithVerification());
    const stillBlockedFrame = selectReplayFrame(
      replayView,
      "replay-frame-still-blocked",
    );
    const verifiedClearFrame = selectReplayFrame(
      replayView,
      "replay-frame-verified-clear",
    );

    expect(stillBlockedFrame.incidentStateLabel).toBe("Clearing");
    expect(stillBlockedFrame.verification).toEqual({
      afterEvidenceFrameId: "frame-workcell-still-blocked",
      confidenceLabel: "92% confidence",
      rationale:
        "After evidence still shows an obstruction in the critical zone.",
      verdictLabel: "Still blocked",
    });
    expect(verifiedClearFrame.incidentStateLabel).toBe("Closed");
    expect(verifiedClearFrame.verification).toEqual({
      afterEvidenceFrameId: "frame-workcell-after-clear",
      confidenceLabel: "97% confidence",
      rationale: "After evidence shows the critical zone is clear.",
      verdictLabel: "Clear",
    });
  });

  test("exposes audit packet and local review sample for the closed frame", () => {
    const replayView = createReplayViewModel(createReplayWithVerification());
    const verifiedClearFrame = selectReplayFrame(
      replayView,
      "replay-frame-verified-clear",
    );

    expect(verifiedClearFrame.auditPacket).toEqual({
      afterFrameId: "frame-workcell-after-clear",
      afterTimestamp: "2026-05-08T12:00:45+00:00",
      alertTranscript:
        "Robotics notice: clear the obstruction at Robot Workcell A-2.",
      beforeFrameId: "frame-workcell-sustained-blocked",
      beforeTimestamp: "2026-05-08T12:00:30+00:00",
    });
    expect(verifiedClearFrame.reviewSample).toEqual({
      exportStatusLabel: "Local only",
      humanDecisionLabel: "Pending",
      labels: ["Blocked robot workcell", "Verified clear"],
    });
  });
});

function createReplayWithVerification(): DemoReplay {
  const alertFrame = replay.frames[3];

  if (alertFrame === undefined) {
    throw new Error("Expected replay fixture to include an alert frame");
  }

  const alertIncident = alertFrame.assessment.incident;

  if (alertIncident === null) {
    throw new Error("Expected replay fixture to include an alert incident");
  }

  return {
    ...replay,
    frames: [
      ...replay.frames.slice(0, 4),
      createVerificationFrame({
        alertIncident,
        annotationLabel: "zone_overlap",
        confidence: 0.92,
        dwellSeconds: 40,
        evidenceFrameId: "frame-workcell-still-blocked",
        id: "replay-frame-still-blocked",
        imageRef: "assets/demo/workcell-blocked.svg",
        label: "Still blocked",
        observedState: "blocked",
        rationale:
          "After evidence still shows an obstruction in the critical zone.",
        seconds: 40,
        state: "clearing",
        verdict: "still_blocked",
      }),
      createVerificationFrame({
        alertIncident,
        annotationLabel: "zone_clear",
        confidence: 0.97,
        dwellSeconds: 0,
        evidenceFrameId: "frame-workcell-after-clear",
        id: "replay-frame-verified-clear",
        imageRef: "assets/demo/workcell-clear.svg",
        label: "Verified clear",
        observedState: "clear",
        rationale: "After evidence shows the critical zone is clear.",
        seconds: 45,
        state: "closed",
        verdict: "clear",
        withEvidencePackage: true,
      }),
    ],
  };
}

function createVerificationFrame({
  alertIncident,
  annotationLabel,
  confidence,
  dwellSeconds,
  evidenceFrameId,
  id,
  imageRef,
  label,
  observedState,
  rationale,
  seconds,
  state,
  verdict,
  withEvidencePackage = false,
}: {
  alertIncident: ReplayFixtureIncident;
  annotationLabel: string;
  confidence: number;
  dwellSeconds: number;
  evidenceFrameId: string;
  id: string;
  imageRef: string;
  label: string;
  observedState: ObservedState;
  rationale: string;
  seconds: number;
  state: IncidentState;
  verdict: VerificationVerdict;
  withEvidencePackage?: boolean;
}): ReplayFixtureFrame {
  const auditPacket: AuditPacket | null = withEvidencePackage
    ? {
        incident_id: alertIncident.id,
        before_frame_id: alertIncident.before_evidence_frame_id,
        after_frame_id: evidenceFrameId,
        before_timestamp: "2026-05-08T12:00:30+00:00",
        after_timestamp: `2026-05-08T12:00:${seconds}+00:00`,
        alert_transcript:
          "Robotics notice: clear the obstruction at Robot Workcell A-2.",
        verification_verdict: verdict,
      }
    : (alertIncident.audit_packet ?? null);
  const reviewSample: ReviewSample | null = withEvidencePackage
    ? {
        incident_id: alertIncident.id,
        before_frame_id: alertIncident.before_evidence_frame_id,
        after_frame_id: evidenceFrameId,
        labels: ["blocked_robot_workcell", "verified_clear"],
        human_decision: "pending",
        export_status: "local_only",
      }
    : (alertIncident.review_sample ?? null);

  return {
    id,
    label,
    evidence_frame: {
      id: evidenceFrameId,
      source: "replay",
      timestamp: `2026-05-08T12:00:${seconds}Z`,
      image_ref: imageRef,
      annotations: [{ label: annotationLabel, confidence }],
    },
    observation: {
      zone_id: "zone-workcell-a2",
      observed_state: observedState,
      dwell_duration_seconds: dwellSeconds,
      evidence_frame_id: evidenceFrameId,
      confidence,
    },
    assessment: {
      incident_state: state,
      policy_reason: rationale,
      incident: {
        ...alertIncident,
        state,
        verification: {
          verdict,
          confidence,
          rationale,
          after_evidence_frame_id: evidenceFrameId,
        },
        audit_packet: auditPacket,
        review_sample: reviewSample,
      },
    },
  };
}
