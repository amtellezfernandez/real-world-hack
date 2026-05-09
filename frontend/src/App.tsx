import { useEffect, useMemo, useRef, useState, type MutableRefObject } from "react";

type CameraStatus = "starting" | "live" | "blocked";
type RunPhase = "arming" | "moving" | "stopped" | "closed";

type MotionPose = {
  heading: number;
  x: number;
  y: number;
};

type EncordExportStatus = "idle" | "sending" | "exported" | "failed";
type LiveIncidentSignalStatus = "accepted" | "exported" | "failed";

const START_POSE: MotionPose = {
  heading: 0,
  x: 26,
  y: 56,
};

const STOP_X = 46;
const POSE_STEP = 0.1;
const BACKEND_BASE_URL =
  import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";
const LIVE_INCIDENT_OPEN_ENDPOINT = `${BACKEND_BASE_URL}/api/demo-replay/incident/open`;
const LIVE_INCIDENT_RESOLVE_ENDPOINT = `${BACKEND_BASE_URL}/api/demo-replay/incident/resolve`;
function App() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const poseRef = useRef(START_POSE);
  const phaseRef = useRef<RunPhase>("arming");
  const alarmContextRef = useRef<AudioContext | null>(null);
  const alarmTimerRef = useRef<number | null>(null);
  const captureTokenRef = useRef(0);

  const [cameraStatus, setCameraStatus] = useState<CameraStatus>("starting");
  const [cameraMessage, setCameraMessage] = useState("");
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [phase, setPhase] = useState<RunPhase>("arming");
  const [pose, setPose] = useState(START_POSE);
  const [clock, setClock] = useState(() => Date.now());
  const [encordStatus, setEncordStatus] = useState<EncordExportStatus>("idle");
  const [encordMessage, setEncordMessage] = useState("Waiting for the first incident.");
  const [lastAlert, setLastAlert] = useState(
    "Webcam is live. The incident model slot is reserved for later.",
  );
  const beforeFrameRef = useRef<string | null>(null);
  const afterFrameRef = useRef<string | null>(null);

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
    return () => {
      stopIncidentAlarm(alarmContextRef, alarmTimerRef);
    };
  }, []);

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

  const motionState =
    phase === "arming"
      ? "arming"
      : phase === "moving"
        ? "moving"
        : phase === "stopped"
          ? "stopped"
          : "closed";
  const incidentState = phase === "stopped" ? "open" : "clear";

  function resetRun() {
    captureTokenRef.current += 1;
    stopIncidentAlarm(alarmContextRef, alarmTimerRef);
    phaseRef.current = cameraStatus === "live" ? "moving" : "arming";
    poseRef.current = START_POSE;
    beforeFrameRef.current = null;
    afterFrameRef.current = null;
    setEncordStatus("idle");
    setEncordMessage("Waiting for the first incident.");
    setPhase(cameraStatus === "live" ? "moving" : "arming");
    setPose(START_POSE);
    setLastAlert("Run reset. Motion resumes from the current lane start.");
  }

  async function openIncident() {
    if (phaseRef.current !== "moving") {
      return;
    }

    captureTokenRef.current += 1;
    const captureToken = captureTokenRef.current;
    setEncordStatus("sending");
    setEncordMessage("Capturing the live before frame for Encord.");
    const capturedBefore = await captureLiveFrameUntilReady(
      videoRef.current,
      captureTokenRef,
      captureToken,
    );
    if (capturedBefore === null) {
      return;
    }

    setEncordStatus("sending");
    setEncordMessage("Sending before frame to the backend.");
    const result = await sendLiveIncidentSignal(LIVE_INCIDENT_OPEN_ENDPOINT, capturedBefore);
    if (result.status !== "accepted") {
      setEncordStatus("failed");
      setEncordMessage(result.detail);
      setLastAlert("Incident open failed.");
      return;
    }

    beforeFrameRef.current = capturedBefore;
    afterFrameRef.current = null;
    phaseRef.current = "stopped";
    setPhase("stopped");
    void startIncidentAlarm(alarmContextRef, alarmTimerRef, phaseRef);
    setEncordMessage("Before frame stored. Resolve the incident to export to Encord.");
    setLastAlert("Incident open. Motion paused.");
  }

  async function resolveIncident() {
    if (phaseRef.current !== "stopped") {
      return;
    }

    captureTokenRef.current += 1;
    const captureToken = captureTokenRef.current;
    setEncordStatus("sending");
    setEncordMessage("Capturing the live after frame and exporting to Encord.");
    const capturedAfter = await captureLiveFrameUntilReady(
      videoRef.current,
      captureTokenRef,
      captureToken,
    );
    if (capturedAfter === null) {
      return;
    }

    afterFrameRef.current = capturedAfter;
    phaseRef.current = "moving";
    setPhase("moving");
    stopIncidentAlarm(alarmContextRef, alarmTimerRef);
    setLastAlert("Incident cleared. Motion resumed.");

    if (beforeFrameRef.current === null) {
      setEncordStatus("failed");
      setEncordMessage("No before frame was captured. Resolve and reopen the incident.");
      return;
    }

    setEncordStatus("sending");
    setEncordMessage("Sending after frame to the backend and exporting to Encord.");
    const result = await sendLiveIncidentSignal(LIVE_INCIDENT_RESOLVE_ENDPOINT, capturedAfter);
    if (result.status === "exported") {
      setEncordStatus("exported");
      setEncordMessage(result.detail);
      beforeFrameRef.current = null;
      afterFrameRef.current = null;
      return;
    }

    setEncordStatus("failed");
    setEncordMessage(result.detail);
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
          <span className="status-pill">Incident {incidentState}</span>
          <span className="status-pill">Motion {motionState}</span>
          <span className="status-pill">Encord {encordStatus}</span>
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
              <MetricRow label="Export" value={encordStatus} />
            </div>
            <div className="action-row">
              <button className="action-button" onClick={openIncident} type="button">
                Open incident
              </button>
              <button className="action-button action-button--secondary" onClick={resolveIncident} type="button">
                Resolve
              </button>
            </div>
            <button className="action-button action-button--ghost" onClick={resetRun} type="button">
              Reset run
            </button>
            <p className="note">{lastAlert}</p>
            <p className="note">{encordMessage}</p>
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

async function sendLiveIncidentSignal(
  endpoint: "/api/demo-replay/incident/open" | "/api/demo-replay/incident/resolve",
  imageDataUrl: string,
) {
  try {
    const response = await fetch(endpoint, {
      body: JSON.stringify({
        image_data_url: imageDataUrl,
      }),
      headers: {
        "Content-Type": "application/json",
      },
      method: "POST",
    });

    const payload: { status?: LiveIncidentSignalStatus; detail?: string } =
      await response.json();

    if (!response.ok) {
      return {
        detail: payload.detail ?? `Request failed with status ${response.status}.`,
        status: "failed" as const,
      };
    }

    if (payload.status === "accepted" || payload.status === "exported") {
      return {
        detail: payload.detail ?? "Incident signal accepted.",
        status: payload.status,
      };
    }

    return {
      detail: payload.detail ?? "Incident signal failed.",
      status: "failed" as const,
    };
  } catch (error: unknown) {
    return {
      detail: describeError(error, "Incident signal failed."),
      status: "failed" as const,
    };
  }
}

async function startIncidentAlarm(
  alarmContextRef: MutableRefObject<AudioContext | null>,
  alarmTimerRef: MutableRefObject<number | null>,
  phaseRef: MutableRefObject<RunPhase>,
) {
  if (alarmTimerRef.current !== null) {
    return;
  }

  const audioContext = await getOrCreateAudioContext(alarmContextRef);
  if (audioContext === null) {
    return;
  }

  await audioContext.resume();

  const beep = () => {
    const context = alarmContextRef.current;
    if (context === null || phaseRef.current !== "stopped") {
      return;
    }

    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.type = "square";
    oscillator.frequency.value = 980;
    gain.gain.value = 0.0001;

    oscillator.connect(gain);
    gain.connect(context.destination);

    const startTime = context.currentTime;
    gain.gain.setValueAtTime(0.0001, startTime);
    gain.gain.exponentialRampToValueAtTime(0.08, startTime + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.0001, startTime + 0.14);

    oscillator.start(startTime);
    oscillator.stop(startTime + 0.16);
  };

  beep();
  alarmTimerRef.current = window.setInterval(beep, 420);
}

function stopIncidentAlarm(
  alarmContextRef: MutableRefObject<AudioContext | null>,
  alarmTimerRef: MutableRefObject<number | null>,
) {
  if (alarmTimerRef.current !== null) {
    window.clearInterval(alarmTimerRef.current);
    alarmTimerRef.current = null;
  }

  const context = alarmContextRef.current;
  if (context !== null && context.state === "running") {
    void context.suspend();
  }
}

async function getOrCreateAudioContext(
  alarmContextRef: MutableRefObject<AudioContext | null>,
) {
  if (alarmContextRef.current !== null) {
    return alarmContextRef.current;
  }

  const AudioContextCtor =
    window.AudioContext ?? (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;

  if (AudioContextCtor === undefined) {
    return null;
  }

  alarmContextRef.current = new AudioContextCtor();
  return alarmContextRef.current;
}

function captureLiveFrame(video: HTMLVideoElement | null): string | null {
  if (video === null || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
    return null;
  }

  const width = video.videoWidth;
  const height = video.videoHeight;
  if (width <= 0 || height <= 0) {
    return null;
  }

  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;

  const context = canvas.getContext("2d");
  if (context === null) {
    return null;
  }

  context.drawImage(video, 0, 0, width, height);
  return canvas.toDataURL("image/jpeg", 0.9);
}

async function captureLiveFrameUntilReady(
  video: HTMLVideoElement | null,
  captureTokenRef: MutableRefObject<number>,
  captureToken: number,
) {
  while (captureTokenRef.current === captureToken) {
    const frame = captureLiveFrame(video);
    if (frame !== null) {
      return frame;
    }

    await wait(60);
  }

  return null;
}

function wait(milliseconds: number) {
  return new Promise<void>((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
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

function describeError(error: unknown, fallback: string): string {
  if (error instanceof Error) {
    return error.message;
  }

  return fallback;
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
