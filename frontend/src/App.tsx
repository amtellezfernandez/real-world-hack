import { useEffect, useRef, useState } from "react";

import { apiClient } from "./modules/api-client/client";
import type {
  GeminiObjectDetection,
  GeminiSemanticStatusResult,
} from "./modules/api-client/types";

type CameraStatus = "starting" | "live" | "blocked";
type RunPhase = "arming" | "moving" | "blocked" | "closed";

type DetectionState = {
  detections: GeminiObjectDetection[];
  message: string | null;
  status: "warming" | "clear" | "detected" | "error";
};

type OverlayFrame = {
  height: number;
  left: number;
  top: number;
  width: number;
};

type MutableBooleanRef = {
  current: boolean;
};

type MutableNumberRef = {
  current: number;
};

type MotionPose = {
  heading: number;
  x: number;
  y: number;
};

function firstWaypoint(waypoints: MotionPose[]): MotionPose {
  const waypoint = waypoints[0];
  if (waypoint === undefined) {
    throw new Error("At least one waypoint is required");
  }

  return { ...waypoint };
}

function toSvgX(wx: number) {
  return wx * 10;
}

function toSvgY(wy: number) {
  return (60 - wy) * 10;
}

// ── Warehouse zones (warehouse coords) ──────────────────────
// STORAGE:   x 2–39, y 38–58
// RECEIVING: x 41–78, y 38–58
// AISLE:     x 2–78, y 30–37
// OPS:       x 2–19, y 2–29
// PICKING:   x 21–38, y 2–29
// SHIPPING:  x 41–78, y 2–29

// ── Robot path: PICKING → AISLE → STORAGE ───────────────────
// Waypoints the robot follows in order (warehouse coords)
const WAYPOINTS: MotionPose[] = [
  { heading: 0, x: 30, y: 10 }, // start: inside PICKING
  { heading: 0, x: 30, y: 33 }, // enter aisle, moving north
  { heading: 270, x: 20, y: 33 }, // turn west through aisle
  { heading: 0, x: 20, y: 50 }, // arrive in STORAGE
];

const START_POSE: MotionPose = firstWaypoint(WAYPOINTS);
const POSE_STEP = 0.18;
const MOTION_TICK_MS = 95;
const DETECTION_INTERVAL_MS = 100;
const SEMANTIC_STATUS_INTERVAL_MS = 750;
const SEMANTIC_BLOCKED_CONFIRMATIONS = 1;
const SEMANTIC_CLEAR_CONFIRMATIONS = 2;
const DETECTION_FRAME_WIDTH = 640;
const DETECTION_IMAGE_QUALITY = 0.72;
const EMPTY_DETECTION_STATE: DetectionState = {
  detections: [],
  message: null,
  status: "warming",
};

