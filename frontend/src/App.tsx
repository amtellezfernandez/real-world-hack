import { useEffect, useMemo, useRef, useState } from "react";

type CameraStatus = "starting" | "live" | "blocked";
type RunPhase = "arming" | "moving" | "closed";

type MotionPose = {
  heading: number;
  x: number;
  y: number;
};

const START_POSE: MotionPose = {
  heading: 0,
  x: 26,
  y: 56,
};

const STOP_X = 46;
const POSE_STEP = 0.1;

function App() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const poseRef = useRef(START_POSE);
  const phaseRef = useRef<RunPhase>("arming");

  const [cameraStatus, setCameraStatus] = useState<CameraStatus>("starting");
  const [cameraMessage, setCameraMessage] = useState("");
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [phase, setPhase] = useState<RunPhase>("arming");
  const [pose, setPose] = useState(START_POSE);
  const [clock, setClock] = useState(() => Date.now());
  const [lastAlert, setLastAlert] = useState(
    "Webcam is live. The obstruction model slot is reserved for later.",
  );

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
          stream.getTracks().forEach((track) => track.stop());
          return;
        }

        setCameraStream(stream);
        setCameraStatus("live");
        setCameraMessage("");
      } catch (error: unknown) {
        if (!active) {
          return;
        }

        setCameraStatus("blocked");
        setCameraMessage(describeCameraError(error));
      }
    }

    void startCamera();

    return () => {
      active = false;

      if (stream !== null) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  useEffect(() => {
    const video = videoRef.current;

    if (cameraStream === null || video === null) {
      return;
    }

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
    phaseRef.current = phase;
  }, [phase]);

  useEffect(() => {
    poseRef.current = pose;
  }, [pose]);

  useEffect(() => {
    const clockTimer = window.setInterval(() => {
      setClock(Date.now());
    }, 500);

    return () => window.clearInterval(clockTimer);
  }, []);

  useEffect(() => {
    if (cameraStatus !== "live" || phase !== "arming") {
      return;
    }

    const armTimer = window.setTimeout(() => {
      if (phaseRef.current !== "arming") {
        return;
      }

      phaseRef.current = "moving";
      setPhase("moving");
      setLastAlert("Lane armed. Motion engaged.");
    }, 700);

    return () => window.clearTimeout(armTimer);
  }, [cameraStatus, phase]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      if (phaseRef.current !== "moving") {
        return;
      }

      const current = poseRef.current;
      const nextX = Math.min(current.x + POSE_STEP, STOP_X);
      const nextPose: MotionPose = {
        heading: 0,
        x: nextX,
        y: current.y,
      };

      poseRef.current = nextPose;
      setPose(nextPose);

      if (nextX >= STOP_X) {
        phaseRef.current = "closed";
        setPhase("closed");
        setLastAlert("Lane traversal finished.");
      }
    }, 180);

    return () => window.clearInterval(interval);
  }, []);

  const progress = useMemo(() => {
    const range = STOP_X - START_POSE.x;
    return clamp((pose.x - START_POSE.x) / range, 0, 1);
  }, [pose.x]);

  const laneState = "model pending";
  const motionState =
    phase === "arming" ? "arming" : phase === "moving" ? "moving" : "closed";

  function resetRun() {
    phaseRef.current = cameraStatus === "live" ? "moving" : "arming";
    poseRef.current = START_POSE;
    setPhase(cameraStatus === "live" ? "moving" : "arming");
    setPose(START_POSE);
    setLastAlert("Run reset. Obstruction model slot remains open.");
  }

  return (
    <main className="shell">
      <header className="header">
        <div className="title-block">
          <p className="eyebrow">Runtime</p>
          <h1>Warehouse incident console</h1>
          <p className="subhead">Left: camera evidence. Center: aisle plan. Right: incident state.</p>
        </div>
        <div className="header-status">
          <span className="status-pill">Camera {cameraStatus === "live" ? "live" : cameraStatus}</span>
          <span className="status-pill">Motion {motionState}</span>
          <span className="status-pill">Run {Math.round(progress * 100)}%</span>
        </div>
      </header>

      <section className="workspace" aria-label="Warehouse automation demo workspace">
        <section className="workspace-main">
          <section className="card card--camera">
            <div className="card-head">
              <div>
                <p className="eyebrow">1. Camera</p>
                <h2>Live evidence</h2>
              </div>
              <span className="card-note">Webcam feed</span>
            </div>
            <div className="camera-frame">
              <video
                ref={videoRef}
                className="camera-feed"
                autoPlay
                playsInline
                muted
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
                <h2>Straight aisle</h2>
              </div>
              <span className="card-note">Scripted motion</span>
            </div>
            <WarehouseMap pose={pose} />
          </section>
        </section>

        <aside className="rail" aria-label="Incident rail">
          <section className="panel panel--compact">
            <p className="eyebrow">3. Incident</p>
            <h2>{motionState}</h2>
            <div className="metric-list metric-list--compact">
              <MetricRow label="Vision" value="model pending" />
              <MetricRow label="Heading" value={`${pose.heading.toFixed(0)}°`} />
              <MetricRow label="Progress" value={`${Math.round(progress * 100)}%`} />
            </div>
            <button className="action-button" onClick={resetRun} type="button">
              Reset run
            </button>
            <p className="note">{lastAlert}</p>
          </section>
        </aside>
      </section>
    </main>
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

function WarehouseMap({ pose }: { pose: MotionPose }) {
  const lanePoint = toLanePoint(pose);

  return (
    <svg
      aria-label="Warehouse layout"
      className="warehouse-map"
      role="img"
      viewBox="0 0 1000 660"
      preserveAspectRatio="xMidYMid meet"
    >
      <rect x="0" y="0" width="1000" height="660" fill="#ffffff" />

      <rect x="36" y="36" width="430" height="250" fill="#ffffff" stroke="#111111" strokeWidth="2" />
      <rect x="496" y="36" width="468" height="220" fill="#ffffff" stroke="#111111" strokeWidth="2" />
      <rect x="36" y="316" width="928" height="64" fill="#ffffff" stroke="#111111" strokeWidth="2" />
      <rect x="36" y="410" width="214" height="214" fill="#ffffff" stroke="#111111" strokeWidth="2" />
      <rect x="262" y="410" width="214" height="214" fill="#ffffff" stroke="#111111" strokeWidth="2" />
      <rect x="496" y="316" width="468" height="308" fill="#ffffff" stroke="#111111" strokeWidth="2" />

      <text x="251" y="96" fill="#111111" fontFamily="Arial, sans-serif" fontSize="18" fontWeight="700" textAnchor="middle">
        STORAGE
      </text>
      <text x="730" y="96" fill="#111111" fontFamily="Arial, sans-serif" fontSize="18" fontWeight="700" textAnchor="middle">
        RECEIVING
      </text>
      <text x="500" y="355" fill="#111111" fontFamily="Arial, sans-serif" fontSize="16" fontWeight="700" textAnchor="middle">
        AISLE
      </text>
      <text x="143" y="534" fill="#111111" fontFamily="Arial, sans-serif" fontSize="16" fontWeight="700" textAnchor="middle">
        OPS
      </text>
      <text x="369" y="534" fill="#111111" fontFamily="Arial, sans-serif" fontSize="16" fontWeight="700" textAnchor="middle">
        PICKING
      </text>
      <text x="730" y="396" fill="#111111" fontFamily="Arial, sans-serif" fontSize="18" fontWeight="700" textAnchor="middle">
        SHIPPING
      </text>

      <line
        x1="220"
        x2="540"
        y1="348"
        y2="348"
        stroke="#111111"
        strokeDasharray="7 8"
        strokeWidth="2"
      />

      <g fill="#ffffff" stroke="#111111" strokeWidth="2">
        <rect x="100" y="136" width="76" height="26" rx="2" />
        <rect x="190" y="136" width="76" height="26" rx="2" />
        <rect x="280" y="136" width="76" height="26" rx="2" />
        <rect x="370" y="136" width="48" height="26" rx="2" />
        <rect x="100" y="174" width="76" height="26" rx="2" />
        <rect x="190" y="174" width="76" height="26" rx="2" />
        <rect x="280" y="174" width="76" height="26" rx="2" />
        <rect x="370" y="174" width="48" height="26" rx="2" />
      </g>

      <g fill="#ffffff" stroke="#111111" strokeWidth="2">
        <rect x="530" y="92" width="38" height="38" rx="2" />
        <rect x="582" y="92" width="38" height="38" rx="2" />
        <rect x="634" y="92" width="38" height="38" rx="2" />
        <rect x="686" y="92" width="38" height="38" rx="2" />
      </g>

      <g fill="#ffffff" stroke="#111111" strokeWidth="2">
        <rect x="530" y="336" width="38" height="38" rx="2" />
        <rect x="582" y="336" width="38" height="38" rx="2" />
        <rect x="634" y="336" width="38" height="38" rx="2" />
      </g>

      <g fill="#ffffff" stroke="#111111" strokeWidth="2">
        <rect x="82" y="452" width="82" height="52" rx="2" />
        <rect x="176" y="452" width="38" height="52" rx="2" />
      </g>

      <g fill="#ffffff" stroke="#111111" strokeWidth="2">
        <rect x="300" y="448" width="128" height="28" rx="2" />
      </g>

      <g fill="#ffffff" stroke="#111111" strokeWidth="2">
        <rect x="540" y="452" width="38" height="38" rx="2" />
        <rect x="592" y="452" width="38" height="38" rx="2" />
        <rect x="644" y="452" width="38" height="38" rx="2" />
        <rect x="696" y="452" width="38" height="38" rx="2" />
      </g>

      <line
        x1={lanePoint.x - 10}
        y1={lanePoint.y}
        x2={lanePoint.x + 10}
        y2={lanePoint.y}
        stroke="#ffffff"
        strokeWidth="3"
      />
      <line
        x1={lanePoint.x}
        y1={lanePoint.y - 10}
        x2={lanePoint.x}
        y2={lanePoint.y + 10}
        stroke="#ffffff"
        strokeWidth="3"
      />
      <rect x={lanePoint.x - 11} y={lanePoint.y - 11} width="22" height="22" fill="#111111" stroke="#ffffff" strokeWidth="2" />
    </svg>
  );
}

function toLanePoint(pose: MotionPose): { x: number; y: number } {
  const progress = clamp((pose.x - START_POSE.x) / (STOP_X - START_POSE.x), 0, 1);

  return {
    x: 220 + progress * 320,
    y: 348,
  };
}

function describeCameraError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return "Camera access was denied.";
}

function formatClock(clock: number): string {
  return new Date(clock).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

export default App;
