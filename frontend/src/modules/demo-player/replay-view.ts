import type { DemoReplay, ObservedState } from "../api-client/types";
import { formatToken } from "../safety-ui/format-token";

/** Timing mode token for demo playback controls. */
export type ReplayTimingMode = DemoReplay["timing"]["options"][number]["mode"];

/** Incident report fields prepared for the operations rail. */
export type IncidentReportView = {
  hazard: string;
  recommendedAction: string;
};

/** Alert event fields prepared for the operations rail. */
export type AlertEventView = {
  transcript: string;
};

/** Clearance verification fields prepared for the operations rail. */
export type ClearanceVerificationView = {
  afterEvidenceFrameId: string;
  confidenceLabel: string;
  rationale: string;
  verdictLabel: string;
};

/** Audit packet fields prepared for the operations rail. */
export type AuditPacketView = {
  afterFrameId: string;
  afterTimestamp: string;
  alertTranscript: string;
  beforeFrameId: string;
  beforeTimestamp: string;
};

/** Local review sample fields prepared for the operations rail. */
export type ReviewSampleView = {
  exportStatusLabel: string;
  humanDecisionLabel: string;
  labels: string[];
};

/** Replay timing option prepared for demo playback controls. */
export type ReplayTimingOptionView = {
  clearanceLabel: string;
  dwellLabel: string;
  frameIntervalLabel: string;
  frameIntervalMs: number;
  label: string;
  mode: ReplayTimingMode;
  providerRequirementLabel: string;
};

/** Replay frame data prepared for the operations view. */
export type ReplayFrameView = {
  alert: AlertEventView | null;
  auditPacket: AuditPacketView | null;
  confidenceLabel: string;
  dwellLabel: string;
  id: string;
  imageRef: string;
  incidentReport: IncidentReportView | null;
  incidentSeverity: string;
  incidentStateLabel: string;
  label: string;
  observedState: ObservedState;
  observationLabel: string;
  policyReason: string;
  reviewSample: ReviewSampleView | null;
  timestamp: string;
  verification: ClearanceVerificationView | null;
};

/** CSS-ready bounding box for a normalized critical-zone polygon. */
export type ZoneBox = {
  height: string;
  left: string;
  top: string;
  width: string;
};

/** UI-ready replay state for the active operations view frame. */
export type ReplayViewModel = {
  defaultTimingMode: DemoReplay["timing"]["default_mode"];
  framesById: ReadonlyMap<string, ReplayFrameView>;
  frameOptions: ReplayFrameView[];
  nextFrameIdById: ReadonlyMap<string, string>;
  replayName: string;
  timingOptions: ReplayTimingOptionView[];
  timingOptionsByMode: ReadonlyMap<ReplayTimingMode, ReplayTimingOptionView>;
  zoneBox: ZoneBox;
  zoneName: string;
};

/** Convert a backend demo replay into operations view data. */
export function createReplayViewModel(replay: DemoReplay): ReplayViewModel {
  const frameOptions = replay.frames.map((frame) => ({
    alert: createAlertView(frame.assessment.incident),
    auditPacket: createAuditPacketView(frame.assessment.incident),
    confidenceLabel: formatConfidence(frame.observation.confidence),
    dwellLabel: `${frame.observation.dwell_duration_seconds}s dwell`,
    id: frame.id,
    imageRef: frame.evidence_frame.image_ref,
    incidentReport: createIncidentReportView(frame.assessment.incident),
    incidentSeverity: frame.assessment.incident?.severity ?? "none",
    incidentStateLabel: formatToken(frame.assessment.incident_state),
    label: frame.label,
    observedState: frame.observation.observed_state,
    observationLabel: formatToken(frame.observation.observed_state),
    policyReason: frame.assessment.policy_reason,
    reviewSample: createReviewSampleView(frame.assessment.incident),
    timestamp: frame.evidence_frame.timestamp,
    verification: createVerificationView(frame.assessment.incident),
  }));
  const firstFrame = frameOptions[0];

  if (firstFrame === undefined) {
    throw new Error("Demo replay has no frames");
  }
  const timingOptions = replay.timing.options.map(createTimingOptionView);

  return {
    defaultTimingMode: replay.timing.default_mode,
    framesById: new Map(frameOptions.map((frame) => [frame.id, frame])),
    frameOptions,
    nextFrameIdById: createNextFrameIdMap(frameOptions),
    replayName: replay.name,
    timingOptions,
    timingOptionsByMode: new Map(
      timingOptions.map((option) => [option.mode, option]),
    ),
    zoneBox: createZoneBox(replay),
    zoneName: replay.zone.name,
  };
}

/** Select the requested replay frame, falling back to the first replay frame. */
export function selectReplayFrame(
  replayView: ReplayViewModel,
  activeFrameId: string,
): ReplayFrameView {
  const firstFrame = replayView.frameOptions[0];

  if (firstFrame === undefined) {
    throw new Error("Demo replay has no frames");
  }

  return replayView.framesById.get(activeFrameId) ?? firstFrame;
}