function App() {
  const cameraFrameRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const poseRef = useRef(START_POSE);
  const phaseRef = useRef<RunPhase>("arming");
  const waypointIdxRef = useRef(0);
  const detectionInFlightRef = useRef(false);
  const semanticStatusInFlightRef = useRef(false);
  const semanticBlockedCountRef = useRef(0);
  const semanticClearCountRef = useRef(0);
  const liveIncidentExportInFlightRef = useRef(false);
  const liveIncidentOpenRef = useRef(false);

  const [cameraStatus, setCameraStatus] = useState<CameraStatus>("starting");
  const [cameraMessage, setCameraMessage] = useState("");
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [detectionState, setDetectionState] = useState<DetectionState>(
    EMPTY_DETECTION_STATE,
  );
  const [overlayFrame, setOverlayFrame] = useState<OverlayFrame | null>(null);
  const [semanticStatus, setSemanticStatus] =
    useState<GeminiSemanticStatusResult | null>(null);
  const [phase, setPhase] = useState<RunPhase>("arming");
  const [pose, setPose] = useState(START_POSE);
  const [lastAlert, setLastAlert] = useState(
    "Awaiting camera. Gemini perception will start once live.",
  );

  // ── Camera setup ───────────────────────────────────────────
  useEffect(() => {
    let active = true;
    let stream: MediaStream | null = null;

    async function startCamera() {
      if (!navigator.mediaDevices?.getUserMedia) {
        if (active) {
          setCameraStatus("blocked");
          setCameraMessage("Camera access is unavailable in this browser.");
        }
        return;
      }

      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: {
            facingMode: { ideal: "environment" },
            frameRate: { ideal: 30, max: 30 },
            width: { ideal: 960 },
            height: { ideal: 540 },
          },
        });

        if (!active) {
          stream.getTracks().forEach((track) => {
            track.stop();
          });
          return;
        }

        setCameraStream(stream);
        setCameraStatus("live");
        setCameraMessage("");
      } catch (error: unknown) {
        if (!active) return;
        setCameraStatus("blocked");
        setCameraMessage(describeCameraError(error));
      }
    }

    void startCamera();

    return () => {
      active = false;
      if (stream !== null) {
        stream.getTracks().forEach((track) => {
          track.stop();
        });
      }
    };
  }, []);

  useEffect(() => {
    const video = videoRef.current;
    if (cameraStream === null || video === null) return;
    video.srcObject = cameraStream;
    video.muted = true;
    video.playsInline = true;
    video.autoplay = true;
    video.onloadedmetadata = () => {
      void video.play();
    };
    void video.play();
  }, [cameraStream]);

  useEffect(() => {
    const video = videoRef.current;
    const cameraFrame = cameraFrameRef.current;

    if (video === null || cameraFrame === null) return;

    const cameraFrameElement = cameraFrame;
    const videoElement = video;

    function updateOverlayFrame() {
      const nextOverlayFrame = calculateOverlayFrame(
        cameraFrameElement,
        videoElement,
      );
      setOverlayFrame((current) =>
        overlayFramesEqual(current, nextOverlayFrame)
          ? current
          : nextOverlayFrame,
      );
    }

    updateOverlayFrame();
    videoElement.addEventListener("loadedmetadata", updateOverlayFrame);
    const resizeObserver = new ResizeObserver(updateOverlayFrame);
    resizeObserver.observe(cameraFrameElement);

    return () => {
      videoElement.removeEventListener("loadedmetadata", updateOverlayFrame);
      resizeObserver.disconnect();
    };
  }, []);

  // ── Sync refs ──────────────────────────────────────────────
  useEffect(() => {
    phaseRef.current = phase;
  }, [phase]);
  useEffect(() => {
    poseRef.current = pose;
  }, [pose]);

  // ── Arm → Moving after camera goes live ────────────────────
  useEffect(() => {
    if (cameraStatus !== "live" || phase !== "arming") return;

    const armTimer = window.setTimeout(() => {
      if (phaseRef.current !== "arming") return;
      phaseRef.current = "moving";
      waypointIdxRef.current = 0;
      setPhase("moving");
      setLastAlert("Robot departing PICKING zone. Heading toward STORAGE.");
    }, 700);

    return () => window.clearTimeout(armTimer);
  }, [cameraStatus, phase]);

  useEffect(() => {
    if (cameraStatus !== "live") {
      setDetectionState((current) =>
        detectionStatesEqual(current, EMPTY_DETECTION_STATE)
          ? current
          : EMPTY_DETECTION_STATE,
      );
      return;
    }

    let active = true;
    const abortController = new AbortController();

    async function detectCurrentFrame() {
      if (detectionInFlightRef.current) return;

      const video = videoRef.current;
      const canvas = canvasRef.current;

      if (
        video === null ||
        canvas === null ||
        video.videoWidth === 0 ||
        video.videoHeight === 0
      ) {
        return;
      }

      detectionInFlightRef.current = true;

      try {
        const image = captureVideoFrame(video, canvas);
        const { data, error, response } = await apiClient.POST(
          "/api/perception/detect",
          {
            body: {
              image_base64: image.base64,
              mime_type: image.mimeType,
            },
            signal: abortController.signal,
          },
        );

        if (!active) return;

        if (data === undefined || error !== undefined) {
          throw new Error(`Gemini detection failed with ${response.status}`);
        }

        const detections = data.detections ?? [];
        const nextDetectionState: DetectionState = {
          detections,
          message: null,
          status: detections.length === 0 ? "clear" : "detected",
        };
        setDetectionState((current) =>
          detectionStatesEqual(current, nextDetectionState)
            ? current
            : nextDetectionState,
        );
      } catch (error: unknown) {
        if (!active) return;

        const nextDetectionState: DetectionState = {
          detections: [],
          message: describeDetectionError(error),
          status: "error",
        };
        setDetectionState((current) =>
          detectionStatesEqual(current, nextDetectionState)
            ? current
            : nextDetectionState,
        );
      } finally {
        detectionInFlightRef.current = false;
      }
    }

    void detectCurrentFrame();
    const detectionTimer = window.setInterval(() => {
      void detectCurrentFrame();
    }, DETECTION_INTERVAL_MS);

    return () => {
      active = false;
      abortController.abort();
      detectionInFlightRef.current = false;
      window.clearInterval(detectionTimer);
    };
  }, [cameraStatus]);

  useEffect(() => {
    if (cameraStatus !== "live") return;

    let active = true;
    const abortController = new AbortController();

    async function describeCurrentFrame() {
      if (semanticStatusInFlightRef.current) return;

      const video = videoRef.current;
      const canvas = canvasRef.current;

      if (
        video === null ||
        canvas === null ||
        video.videoWidth === 0 ||
        video.videoHeight === 0
      ) {
        return;
      }

      semanticStatusInFlightRef.current = true;

      try {
        const image = captureVideoFrame(video, canvas);
        const { data, error, response } = await apiClient.POST(
          "/api/perception/semantic-status",
          {
            body: {
              image_base64: image.base64,
              mime_type: image.mimeType,
            },
            signal: abortController.signal,
          },
        );

        if (!active) return;

        if (data === undefined || error !== undefined) {
          throw new Error(
            `Gemini semantic status failed with ${response.status}`,
          );
        }

        const confirmedSemanticState = updateSemanticStateConfirmation({
          blockedCountRef: semanticBlockedCountRef,
          clearCountRef: semanticClearCountRef,
          status: data.status,
        });

        if (confirmedSemanticState === "pending") {
          setSemanticStatus(data.status);
          return;
        }

        setSemanticStatus(data.status);

        if (confirmedSemanticState === "blocked") {
          if (!liveIncidentOpenRef.current) {
            void signalLiveIncident({
              imageDataUrl: toImageDataUrl(image),
              kind: "open",
              liveIncidentExportInFlightRef,
              liveIncidentOpenRef,
              status: data.status,
            });
          }

          phaseRef.current = "blocked";
          setPhase("blocked");
          setLastAlert(
            `Blocked by ${data.status.blocking_object ?? "unknown object"}. ${data.status.rationale}`,
          );
        } else if (
          phaseRef.current !== "moving" &&
          phaseRef.current !== "closed"
        ) {
          if (liveIncidentOpenRef.current) {
            void signalLiveIncident({
              imageDataUrl: toImageDataUrl(image),
              kind: "resolve",
              liveIncidentExportInFlightRef,
              liveIncidentOpenRef,
              status: data.status,
            });
          }

          phaseRef.current = "moving";
          setPhase("moving");
          setLastAlert("Path clear according to Gemini Robotics-ER.");
        } else if (phaseRef.current !== "closed") {
          if (liveIncidentOpenRef.current) {
            void signalLiveIncident({
              imageDataUrl: toImageDataUrl(image),
              kind: "resolve",
              liveIncidentExportInFlightRef,
              liveIncidentOpenRef,
              status: data.status,
            });
          }

          setLastAlert("Path clear according to Gemini Robotics-ER.");
        }
      } catch (error: unknown) {
        if (!active) return;
        setLastAlert(describeDetectionError(error));
      } finally {
        semanticStatusInFlightRef.current = false;
      }
    }

    void describeCurrentFrame();
    const semanticStatusTimer = window.setInterval(() => {
      void describeCurrentFrame();
    }, SEMANTIC_STATUS_INTERVAL_MS);

    return () => {
      active = false;
      abortController.abort();
      semanticStatusInFlightRef.current = false;
      window.clearInterval(semanticStatusTimer);
    };
  }, [cameraStatus]);

  // ── Motion tick ────────────────────────────────────────────
  useEffect(() => {
    const interval = window.setInterval(() => {
      if (phaseRef.current !== "moving") return;

      const cur = poseRef.current;
      const wpIdx = waypointIdxRef.current;
      const nextWpIdx = wpIdx + 1;

      if (nextWpIdx >= WAYPOINTS.length) {
        phaseRef.current = "closed";
        setPhase("closed");
        setLastAlert("Robot arrived at STORAGE.");
        return;
      }

      const target = WAYPOINTS[nextWpIdx];
      if (target === undefined) {
        phaseRef.current = "closed";
        setPhase("closed");
        return;
      }
      const dx = target.x - cur.x;
      const dy = target.y - cur.y;
      const dist = Math.sqrt(dx * dx + dy * dy);

      let nextPose: MotionPose;

      if (dist <= POSE_STEP) {
        nextPose = { ...target };
        waypointIdxRef.current = nextWpIdx;
      } else {
        const ux = dx / dist;
        const uy = dy / dist;
        nextPose = {
          heading: target.heading,
          x: cur.x + ux * POSE_STEP,
          y: cur.y + uy * POSE_STEP,
        };
      }

      poseRef.current = nextPose;
      setPose(nextPose);
    }, MOTION_TICK_MS);

    return () => window.clearInterval(interval);
  }, []);

  // ── Derived state ──────────────────────────────────────────
  const motionState =
    phase === "arming"
      ? "arming"
      : phase === "moving"
        ? "moving"
        : phase === "blocked"
          ? "blocked"
          : "closed";

  const displayCoord = `(${pose.x.toFixed(1)}, ${pose.y.toFixed(1)})`;
  const visionStatus = formatVisionStatus(detectionState);
  const pathStatus =
    semanticStatus === null
      ? "warming up"
      : `${semanticStatus.state} ${Math.round(semanticStatus.confidence * 100)}%`;

  function resetRun() {
    phaseRef.current = cameraStatus === "live" ? "moving" : "arming";
    poseRef.current = START_POSE;
    waypointIdxRef.current = 0;
    setPhase(cameraStatus === "live" ? "moving" : "arming");
    setPose(START_POSE);
    setSemanticStatus(null);
    setLastAlert("Run reset. Robot returning to PICKING.");
  }

  // ── Render ─────────────────────────────────────────────────
  return (
    <main className="shell">
      <header className="header">
        <div className="title-block">
          <p className="eyebrow">Runtime</p>
          <h1>Warehouse incident console</h1>
          <p className="subhead">
            Left: camera evidence. Top right: warehouse plan. Bottom right:
            incident state.
          </p>
        </div>
        <div className="header-status">
          <span className="status-pill">
            Camera {cameraStatus === "live" ? "live" : cameraStatus}
          </span>
          <span className="status-pill">Motion {motionState}</span>
          <span className="status-pill">Loc {displayCoord}</span>
        </div>
      </header>

      <section
        className="workspace"
        aria-label="Warehouse automation demo workspace"
      >
        <section className="workspace-main">
          <section className="card card--camera">
            <div className="card-head">
              <div>
                <p className="eyebrow">1. Camera</p>
                <h2>Live evidence</h2>
              </div>
              <span className="card-note">Webcam feed</span>
            </div>
            <div className="camera-frame" ref={cameraFrameRef}>
              <video
                ref={videoRef}
                className="camera-feed"
                autoPlay
                playsInline
                muted
              />
              <canvas ref={canvasRef} className="analysis-canvas" />
              <DetectionOverlay
                detections={detectionState.detections}
                frame={overlayFrame}
              />
              {cameraStatus !== "live" ? (
                <div className="camera-overlay">
                  <p>{cameraMessage || "Awaiting camera permission."}</p>
                </div>
              ) : null}
            </div>
          </section>
          <section className="card card--plan">
            <div className="card-head">
              <div>
                <p className="eyebrow">2. Plan</p>
                <h2>Warehouse map</h2>
              </div>
              <span className="card-note">PICKING → STORAGE</span>
            </div>
            <WarehouseMap phase={phase} pose={pose} />
          </section>
        </section>

        <aside className="rail" aria-label="Incident rail">
          <section className="panel panel--compact">
            <p className="eyebrow">3. Incident</p>
            <h2 className={phase === "blocked" ? "incident-title" : ""}>
              {motionState}
            </h2>
            <div className="metric-list metric-list--compact">
              <MetricRow label="Vision" value={visionStatus} />
              <MetricRow label="Path" value={pathStatus} />
              <MetricRow
                label="Heading"
                value={`${pose.heading.toFixed(0)}°`}
              />
              <MetricRow label="Position" value={displayCoord} />
              <MetricRow label="Zone" value={getZoneName(pose)} />
            </div>
            <button className="action-button" onClick={resetRun} type="button">
              Reset run
            </button>
            <p className={`note ${getPathNoteClass(semanticStatus)}`}>
              {lastAlert}
            </p>
          </section>
        </aside>
      </section>
    </main>
  );
}

