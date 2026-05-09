import type { ReactNode } from "react";
import { useEffect, useMemo, useRef, useState } from "react";

import { apiClient, getApiBaseUrl } from "./modules/api-client/client";
import type {
  DemoReplay,
  ObservedState,
  ProductContract,
} from "./modules/api-client/types";
import { resolveReplayImageUrl } from "./modules/demo-player/replay-assets";
import {
  createReplayImageAlt,
  createReplayViewModel,
  type ReplayFrameView,
  type ReplayTimingMode,
  type ReplayTimingOptionView,
  type ReplayViewModel,
  selectNextReplayFrameId,
  selectReplayFrame,
  selectReplayTiming,
} from "./modules/demo-player/replay-view";
import {
  type ContractSummary,
  createContractSummary,
} from "./modules/safety-ui/operations-summary";

type OperationsLoadState =
  | { status: "loading" }
  | {
      contract: ProductContract;
      replay: DemoReplay;
      status: "ready";
    }
  | {
      message: string;
      status: "error";
    };

const initialState: OperationsLoadState = { status: "loading" };

type DetailRow = {
  label: string;
  value: ReactNode;
};

type ProviderStatusRow = {
  detail: string;
  key: string;
  label: string;
  meta?: string;
  status: string;
};

/** RobotOps Sentinel operations application shell. */
function App() {
  const [loadState, setLoadState] = useState<OperationsLoadState>(initialState);
  const [activeFrameId, setActiveFrameId] = useState("");
  const [activeTimingMode, setActiveTimingMode] =
    useState<ReplayTimingMode | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackEpoch, setPlaybackEpoch] = useState(0);
  const playbackEpochRef = useRef(playbackEpoch);
  const replay = loadState.status === "ready" ? loadState.replay : null;
  const contractSummary =
    loadState.status === "ready"
      ? createContractSummary(loadState.contract)
      : null;
  const replayView = useMemo(
    () => (replay === null ? null : createReplayViewModel(replay)),
    [replay],
  );
  const activeReplayFrame =
    replayView === null ? null : selectReplayFrame(replayView, activeFrameId);
  const activeReplayTiming =
    replayView === null
      ? null
      : selectReplayTiming(replayView, activeTimingMode);

  useEffect(() => {
    if (!isPlaying || replayView === null || activeReplayTiming === null) {
      return;
    }

    playbackEpochRef.current = playbackEpoch;
    const nextFrameId = selectNextReplayFrameId(replayView, activeFrameId);

    if (nextFrameId === null) {
      setIsPlaying(false);
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setActiveFrameId(nextFrameId);
    }, activeReplayTiming.frameIntervalMs);

    return () => window.clearTimeout(timeoutId);
  }, [activeFrameId, activeReplayTiming, isPlaying, playbackEpoch, replayView]);

  useEffect(() => {
    const controller = new AbortController();

    async function loadOperationsData(requestController: AbortController) {
      const signal = requestController.signal;

      try {
        const [contractResult, replayResult] = await Promise.all([
          apiClient.GET("/api/product-contract", { signal }),
          apiClient.GET("/api/demo-replay", { signal }),
        ]);

        if (signal.aborted) {
          return;
        }

        if (contractResult.data === undefined) {
          setLoadState({
            message: describeApiLoadFailure(
              "Backend contract",
              contractResult.response.status,
              contractResult.error,
            ),
            status: "error",
          });
          return;
        }

        if (replayResult.data === undefined) {
          setLoadState({
            message: describeApiLoadFailure(
              "Demo replay",
              replayResult.response.status,
              replayResult.error,
            ),
            status: "error",
          });
          return;
        }

        const firstFrame = replayResult.data.frames[0];
        if (firstFrame === undefined) {
          setLoadState({
            message: "Demo replay has no frames",
            status: "error",
          });
          return;
        }

        setLoadState({
          contract: contractResult.data,
          replay: replayResult.data,
          status: "ready",
        });
        setActiveFrameId(firstFrame.id);
        setActiveTimingMode(replayResult.data.timing.default_mode);
        setIsPlaying(false);
      } catch (error: unknown) {
        if (signal.aborted || isAbortError(error)) {
          return;
        }

        requestController.abort();
        setLoadState({
          message: describeThrownContractError(error),
          status: "error",
        });
      }
    }

    void loadOperationsData(controller);

    return () => {
      controller.abort();
    };
  }, []);

  function restartReplay() {
    const firstFrame = replayView?.frameOptions[0];

    if (firstFrame === undefined) {
      return;
    }

    setActiveFrameId(firstFrame.id);
    setIsPlaying(true);
    setPlaybackEpoch((epoch) => epoch + 1);
  }

  function selectManualFrame(frameId: string) {
    setActiveFrameId(frameId);
    setIsPlaying(false);
  }

  return (
    <main className="operations-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">RobotOps Sentinel</p>
          <h1>{contractSummary?.referenceZoneName ?? "Critical zone"}</h1>
        </div>
        <div className="status-pill">Operations data: {loadState.status}</div>
      </header>

      <section className="workspace" aria-label="Robotics operations workspace">
        <div className="video-stage">
          {loadState.status === "ready" &&
          replayView !== null &&
          activeReplayFrame !== null ? (
            <ReplayStage
              activeFrameId={activeFrameId}
              activeFrame={activeReplayFrame}
              activeTiming={activeReplayTiming}
              activeTimingMode={activeTimingMode}
              isPlaying={isPlaying}
              onFrameSelect={selectManualFrame}
              onPlayingChange={setIsPlaying}
              onRestart={restartReplay}
              onTimingSelect={setActiveTimingMode}
              replayView={replayView}
            />
          ) : (
            <div
              className="camera-frame camera-frame--empty"
              role="img"
              aria-label="Emergency exit camera view loading"
            >
              <div className="timestamp">Awaiting replay</div>
            </div>
          )}
        </div>

        <aside className="incident-rail" aria-label="Incident state">
          {loadState.status === "loading" ? (
            <p className="muted">Connecting to {getApiBaseUrl()}</p>
          ) : null}

          {loadState.status === "error" ? (
            <div className="alert-block">
              <h2>{loadState.message}</h2>
              <p>{getApiBaseUrl()}</p>
            </div>
          ) : null}

          {loadState.status === "ready" && contractSummary !== null ? (
            <ContractPanel
              activeFrame={activeReplayFrame}
              contract={loadState.contract}
              summary={contractSummary}
            />
          ) : null}
        </aside>
      </section>
    </main>
  );
}