/** Select the requested timing option, falling back to the default mode. */
export function selectReplayTiming(
  replayView: ReplayViewModel,
  activeTimingMode: ReplayTimingMode | null,
): ReplayTimingOptionView {
  const defaultTiming = replayView.timingOptionsByMode.get(
    replayView.defaultTimingMode,
  );

  if (defaultTiming === undefined) {
    throw new Error("Demo replay default timing is unavailable");
  }

  if (activeTimingMode === null) {
    return defaultTiming;
  }

  return replayView.timingOptionsByMode.get(activeTimingMode) ?? defaultTiming;
}

/** Select the next replay frame id, or null at the end of the replay. */
export function selectNextReplayFrameId(
  replayView: ReplayViewModel,
  activeFrameId: string,
): string | null {
  return replayView.nextFrameIdById.get(activeFrameId) ?? null;
}

/** Build accessible image text for a selected replay frame. */
export function createReplayImageAlt(
  replayView: ReplayViewModel,
  activeFrame: ReplayFrameView,
): string {
  return `${activeFrame.label} replay frame for ${replayView.zoneName}`;
}

function createZoneBox(replay: DemoReplay): ZoneBox {
  const firstPoint = replay.zone.geometry[0];

  if (firstPoint === undefined) {
    throw new Error("Demo replay zone has no geometry");
  }

  let left = firstPoint.x;
  let right = firstPoint.x;
  let top = firstPoint.y;
  let bottom = firstPoint.y;

  for (const point of replay.zone.geometry.slice(1)) {
    left = Math.min(left, point.x);
    right = Math.max(right, point.x);
    top = Math.min(top, point.y);
    bottom = Math.max(bottom, point.y);
  }

  return {
    height: formatPercent(bottom - top),
    left: formatPercent(left),
    top: formatPercent(top),
    width: formatPercent(right - left),
  };
}

function formatPercent(value: number): string {
  return `${Number((value * 100).toFixed(2))}%`;
}

function formatConfidence(confidence: number | null | undefined): string {
  if (typeof confidence !== "number") {
    return "Confidence unavailable";
  }

  return `${Math.round(confidence * 100)}% confidence`;
}

function formatSeconds(seconds: number): string {
  return `${Number(seconds.toFixed(1))}s`;
}

function createNextFrameIdMap(
  frameOptions: ReplayFrameView[],
): ReadonlyMap<string, string> {
  return new Map(
    frameOptions.flatMap((frame, index) => {
      const nextFrame = frameOptions[index + 1];

      if (nextFrame === undefined) {
        return [];
      }

      return [[frame.id, nextFrame.id]];
    }),
  );
}

function createTimingOptionView(
  option: DemoReplay["timing"]["options"][number],
): ReplayTimingOptionView {
  return {
    clearanceLabel: `${formatSeconds(option.playback_clearance_seconds)} clearance`,
    dwellLabel: `${formatSeconds(option.playback_dwell_seconds)} dwell`,
    frameIntervalLabel: `${option.frame_interval_ms}ms/frame`,
    frameIntervalMs: option.frame_interval_ms,
    label: option.label,
    mode: option.mode,
    providerRequirementLabel: option.requires_external_providers
      ? "Provider required"
      : "Local fallback ready",
  };
}

function createIncidentReportView(
  incident: DemoReplay["frames"][number]["assessment"]["incident"],
): IncidentReportView | null {
  const report = incident?.incident_report;

  if (report === undefined || report === null) {
    return null;
  }

  return {
    hazard: report.hazard,
    recommendedAction: report.recommended_action,
  };
}

function createAlertView(
  incident: DemoReplay["frames"][number]["assessment"]["incident"],
): AlertEventView | null {
  const alertEvent = incident?.alert_events?.[0];

  if (alertEvent === undefined) {
    return null;
  }

  return {
    transcript: alertEvent.alert_text,
  };
}

function createVerificationView(
  incident: DemoReplay["frames"][number]["assessment"]["incident"],
): ClearanceVerificationView | null {
  const verification = incident?.verification;

  if (verification === undefined || verification === null) {
    return null;
  }

  return {
    afterEvidenceFrameId: verification.after_evidence_frame_id,
    confidenceLabel: formatConfidence(verification.confidence),
    rationale: verification.rationale,
    verdictLabel: formatToken(verification.verdict),
  };
}

function createAuditPacketView(
  incident: DemoReplay["frames"][number]["assessment"]["incident"],
): AuditPacketView | null {
  const auditPacket = incident?.audit_packet;

  if (auditPacket === undefined || auditPacket === null) {
    return null;
  }

  return {
    afterFrameId: auditPacket.after_frame_id,
    afterTimestamp: auditPacket.after_timestamp,
    alertTranscript: auditPacket.alert_transcript,
    beforeFrameId: auditPacket.before_frame_id,
    beforeTimestamp: auditPacket.before_timestamp,
  };
}

function createReviewSampleView(
  incident: DemoReplay["frames"][number]["assessment"]["incident"],
): ReviewSampleView | null {
  const reviewSample = incident?.review_sample;

  if (reviewSample === undefined || reviewSample === null) {
    return null;
  }

  return {
    exportStatusLabel: formatToken(reviewSample.export_status),
    humanDecisionLabel: formatToken(reviewSample.human_decision),
    labels: reviewSample.labels.map(formatToken),
  };
}