function getZoneName(pose: MotionPose): string {
  const { x, y } = pose;
  if (x >= 2 && x <= 39 && y >= 38) return "STORAGE";
  if (x >= 41 && y >= 38) return "RECEIVING";
  if (y >= 30 && y <= 37) return "AISLE";
  if (x >= 2 && x <= 19 && y < 30) return "OPS";
  if (x >= 21 && x <= 38 && y < 30) return "PICKING";
  if (x >= 41 && y < 30) return "SHIPPING";
  return "TRANSIT";
}

function DetectionOverlay({
  detections,
  frame,
}: {
  detections: GeminiObjectDetection[];
  frame: OverlayFrame | null;
}) {
  if (frame === null) return null;

  return (
    <div
      className="detection-overlay"
      aria-hidden="true"
      style={{
        height: `${frame.height}px`,
        left: `${frame.left}px`,
        top: `${frame.top}px`,
        width: `${frame.width}px`,
      }}
    >
      {detections.map((detection) => (
        <div
          className="detection-box"
          key={[
            detection.label,
            detection.box.x_min,
            detection.box.y_min,
            detection.box.x_max,
            detection.box.y_max,
          ].join("-")}
          style={{
            height: `${(detection.box.y_max - detection.box.y_min) * 100}%`,
            left: `${detection.box.x_min * 100}%`,
            top: `${detection.box.y_min * 100}%`,
            width: `${(detection.box.x_max - detection.box.x_min) * 100}%`,
          }}
        >
          <span>
            {detection.label}
            {detection.confidence === null || detection.confidence === undefined
              ? ""
              : ` ${Math.round(detection.confidence * 100)}%`}
          </span>
        </div>
      ))}
    </div>
  );
}

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

