import { useEffect, useRef, useState } from "react";

type MotionPose = {
  heading: number;
  speed: number;
  x: number;
  y: number;
};

type CameraStatus = "starting" | "live" | "blocked";

type WarehouseZone = {
  label: string;
  state: "clear" | "blocked";
};

const initialPose: MotionPose = {
  heading: 90,
  speed: 0,
  x: 24,
  y: 76,
};

function App() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [cameraStatus, setCameraStatus] = useState<CameraStatus>("starting");
  const [cameraMessage, setCameraMessage] = useState("");
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [pose, setPose] = useState<MotionPose>(initialPose);
  const [trail, setTrail] = useState<MotionPose[]>([initialPose]);

  useEffect(() => {
    let active = true;
    let stream: MediaStream | null = null;

    async function startCamera() {
      if (!navigator.mediaDevices?.getUserMedia) {
        if (active) {
          setCameraStatus("blocked");
          setCameraMessage("Camera APIs are unavailable in this browser.");
        }
        return;
      }

      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: {
            facingMode: { ideal: "user" },
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
  }, [cameraStream, cameraStatus]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const step = event.shiftKey ? 4 : 2;
      let nextPose: MotionPose | null = null;

      switch (event.key) {
        case "ArrowUp":
        case "w":
        case "W":
          nextPose = movePose(pose, 0, -step, 0);
          break;
        case "ArrowDown":
        case "s":
        case "S":
          nextPose = movePose(pose, 0, step, 180);
          break;
        case "ArrowLeft":
        case "a":
        case "A":
          nextPose = movePose(pose, -step, 0, 270);
          break;
        case "ArrowRight":
        case "d":
        case "D":
          nextPose = movePose(pose, step, 0, 90);
          break;
        case "q":
        case "Q":
          nextPose = {
            ...pose,
            heading: wrapHeading(pose.heading - 15),
            speed: 0,
          };
          break;
        case "e":
        case "E":
          nextPose = {
            ...pose,
            heading: wrapHeading(pose.heading + 15),
            speed: 0,
          };
          break;
        case "r":
        case "R":
          nextPose = initialPose;
          break;
      }

      if (nextPose === null) {
        return;
      }

      event.preventDefault();
      setPose(nextPose);
      setTrail((previous) => [...previous.slice(-8), nextPose]);
    }

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [pose]);

  const zone = classifyWarehouseZone(pose);

  function centerRuntime() {
    setPose(initialPose);
    setTrail([initialPose]);
  }

  function dockRuntime() {
    const dockedPose: MotionPose = {
      heading: 90,
      speed: 0,
      x: 74,
      y: 22,
    };

    setPose(dockedPose);
    setTrail((previous) => [...previous.slice(-8), dockedPose]);
  }

  function parkRuntime() {
    const parkedPose: MotionPose = {
      heading: 180,
      speed: 0,
      x: 48,
      y: 74,
    };

    setPose(parkedPose);
    setTrail((previous) => [...previous.slice(-8), parkedPose]);
  }

  return (
    <main className="operations-shell">
      <header className="topbar">
        <div className="brand-block">
          <p className="eyebrow">Runtime</p>
          <h1>Laptop runtime</h1>
          <p className="subhead">Webcam feed and odometry on a warehouse plan</p>
        </div>
        <div className="status-strip">
          <span className="status-pill">
            Webcam{" "}
            {cameraStatus === "live"
              ? "live"
              : cameraStatus === "starting"
                ? "starting"
                : "blocked"}
          </span>
          <span className="status-pill">
            Odometry {pose.x.toFixed(1)} / {pose.y.toFixed(1)}
          </span>
          <span className="status-pill">{zone.label}</span>
        </div>
      </header>

      <section className="signal-strip" aria-label="Signal flow">
        <span className="flow-node">
          <span className="flow-node-label">Webcam</span>
          <span className="flow-node-value">
            {cameraStatus === "live"
              ? "Live"
              : cameraStatus === "starting"
                ? "Starting"
                : "Blocked"}
          </span>
        </span>
        <span className="flow-line" />
        <span className="flow-node">
          <span className="flow-node-label">Odometry</span>
          <span className="flow-node-value">
            {pose.x.toFixed(1)} / {pose.y.toFixed(1)}
          </span>
        </span>
        <span className="flow-line" />
        <span className="flow-node">
          <span className="flow-node-label">Floor plan</span>
          <span className="flow-node-value">{zone.state === "blocked" ? "Blocked" : "Clear"}</span>
        </span>
      </section>

      <section className="workspace" aria-label="Laptop runtime workspace">
        <section className="workspace-main">
          <section className="camera-panel">
            <div className="panel-head">
              <p className="eyebrow">Webcam</p>
              <div className="panel-meta">
                <span>
                  {cameraStatus === "live"
                    ? "Active"
                    : cameraStatus === "starting"
                      ? "Starting"
                      : "Unavailable"}
                </span>
                <span>Source laptop</span>
              </div>
            </div>
            <div className="camera-frame camera-frame--live">
              <video
                ref={videoRef}
                className="camera-feed"
                autoPlay
                playsInline
                muted
              />
              {cameraStatus !== "live" ? (
                <div className="camera-fallback">
                  <strong>Camera feed unavailable</strong>
                  <span>{cameraMessage || "Awaiting camera permission."}</span>
                </div>
              ) : null}
            </div>
          </section>

          <section className="map-panel">
            <div className="panel-head">
              <p className="eyebrow">Warehouse plan</p>
              <div className="panel-meta">
                <span>{zone.state === "blocked" ? "Blocked" : "Clear"}</span>
                <span>{zone.label}</span>
              </div>
            </div>
            <WarehouseMap pose={pose} trail={trail} zone={zone} />
          </section>
        </section>

        <aside className="incident-rail" aria-label="Runtime telemetry">
          <section className="panel-section">
            <p className="eyebrow">Telemetry</p>
            <h2>Live motion</h2>
            <div className="metric-list">
              <MetricRow label="Webcam" value={cameraStatus === "live" ? "Live" : cameraStatus === "starting" ? "Starting" : "Unavailable"} />
              <MetricRow label="Odometry" value={`${pose.x.toFixed(1)} / ${pose.y.toFixed(1)} @ ${pose.heading}°`} />
              <MetricRow label="Zone" value={zone.label} />
              <MetricRow label="X" value={`${pose.x.toFixed(1)}%`} />
              <MetricRow label="Y" value={`${pose.y.toFixed(1)}%`} />
              <MetricRow label="Heading" value={`${pose.heading}°`} />
              <MetricRow label="Speed" value={`${pose.speed.toFixed(1)} m/s`} />
            </div>
          </section>

          <section className="panel-section">
            <p className="eyebrow">Commands</p>
            <div className="action-grid">
              <button className="action-button" onClick={centerRuntime} type="button">
                Center
              </button>
              <button className="action-button" onClick={dockRuntime} type="button">
                Dock
              </button>
              <button className="action-button" onClick={parkRuntime} type="button">
                Park
              </button>
            </div>
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

function WarehouseMap({
  pose,
  trail,
  zone,
}: {
  pose: MotionPose;
  trail: MotionPose[];
  zone: WarehouseZone;
}) {
  const markerPoint = toMapPoint(pose);
  const trailPoints = trail
    .map((item) => {
      const point = toMapPoint(item);
      return `${point.x},${point.y}`;
    })
    .join(" ");

  return (
    <svg
      aria-label="Warehouse layout"
      className="warehouse-map"
      role="img"
      viewBox="0 0 1000 640"
      preserveAspectRatio="xMidYMid meet"
    >
      <rect x="0" y="0" width="1000" height="640" fill="#ffffff" />
      <rect x="56" y="40" width="888" height="560" fill="#ffffff" stroke="#111111" strokeWidth="3" />
      <rect x="56" y="40" width="420" height="380" fill="#f8f8f8" stroke="#111111" strokeWidth="3" />
      <rect x="476" y="40" width="468" height="200" fill="#fcfcfc" stroke="#111111" strokeWidth="3" />
      <rect x="476" y="240" width="468" height="190" fill="#fcfcfc" stroke="#111111" strokeWidth="3" />
      <rect x="476" y="430" width="468" height="170" fill="#f8f8f8" stroke="#111111" strokeWidth="3" />
      <rect x="56" y="420" width="228" height="180" fill="#fafafa" stroke="#111111" strokeWidth="3" />
      <rect x="284" y="420" width="192" height="180" fill="#f8f8f8" stroke="#111111" strokeWidth="3" />

      <text x="266" y="88" fill="#111111" fontFamily="Arial, sans-serif" fontSize="22" fontWeight="700" textAnchor="middle">
        STORAGE
      </text>
      <text x="710" y="88" fill="#111111" fontFamily="Arial, sans-serif" fontSize="22" fontWeight="700" textAnchor="middle">
        RECEIVING
      </text>
      <text x="710" y="286" fill="#111111" fontFamily="Arial, sans-serif" fontSize="22" fontWeight="700" textAnchor="middle">
        SHIPPING
      </text>
      <text x="380" y="516" fill="#111111" fontFamily="Arial, sans-serif" fontSize="20" fontWeight="700" textAnchor="middle">
        PICKING
      </text>
      <text x="170" y="514" fill="#111111" fontFamily="Arial, sans-serif" fontSize="18" fontWeight="700" textAnchor="middle">
        OPS
      </text>

      <g fill="#ffffff" stroke="#111111" strokeWidth="2">
        <rect x="110" y="112" width="86" height="28" rx="3" />
        <rect x="208" y="112" width="86" height="28" rx="3" />
        <rect x="306" y="112" width="86" height="28" rx="3" />
        <rect x="110" y="158" width="86" height="28" rx="3" />
        <rect x="208" y="158" width="86" height="28" rx="3" />
        <rect x="306" y="158" width="86" height="28" rx="3" />
        <rect x="110" y="204" width="86" height="28" rx="3" />
        <rect x="208" y="204" width="86" height="28" rx="3" />
        <rect x="306" y="204" width="86" height="28" rx="3" />
        <rect x="110" y="250" width="86" height="28" rx="3" />
        <rect x="208" y="250" width="86" height="28" rx="3" />
        <rect x="306" y="250" width="86" height="28" rx="3" />
      </g>

      <g fill="#ffffff" stroke="#111111" strokeWidth="2">
        <rect x="516" y="114" width="38" height="38" rx="3" />
        <rect x="564" y="114" width="38" height="38" rx="3" />
        <rect x="612" y="114" width="38" height="38" rx="3" />
        <rect x="660" y="114" width="38" height="38" rx="3" />
        <rect x="708" y="114" width="38" height="38" rx="3" />
        <rect x="756" y="114" width="38" height="38" rx="3" />
        <rect x="804" y="114" width="38" height="38" rx="3" />
        <rect x="852" y="114" width="38" height="38" rx="3" />
      </g>

      <g fill="#ffffff" stroke="#111111" strokeWidth="2">
        <rect x="516" y="266" width="38" height="38" rx="3" />
        <rect x="564" y="266" width="38" height="38" rx="3" />
        <rect x="612" y="266" width="38" height="38" rx="3" />
        <rect x="660" y="266" width="38" height="38" rx="3" />
      </g>

      <g fill="#ffffff" stroke="#111111" strokeWidth="2">
        <rect x="516" y="474" width="36" height="36" rx="3" />
        <rect x="564" y="474" width="36" height="36" rx="3" />
        <rect x="612" y="474" width="36" height="36" rx="3" />
        <rect x="660" y="474" width="36" height="36" rx="3" />
      </g>

      <g fill="#ffffff" stroke="#111111" strokeWidth="2">
        <rect x="108" y="484" width="84" height="58" rx="4" />
        <rect x="206" y="484" width="54" height="58" rx="4" />
      </g>

      <g fill="none" stroke="#111111" strokeWidth="2">
        <polyline points={trailPoints} />
      </g>

      <rect
        x={markerPoint.x - 9}
        y={markerPoint.y - 9}
        width="18"
        height="18"
        fill={zone.state === "blocked" ? "#111111" : "#ffffff"}
        stroke="#111111"
        strokeWidth="3"
      />
    </svg>
  );
}

function classifyWarehouseZone(pose: MotionPose): WarehouseZone {
  if (pose.x >= 66 && pose.y <= 34) {
    return { label: "Receiving dock", state: "blocked" };
  }

  if (pose.x < 38 && pose.y < 58) {
    return { label: "Storage", state: "clear" };
  }

  if (pose.x >= 38 && pose.x < 62 && pose.y >= 58) {
    return { label: "Picking", state: "clear" };
  }

  if (pose.x >= 38 && pose.x < 62 && pose.y < 58) {
    return { label: "Aisle", state: "clear" };
  }

  if (pose.x >= 62 && pose.y < 50) {
    return { label: "Receiving", state: "clear" };
  }

  if (pose.x >= 62 && pose.y >= 50) {
    return { label: "Shipping", state: "clear" };
  }

  return { label: "Ops", state: "clear" };
}

function movePose(
  pose: MotionPose,
  deltaX: number,
  deltaY: number,
  heading: number,
): MotionPose {
  return {
    heading,
    speed: Math.sqrt(deltaX ** 2 + deltaY ** 2) * 0.12,
    x: clamp(pose.x + deltaX, 4, 96),
    y: clamp(pose.y + deltaY, 4, 96),
  };
}

function toMapPoint(pose: MotionPose): { x: number; y: number } {
  return {
    x: 56 + (pose.x / 100) * 888,
    y: 40 + (pose.y / 100) * 560,
  };
}

function wrapHeading(value: number): number {
  const normalized = value % 360;
  return normalized < 0 ? normalized + 360 : normalized;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function describeCameraError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return "Camera access was denied.";
}

export default App;