function describeApiLoadFailure(
  resourceName: string,
  status: number,
  error: unknown,
): string {
  const detail = describeUnknownError(error);

  if (detail.length === 0) {
    return `${resourceName} unavailable (${status})`;
  }

  return `${resourceName} unavailable (${status}): ${detail}`;
}

function describeThrownContractError(error: unknown): string {
  const detail = describeUnknownError(error);

  if (detail.length === 0) {
    return "Backend contract request failed";
  }

  return `Backend contract request failed: ${detail}`;
}

function describeUnknownError(error: unknown): string {
  if (typeof error === "string") {
    return error;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "";
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

function ReplayStage({
  activeFrameId,
  activeFrame,
  activeTiming,
  activeTimingMode,
  isPlaying,
  onFrameSelect,
  onPlayingChange,
  onRestart,
  onTimingSelect,
  replayView,
}: {
  activeFrameId: string;
  activeFrame: ReplayFrameView;
  activeTiming: ReplayTimingOptionView | null;
  activeTimingMode: ReplayTimingMode | null;
  isPlaying: boolean;
  onFrameSelect: (frameId: string) => void;
  onPlayingChange: (isPlaying: boolean) => void;
  onRestart: () => void;
  onTimingSelect: (timingMode: ReplayTimingMode) => void;
  replayView: ReplayViewModel;
}) {
  return (
    <section aria-label={replayView.replayName} className="replay-stage">
      <div
        className={`camera-frame ${getCameraFrameClass(activeFrame.observedState)}`}
      >
        <img
          alt={createReplayImageAlt(replayView, activeFrame)}
          className="replay-image"
          src={resolveReplayImageUrl(activeFrame.imageRef)}
        />
        <div className="zone-outline" style={replayView.zoneBox}>
          <span>{replayView.zoneName}</span>
        </div>
        <ObservationMarker observedState={activeFrame.observedState} />
        <div className="timestamp">{activeFrame.timestamp}</div>
      </div>

      {activeTiming !== null ? (
        <div className="playback-bar">
          <div className="playback-status">
            <strong>{activeTiming.label}</strong>
            <span>
              {activeTiming.frameIntervalLabel} · {activeTiming.dwellLabel} ·{" "}
              {activeTiming.clearanceLabel}
            </span>
          </div>
          <div className="playback-actions">
            <button onClick={onRestart} type="button">
              Restart
            </button>
            <button onClick={() => onPlayingChange(!isPlaying)} type="button">
              {isPlaying ? "Pause" : "Play"}
            </button>
          </div>
        </div>
      ) : null}

      <fieldset className="timing-controls">
        <legend className="visually-hidden">Demo timing</legend>
        {replayView.timingOptions.map((timing) => (
          <button
            aria-pressed={timing.mode === activeTimingMode}
            className="timing-control"
            key={timing.mode}
            onClick={() => onTimingSelect(timing.mode)}
            type="button"
          >
            <strong>{timing.label}</strong>
            <span>{timing.frameIntervalLabel}</span>
            <small>{timing.providerRequirementLabel}</small>
          </button>
        ))}
      </fieldset>

      <fieldset className="replay-controls">
        <legend className="visually-hidden">Replay frames</legend>
        {replayView.frameOptions.map((frame) => (
          <button
            aria-pressed={frame.id === activeFrameId}
            className="replay-control"
            key={frame.id}
            onClick={() => onFrameSelect(frame.id)}
            type="button"
          >
            <span>
              {frame.label}
              <small>{frame.dwellLabel}</small>
            </span>
            <strong>
              {frame.observationLabel}
              <small>{frame.confidenceLabel}</small>
            </strong>
          </button>
        ))}
      </fieldset>
    </section>
  );
}

function getCameraFrameClass(observedState: ObservedState): string {
  switch (observedState) {
    case "clear":
      return "camera-frame--clear";
    case "blocked":
      return "camera-frame--blocked";
    case "uncertain":
      return "camera-frame--uncertain";
    case "camera_unavailable":
      return "camera-frame--unavailable";
  }
}

function ObservationMarker({
  observedState,
}: {
  observedState: ObservedState;
}) {
  switch (observedState) {
    case "clear":
      return <div className="frame-marker frame-marker--clear">Clear path</div>;
    case "blocked":
      return (
        <div className="frame-marker frame-marker--blocked">Zone overlap</div>
      );
    case "uncertain":
      return (
        <div className="frame-marker frame-marker--uncertain">
          Review needed
        </div>
      );
    case "camera_unavailable":
      return (
        <div className="frame-marker frame-marker--unavailable">
          Feed unavailable
        </div>
      );
  }
}

function ContractPanel({
  activeFrame,
  contract,
  summary,
}: {
  activeFrame: ReplayFrameView | null;
  contract: ProductContract;
  summary: ContractSummary;
}) {
  const incidentReport = activeFrame?.incidentReport ?? null;

  return (
    <>
      <section className="panel-section">
        <p className="eyebrow">Primary workflow</p>
        <h2>{summary.primaryWorkflowLabel}</h2>
        <dl className="incident-facts">
          <div>
            <dt>Zone</dt>
            <dd>{summary.referenceZoneName}</dd>
          </div>
          <div>
            <dt>Observed</dt>
            <dd>
              {activeFrame?.observationLabel ??
                summary.referenceObservationState}
            </dd>
          </div>
          <div>
            <dt>Incident</dt>
            <dd>
              {activeFrame?.incidentStateLabel ??
                summary.referenceIncidentState}
            </dd>
          </div>
          <div>
            <dt>Severity</dt>
            <dd>
              {activeFrame?.incidentSeverity ??
                contract.reference_incident.severity}
            </dd>
          </div>
        </dl>
      </section>

      {activeFrame !== null ? (
        <section className="panel-section">
          <p className="eyebrow">Policy assessment</p>
          <h2>{activeFrame.incidentStateLabel}</h2>
          <p className="assessment-reason">{activeFrame.policyReason}</p>
          {incidentReport !== null ? (
            <DetailList
              rows={[
                { label: "Hazard", value: incidentReport.hazard },
                { label: "Response", value: incidentReport.recommendedAction },
              ]}
            />
          ) : null}
          {activeFrame.alert !== null ? (
            <DetailList
              rows={[
                { label: "Alert", value: activeFrame.alert.transcript },
                { label: "Provider", value: activeFrame.alert.providerLabel },
                ...(activeFrame.alert.audioRef === null
                  ? []
                  : [{ label: "Audio", value: activeFrame.alert.audioRef }]),
              ]}
            />
          ) : null}
          {activeFrame.verification !== null ? (
            <DetailList
              rows={[
                {
                  label: "Verification",
                  value: activeFrame.verification.verdictLabel,
                },
                {
                  label: "After frame",
                  value: activeFrame.verification.afterEvidenceFrameId,
                },
                {
                  label: "Confidence",
                  value: activeFrame.verification.confidenceLabel,
                },
                {
                  label: "Rationale",
                  value: activeFrame.verification.rationale,
                },
              ]}
            />
          ) : null}
          {activeFrame.auditPacket !== null ? (
            <DetailList
              rows={[
                {
                  label: "Before",
                  value: activeFrame.auditPacket.beforeFrameId,
                },
                {
                  label: "Before time",
                  value: activeFrame.auditPacket.beforeTimestamp,
                },
                { label: "After", value: activeFrame.auditPacket.afterFrameId },
                {
                  label: "After time",
                  value: activeFrame.auditPacket.afterTimestamp,
                },
                {
                  label: "Transcript",
                  value: activeFrame.auditPacket.alertTranscript,
                },
              ]}
            />
          ) : null}
          {activeFrame.reviewSample !== null ? (
            <DetailList
              rows={[
                {
                  label: "Review",
                  value: activeFrame.reviewSample.humanDecisionLabel,
                },
                {
                  label: "Export",
                  value: activeFrame.reviewSample.exportStatusLabel,
                },
                {
                  label: "Labels",
                  value: activeFrame.reviewSample.labels.join(", "),
                },
              ]}
            />
          ) : null}
        </section>
      ) : null}

      <section className="panel-section">
        <p className="eyebrow">Observation states</p>
        <ul className="token-list">
          {summary.observationStateLabels.map((label) => (
            <li key={label}>{label}</li>
          ))}
        </ul>
      </section>

      <section className="panel-section">
        <p className="eyebrow">Incident states</p>
        <ul className="token-list">
          {summary.incidentStateLabels.map((label) => (
            <li key={label}>{label}</li>
          ))}
        </ul>
      </section>

      <section className="panel-section">
        <p className="eyebrow">Provider selection</p>
        <ProviderStatusList
          rows={summary.providerIntegrationStatuses.map((status) => ({
            detail: status.detail,
            key: status.provider,
            label: status.providerLabel,
            meta: status.boundaryLabel,
            status: status.availabilityLabel,
          }))}
        />
      </section>

      <section className="panel-section">
        <p className="eyebrow">Voice providers</p>
        <ProviderStatusList
          rows={summary.voiceProviderStatuses.map((status) => ({
            detail: status.detail,
            key: status.provider,
            label: status.providerLabel,
            status: status.availabilityLabel,
          }))}
        />
      </section>

      <section className="panel-section">
        <p className="eyebrow">Review export</p>
        <ProviderStatusList
          rows={summary.reviewExportProviderStatuses.map((status) => ({
            detail: status.detail,
            key: status.provider,
            label: status.providerLabel,
            status: status.availabilityLabel,
          }))}
        />
      </section>

      <section className="panel-section">
        <p className="eyebrow">Backend provider boundaries</p>
        <ul className="boundary-list">
          {summary.providerBoundaryLabels.map((label) => (
            <li key={label}>{label}</li>
          ))}
        </ul>
      </section>
    </>
  );
}

function ProviderStatusList({ rows }: { rows: ProviderStatusRow[] }) {
  return (
    <ul className="provider-status-list">
      {rows.map((row) => (
        <li key={row.key}>
          <strong>{row.label}</strong>
          <span>
            {row.meta === undefined
              ? row.status
              : `${row.meta} - ${row.status}`}
          </span>
          <small>{row.detail}</small>
        </li>
      ))}
    </ul>
  );
}

function DetailList({ rows }: { rows: DetailRow[] }) {
  return (
    <dl className="incident-details">
      {rows.map((row) => (
        <div key={row.label}>
          <dt>{row.label}</dt>
          <dd>{row.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export default App;