// ── SVG Warehouse Map ────────────────────────────────────────
function WarehouseMap({ phase, pose }: { phase: RunPhase; pose: MotionPose }) {
  const robotX = toSvgX(pose.x);
  const robotY = toSvgY(pose.y);
  const isMoving = phase === "moving";
  const statusColor = isMoving ? "#137333" : "#b42318";

  // Zone boundaries (SVG pixels) — derived from warehouse coords
  // viewBox 0 0 800 600
  // STORAGE:   x=20..390,  y=20..210   (center: 205, 115)
  // RECEIVING: x=410..780, y=20..210   (center: 595, 115)
  // AISLE:     x=20..780,  y=230..300  (center: 400, 265)
  // OPS:       x=20..190,  y=310..580  (center: 105, 445)
  // PICKING:   x=210..380, y=310..580  (center: 295, 445)
  // SHIPPING:  x=410..780, y=310..580  (center: 595, 445)

  return (
    <svg
      aria-label="Warehouse layout"
      className="warehouse-map"
      role="img"
      viewBox="0 0 800 600"
      preserveAspectRatio="xMidYMid meet"
    >
      {/* Background */}
      <rect x="0" y="0" width="800" height="600" fill="#f8f8f8" />

      {/* ── Zone rectangles ───────────────────────────── */}
      <rect
        x="20"
        y="20"
        width="370"
        height="190"
        fill="#ffffff"
        stroke="#111"
        strokeWidth="2"
      />
      <rect
        x="410"
        y="20"
        width="370"
        height="190"
        fill="#ffffff"
        stroke="#111"
        strokeWidth="2"
      />
      <rect
        x="20"
        y="230"
        width="760"
        height="70"
        fill="#f0f0f0"
        stroke="#111"
        strokeWidth="2"
      />
      <rect
        x="20"
        y="310"
        width="170"
        height="270"
        fill="#ffffff"
        stroke="#111"
        strokeWidth="2"
      />
      <rect
        x="210"
        y="310"
        width="170"
        height="270"
        fill="#eef6ee"
        stroke="#111"
        strokeWidth="2"
      />
      <rect
        x="410"
        y="310"
        width="370"
        height="270"
        fill="#ffffff"
        stroke="#111"
        strokeWidth="2"
      />

      {/* ── Zone labels ───────────────────────────────── */}
      <text
        x="205"
        y="52"
        fill="#111"
        fontFamily="Arial, sans-serif"
        fontSize="16"
        fontWeight="700"
        textAnchor="middle"
      >
        STORAGE
      </text>
      <text
        x="595"
        y="52"
        fill="#111"
        fontFamily="Arial, sans-serif"
        fontSize="16"
        fontWeight="700"
        textAnchor="middle"
      >
        RECEIVING
      </text>
      <text
        x="80"
        y="270"
        fill="#666"
        fontFamily="Arial, sans-serif"
        fontSize="14"
        fontWeight="700"
        textAnchor="middle"
      >
        AISLE
      </text>
      <text
        x="105"
        y="560"
        fill="#111"
        fontFamily="Arial, sans-serif"
        fontSize="14"
        fontWeight="700"
        textAnchor="middle"
      >
        OPS
      </text>
      <text
        x="295"
        y="560"
        fill="#111"
        fontFamily="Arial, sans-serif"
        fontSize="14"
        fontWeight="700"
        textAnchor="middle"
      >
        PICKING
      </text>
      <text
        x="595"
        y="560"
        fill="#111"
        fontFamily="Arial, sans-serif"
        fontSize="14"
        fontWeight="700"
        textAnchor="middle"
      >
        SHIPPING
      </text>

      {/* ── Storage shelves (3 per row, 2 rows, centered at x=205) ─ */}
      {/* Each shelf: 80x20, gap 12. Total width: 80*3+12*2 = 264. Start x: 205-132 = 73 */}
      <g fill="#ffffff" stroke="#111" strokeWidth="1.5">
        <rect x="73" y="80" width="80" height="20" rx="2" />
        <rect x="165" y="80" width="80" height="20" rx="2" />
        <rect x="257" y="80" width="80" height="20" rx="2" />
        <rect x="73" y="112" width="80" height="20" rx="2" />
        <rect x="165" y="112" width="80" height="20" rx="2" />
        <rect x="257" y="112" width="80" height="20" rx="2" />
      </g>

      {/* ── Receiving pallets (4 per row, 2 rows, centered at x=595) ─ */}
      {/* Each pallet: 40x40, gap 10. Total: 40*4+10*3 = 190. Start x: 595-95 = 500 */}
      <g fill="#ffffff" stroke="#111" strokeWidth="1.5">
        <rect x="500" y="70" width="40" height="40" rx="2" />
        <rect x="550" y="70" width="40" height="40" rx="2" />
        <rect x="600" y="70" width="40" height="40" rx="2" />
        <rect x="650" y="70" width="40" height="40" rx="2" />
        <rect x="500" y="120" width="40" height="40" rx="2" />
        <rect x="550" y="120" width="40" height="40" rx="2" />
        <rect x="600" y="120" width="40" height="40" rx="2" />
        <rect x="650" y="120" width="40" height="40" rx="2" />
      </g>

      {/* ── OPS equipment (2 items, centered at x=105) ─────────── */}
      {/* Items: 50x40 and 40x40, gap 10. Total: 100. Start x: 105-50=55 */}
      <g fill="#ffffff" stroke="#111" strokeWidth="1.5">
        <rect x="55" y="410" width="50" height="40" rx="2" />
        <rect x="115" y="410" width="40" height="40" rx="2" />
      </g>

      {/* ── Shipping pallets (4 per row, 2 rows, centered at x=595) */}
      {/* Same layout as receiving */}
      <g fill="#ffffff" stroke="#111" strokeWidth="1.5">
        <rect x="500" y="370" width="40" height="40" rx="2" />
        <rect x="550" y="370" width="40" height="40" rx="2" />
        <rect x="600" y="370" width="40" height="40" rx="2" />
        <rect x="650" y="370" width="40" height="40" rx="2" />
        <rect x="500" y="420" width="40" height="40" rx="2" />
        <rect x="550" y="420" width="40" height="40" rx="2" />
        <rect x="600" y="420" width="40" height="40" rx="2" />
        <rect x="650" y="420" width="40" height="40" rx="2" />
      </g>

      <polyline
        points={WAYPOINTS.map(
          (waypoint) => `${toSvgX(waypoint.x)},${toSvgY(waypoint.y)}`,
        ).join(" ")}
        fill="none"
        stroke={statusColor}
        strokeDasharray={isMoving ? "0" : "8 6"}
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="5"
        opacity="0.7"
      />

      <circle
        cx={robotX}
        cy={robotY}
        r="18"
        fill={statusColor}
        opacity={isMoving ? "0.14" : "0.22"}
      />

      <g aria-label="Robot position">
        <rect
          x={robotX - 12}
          y={robotY - 12}
          width="24"
          height="24"
          fill={statusColor}
          stroke="#ffffff"
          strokeWidth="2"
          rx="4"
        />
        <circle cx={robotX} cy={robotY} r="3" fill="#ffffff" />
      </g>
    </svg>
  );
}

