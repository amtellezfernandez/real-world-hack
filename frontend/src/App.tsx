import type { ReactNode } from "react";
import { useMemo, useState } from "react";

import type { ProductContract } from "./modules/api-client/types";
import { resolveReplayImageUrl } from "./modules/demo-player/replay-assets";
import {
  LOCAL_DEMO_REPLAY,
  LOCAL_PRODUCT_CONTRACT,
} from "./modules/demo-data/local-demo";
import {
  createReplayImageAlt,
  createReplayViewModel,
  type ReplayFrameView,
  type ReplayViewModel,
  selectReplayFrame,
} from "./modules/demo-player/replay-view";
import {
  type ContractSummary,
  createContractSummary,
} from "./modules/safety-ui/operations-summary";

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

/** Robot audit shell. */
function App() {
  const [activeFrameId, setActiveFrameId] = useState(
    () => LOCAL_DEMO_REPLAY.frames[0]?.id ?? "",
  );
  const replay = LOCAL_DEMO_REPLAY;
  const contractSummary = useMemo(
    () => createContractSummary(LOCAL_PRODUCT_CONTRACT),
    [],
  );
  const replayView = useMemo(
    () => createReplayViewModel(replay),
    [replay],
  );
  const activeReplayFrame = selectReplayFrame(replayView, activeFrameId);

  function selectManualFrame(frameId: string) {
    setActiveFrameId(frameId);
  }

  return (
    <main className="operations-shell">
      <header className="topbar">
        <div className="brand-block">
          <p className="eyebrow">Runtime</p>
          <h1>Robot audit console</h1>
          <p className="subhead">
            {contractSummary?.referenceZoneName ?? "Loading robot environment"}
          </p>
        </div>
        <div className="status-strip">
          <span className="status-pill">Source local</span>
          <span className="status-pill">
            Evidence {activeReplayFrame?.label ?? "pending"}
          </span>
          <span className="status-pill">
            Review {contractSummary?.referenceEvidenceTimestamp ?? "pending"}
          </span>
        </div>
      </header>

      <section className="workspace" aria-label="Robot audit console">
        <div className="video-stage">
          <ReplayStage
            activeFrameId={activeFrameId}
            activeFrame={activeReplayFrame}
            onFrameSelect={selectManualFrame}
            replayView={replayView}
          />
        </div>

        <aside className="incident-rail" aria-label="Audit state">
          <ContractPanel
            activeFrame={activeReplayFrame}
            contract={LOCAL_PRODUCT_CONTRACT}
            summary={contractSummary}
          />
        </aside>
      </section>
    </main>
  );
}

function ReplayStage({
  activeFrameId,
  activeFrame,
  onFrameSelect,
  replayView,
}: {
  activeFrameId: string;
  activeFrame: ReplayFrameView;
  onFrameSelect: (frameId: string) => void;
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
        <div className="timestamp">{activeFrame.timestamp}</div>
      </div>

      <div className="evidence-strip" aria-label="Evidence frames">
        {replayView.frameOptions.map((frame) => (
          <button
            aria-pressed={frame.id === activeFrameId}
            className="evidence-control"
            key={frame.id}
            onClick={() => onFrameSelect(frame.id)}
            type="button"
          >
            <span>
              {frame.label}
              <small>{frame.timestamp}</small>
            </span>
            <strong>
              {frame.observationLabel}
              <small>{frame.confidenceLabel}</small>
            </strong>
          </button>
        ))}
      </div>
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
        <p className="eyebrow">Robot summary</p>
        <h2>{summary.primaryWorkflowLabel}</h2>
        <div className="status-chips" aria-label="Current system state">
          <span className="status-chip status-chip--live">Live</span>
          <span className="status-chip">Observed</span>
          <span className="status-chip">Verified</span>
          <span className="status-chip">Escalated</span>
        </div>
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
        <DetailList
          rows={[
            {
              label: "Platform",
              value: "Autodetected",
            },
            {
              label: "Scene",
              value: "Live feed",
            },
            {
              label: "Evidence",
              value: summary.referenceEvidenceTimestamp,
            },
          ]}
        />
      </section>

      {activeFrame !== null ? (
        <section className="panel-section">
          <p className="eyebrow">Selected evidence</p>
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
              rows={[{ label: "Alert", value: activeFrame.alert.transcript }]}
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
        <p className="eyebrow">Execution backends</p>
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
        <p className="eyebrow">Encord review</p>
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
        <p className="eyebrow">Integration boundaries</p>
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