function describeCameraError(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "Camera access was denied.";
}

function updateSemanticStateConfirmation({
  blockedCountRef,
  clearCountRef,
  status,
}: {
  blockedCountRef: MutableNumberRef;
  clearCountRef: MutableNumberRef;
  status: GeminiSemanticStatusResult;
}): "blocked" | "clear" | "pending" {
  if (status.state === "blocked") {
    blockedCountRef.current += 1;
    clearCountRef.current = 0;
    return blockedCountRef.current >= SEMANTIC_BLOCKED_CONFIRMATIONS
      ? "blocked"
      : "pending";
  }

  clearCountRef.current += 1;
  blockedCountRef.current = 0;
  return clearCountRef.current >= SEMANTIC_CLEAR_CONFIRMATIONS
    ? "clear"
    : "pending";
}

function getPathNoteClass(status: GeminiSemanticStatusResult | null): string {
  if (status === null) return "";
  return status.state === "blocked" ? "note--blocked" : "note--clear";
}

function describeDetectionError(error: unknown): string {
  if (error instanceof Error) {
    if (error.name === "AbortError") return "warming up";
    return error.message;
  }

  return "Gemini request failed";
}

function captureVideoFrame(
  video: HTMLVideoElement,
  canvas: HTMLCanvasElement,
): { base64: string; mimeType: "image/jpeg" } {
  const scale = DETECTION_FRAME_WIDTH / video.videoWidth;
  const targetHeight = Math.round(video.videoHeight * scale);

  if (canvas.width !== DETECTION_FRAME_WIDTH) {
    canvas.width = DETECTION_FRAME_WIDTH;
  }

  if (canvas.height !== targetHeight) {
    canvas.height = targetHeight;
  }

  const context = canvas.getContext("2d");
  if (context === null) {
    throw new Error("Canvas rendering context is unavailable");
  }

  context.drawImage(video, 0, 0, canvas.width, canvas.height);

  const mimeType = "image/jpeg";
  const dataUrl = canvas.toDataURL(mimeType, DETECTION_IMAGE_QUALITY);
  const prefix = `data:${mimeType};base64,`;

  if (!dataUrl.startsWith(prefix)) {
    throw new Error("Camera frame encoding failed");
  }

  return {
    base64: dataUrl.slice(prefix.length),
    mimeType,
  };
}

function toImageDataUrl(image: {
  base64: string;
  mimeType: "image/jpeg";
}): string {
  return `data:${image.mimeType};base64,${image.base64}`;
}

async function signalLiveIncident({
  imageDataUrl,
  kind,
  liveIncidentExportInFlightRef,
  liveIncidentOpenRef,
  status,
}: {
  imageDataUrl: string;
  kind: "open" | "resolve";
  liveIncidentExportInFlightRef: MutableBooleanRef;
  liveIncidentOpenRef: MutableBooleanRef;
  status: GeminiSemanticStatusResult;
}) {
  if (liveIncidentExportInFlightRef.current) return;

  liveIncidentExportInFlightRef.current = true;

  try {
    const path =
      kind === "open"
        ? "/api/demo-replay/incident/open"
        : "/api/demo-replay/incident/resolve";
    const { data, error, response } = await apiClient.POST(path, {
      body: {
        blocking_object: status.blocking_object,
        confidence: status.confidence,
        image_data_url: imageDataUrl,
        rationale: status.rationale,
      },
    });

    if (data === undefined || error !== undefined) {
      throw new Error(`Live incident ${kind} failed with ${response.status}`);
    }

    if (kind === "open") {
      liveIncidentOpenRef.current = true;
      console.info(
        "[encord-live-incident] blocked frame accepted",
        data.detail,
      );
      return;
    }

    liveIncidentOpenRef.current = false;
    console.info("[encord-live-incident] clear frame exported", data.detail);
  } catch (error: unknown) {
    console.error("[encord-live-incident]", error);
  } finally {
    liveIncidentExportInFlightRef.current = false;
  }
}

function formatVisionStatus(detectionState: DetectionState): string {
  if (detectionState.status === "warming") return "warming up";
  if (detectionState.status === "error") {
    return detectionState.message ?? "Gemini detection failed";
  }
  if (detectionState.status === "clear") return "clear";

  return `${detectionState.detections.length} object${detectionState.detections.length === 1 ? "" : "s"}`;
}

function detectionStatesEqual(
  left: DetectionState,
  right: DetectionState,
): boolean {
  return (
    left.status === right.status &&
    left.message === right.message &&
    detectionsEqual(left.detections, right.detections)
  );
}

function detectionsEqual(
  left: GeminiObjectDetection[],
  right: GeminiObjectDetection[],
): boolean {
  if (left.length !== right.length) return false;

  return left.every((detection, index) => {
    const other = right[index];
    if (other === undefined) return false;

    return (
      detection.label === other.label &&
      detection.confidence === other.confidence &&
      detection.box.x_min === other.box.x_min &&
      detection.box.y_min === other.box.y_min &&
      detection.box.x_max === other.box.x_max &&
      detection.box.y_max === other.box.y_max
    );
  });
}

function calculateOverlayFrame(
  cameraFrame: HTMLDivElement,
  video: HTMLVideoElement,
): OverlayFrame | null {
  if (video.videoWidth === 0 || video.videoHeight === 0) return null;

  const frameWidth = cameraFrame.clientWidth;
  const frameHeight = cameraFrame.clientHeight;
  const frameAspect = frameWidth / frameHeight;
  const videoAspect = video.videoWidth / video.videoHeight;

  if (videoAspect > frameAspect) {
    const height = frameWidth / videoAspect;
    return {
      height,
      left: 0,
      top: (frameHeight - height) / 2,
      width: frameWidth,
    };
  }

  const width = frameHeight * videoAspect;
  return {
    height: frameHeight,
    left: (frameWidth - width) / 2,
    top: 0,
    width,
  };
}

function overlayFramesEqual(
  left: OverlayFrame | null,
  right: OverlayFrame | null,
): boolean {
  if (left === null || right === null) return left === right;

  return (
    left.height === right.height &&
    left.left === right.left &&
    left.top === right.top &&
    left.width === right.width
  );
}

export default App;
