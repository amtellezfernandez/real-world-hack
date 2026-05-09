import { useEffect, useRef, useState } from "react";

type CameraStatus = "starting" | "live" | "blocked";
type RunPhase = "arming" | "moving" | "incident";

type MotionPose = {
  heading: number;
  x: number;
  y: number;
};

// ── Warehouse coordinate system ─────────────────────────────
// x: 0–80, y: 0–60.  Origin bottom-left.
// SVG transform: svgX = x * 10, svgY = (60 - y) * 10

function toSvgX(wx: number) { return wx * 10; }
function toSvgY(wy: number) { return (60 - wy) * 10; }

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
  { heading: 0,   x: 30, y: 10 },  // start: inside PICKING
  { heading: 0,   x: 30, y: 33 },  // enter aisle, moving north
  { heading: 270, x: 20, y: 33 },  // turn west through aisle
  { heading: 0,   x: 20, y: 50 },  // arrive in STORAGE
];

// Obstruction sits in the aisle blocking the westward path
const OBSTRUCTION = { x: 24, y: 33 };
const OBSTRUCTION_RADIUS = 1.8;

const START_POSE: MotionPose = { ...WAYPOINTS[0] };
const POSE_STEP = 0.25;

function App() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const poseRef = useRef(START_POSE);
  const phaseRef = useRef<RunPhase>("arming");
  const waypointIdxRef = useRef(0);

  const [cameraStatus, setCameraStatus] = useState<CameraStatus>("starting");
  const [cameraMessage, setCameraMessage] = useState("");
  const [cameraStream, setCameraStream] = useState<MediaStream | null>(null);
  const [phase, setPhase] = useState<RunPhase>("arming");
  const [pose, setPose] = useState(START_POSE);
  const [lastAlert, setLastAlert] = useState(
    "Awaiting camera. Robot will depart PICKING once live.",
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
          stream.getTracks().forEach((track) => track.stop());
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
        stream.getTracks().forEach((track) => track.stop());
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
    video.onloadedmetadata = () => { void video.play(); };
    void video.play();
  }, [cameraStream]);

  // ── Sync refs ──────────────────────────────────────────────
  useEffect(() => { phaseRef.current = phase; }, [phase]);
  useEffect(() => { poseRef.current = pose; }, [pose]);

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

  // ── Motion tick ────────────────────────────────────────────
  useEffect(() => {
    const interval = window.setInterval(() => {
      if (phaseRef.current !== "moving") return;

      const cur = poseRef.current;
      const wpIdx = waypointIdxRef.current;
      const nextWpIdx = wpIdx + 1;

      if (nextWpIdx >= WAYPOINTS.length) {
        // Reached final waypoint
        phaseRef.current = "incident";
        setPhase("incident");
        setLastAlert("Robot arrived at STORAGE.");
        return;
      }

      const target = WAYPOINTS[nextWpIdx];
      const dx = target.x - cur.x;
      const dy = target.y - cur.y;
      const dist = Math.sqrt(dx * dx + dy * dy);

      let nextPose: MotionPose;

      if (dist <= POSE_STEP) {
        // Snap to waypoint and advance
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

      // Check obstruction collision
      const odx = nextPose.x - OBSTRUCTION.x;
      const ody = nextPose.y - OBSTRUCTION.y;
      const oDist = Math.sqrt(odx * odx + ody * ody);

      if (oDist < OBSTRUCTION_RADIUS + 1) {
        phaseRef.current = "incident";
        setPhase("incident");
        setPose(nextPose);
        setLastAlert("⚠ Incident: Obstruction detected in aisle! Robot stopped.");
        return;
      }

      poseRef.current = nextPose;
      setPose(nextPose);
    }, 80);

    return () => window.clearInterval(interval);
  }, []);

  // ── Derived state ──────────────────────────────────────────
  const motionState =
    phase === "arming" ? "arming" : phase === "moving" ? "moving" : "incident";

  const displayCoord = `(${pose.x.toFixed(1)}, ${pose.y.toFixed(1)})`;

  function resetRun() {
    phaseRef.current = cameraStatus === "live" ? "moving" : "arming";
    poseRef.current = START_POSE;
    waypointIdxRef.current = 0;
    setPhase(cameraStatus === "live" ? "moving" : "arming");
    setPose(START_POSE);
    setLastAlert("Run reset. Robot returning to PICKING.");
  }

  // ── Render ─────────────────────────────────────────────────
  return (
    <main className="shell">
      <header className="header">
        <div className="title-block">
          <p className="eyebrow">Runtime</p>
          <h1>Warehouse incident console</h1>
          <p className="subhead">Left: camera evidence. Top right: warehouse plan. Bottom right: incident state.</p>
        </div>
        <div className="header-status">
          <span className="status-pill">Camera {cameraStatus === "live" ? "live" : cameraStatus}</span>
          <span className="status-pill">Motion {motionState}</span>
          <span className="status-pill">Loc {displayCoord}</span>
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
                <h2>Warehouse map</h2>
              </div>
              <span className="card-note">PICKING → STORAGE</span>
            </div>
            <WarehouseMap pose={pose} phase={phase} />
          </section>
        </section>

        <aside className="rail" aria-label="Incident rail">
          <section className="panel panel--compact">
            <p className="eyebrow">3. Incident</p>
            <h2 className={phase === "incident" ? "incident-title" : ""}>{motionState}</h2>
            <div className="metric-list metric-list--compact">
              <MetricRow label="Vision" value="model pending" />
              <MetricRow label="Heading" value={`${pose.heading.toFixed(0)}°`} />
              <MetricRow label="Position" value={displayCoord} />
              <MetricRow label="Zone" value={getZoneName(pose)} />
            </div>
            <button className="action-button" onClick={resetRun} type="button">
              Reset run
            </button>
            <p className={`note ${phase === "incident" ? "note--alert" : ""}`}>{lastAlert}</p>
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

function MetricRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

// ── SVG Warehouse Map ────────────────────────────────────────
function WarehouseMap({ pose, phase }: { pose: MotionPose; phase: RunPhase }) {
  // Robot position in SVG
  const rx = toSvgX(pose.x);
  const ry = toSvgY(pose.y);

  // Obstruction in SVG
  const ox = toSvgX(OBSTRUCTION.x);
  const oy = toSvgY(OBSTRUCTION.y);

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
      <rect x="20"  y="20"  width="370" height="190" fill="#ffffff" stroke="#111" strokeWidth="2" />
      <rect x="410" y="20"  width="370" height="190" fill="#ffffff" stroke="#111" strokeWidth="2" />
      <rect x="20"  y="230" width="760" height="70"  fill="#f0f0f0" stroke="#111" strokeWidth="2" />
      <rect x="20"  y="310" width="170" height="270" fill="#ffffff" stroke="#111" strokeWidth="2" />
      <rect x="210" y="310" width="170" height="270" fill="#eef6ee" stroke="#111" strokeWidth="2" />
      <rect x="410" y="310" width="370" height="270" fill="#ffffff" stroke="#111" strokeWidth="2" />

      {/* ── Zone labels ───────────────────────────────── */}
      <text x="205" y="52"  fill="#111" fontFamily="Arial, sans-serif" fontSize="16" fontWeight="700" textAnchor="middle">STORAGE</text>
      <text x="595" y="52"  fill="#111" fontFamily="Arial, sans-serif" fontSize="16" fontWeight="700" textAnchor="middle">RECEIVING</text>
      <text x="80"  y="270" fill="#666" fontFamily="Arial, sans-serif" fontSize="14" fontWeight="700" textAnchor="middle">AISLE</text>
      <text x="105" y="560" fill="#111" fontFamily="Arial, sans-serif" fontSize="14" fontWeight="700" textAnchor="middle">OPS</text>
      <text x="295" y="560" fill="#111" fontFamily="Arial, sans-serif" fontSize="14" fontWeight="700" textAnchor="middle">PICKING</text>
      <text x="595" y="560" fill="#111" fontFamily="Arial, sans-serif" fontSize="14" fontWeight="700" textAnchor="middle">SHIPPING</text>

      {/* ── Storage shelves (3 per row, 2 rows, centered at x=205) ─ */}
      {/* Each shelf: 80x20, gap 12. Total width: 80*3+12*2 = 264. Start x: 205-132 = 73 */}
      <g fill="#ffffff" stroke="#111" strokeWidth="1.5">
        <rect x="73"  y="80"  width="80" height="20" rx="2" />
        <rect x="165" y="80"  width="80" height="20" rx="2" />
        <rect x="257" y="80"  width="80" height="20" rx="2" />
        <rect x="73"  y="112" width="80" height="20" rx="2" />
        <rect x="165" y="112" width="80" height="20" rx="2" />
        <rect x="257" y="112" width="80" height="20" rx="2" />
      </g>

      {/* ── Receiving pallets (4 per row, 2 rows, centered at x=595) ─ */}
      {/* Each pallet: 40x40, gap 10. Total: 40*4+10*3 = 190. Start x: 595-95 = 500 */}
      <g fill="#ffffff" stroke="#111" strokeWidth="1.5">
        <rect x="500" y="70"  width="40" height="40" rx="2" />
        <rect x="550" y="70"  width="40" height="40" rx="2" />
        <rect x="600" y="70"  width="40" height="40" rx="2" />
        <rect x="650" y="70"  width="40" height="40" rx="2" />
        <rect x="500" y="120" width="40" height="40" rx="2" />
        <rect x="550" y="120" width="40" height="40" rx="2" />
        <rect x="600" y="120" width="40" height="40" rx="2" />
        <rect x="650" y="120" width="40" height="40" rx="2" />
      </g>

      {/* ── OPS equipment (2 items, centered at x=105) ─────────── */}
      {/* Items: 50x40 and 40x40, gap 10. Total: 100. Start x: 105-50=55 */}
      <g fill="#ffffff" stroke="#111" strokeWidth="1.5">
        <rect x="55"  y="410" width="50" height="40" rx="2" />
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

      {/* ── Planned route (dashed polyline) ───────────────────── */}
      <polyline
        points={WAYPOINTS.map(w => `${toSvgX(w.x)},${toSvgY(w.y)}`).join(" ")}
        fill="none"
        stroke="#aaa"
        strokeWidth="2"
        strokeDasharray="8 6"
      />

      {/* ── Obstruction (orange crate in aisle) ───────────────── */}
      <rect
        x={ox - 14} y={oy - 14}
        width="28" height="28"
        fill="#e67e22" stroke="#c0392b" strokeWidth="2" rx="3"
      />
      <text x={ox} y={oy + 5} fill="#fff" fontFamily="Arial, sans-serif" fontSize="12" fontWeight="700" textAnchor="middle">!</text>

      {/* ── Robot marker ──────────────────────────────────────── */}
      <g>
        {/* Green dot at start position */}
        <circle cx={toSvgX(START_POSE.x)} cy={toSvgY(START_POSE.y)} r="5" fill="#2ecc71" opacity="0.5" />

        {/* Robot body */}
        <rect
          x={rx - 12} y={ry - 12}
          width="24" height="24"
          fill={phase === "incident" ? "#e74c3c" : "#2980b9"}
          stroke="#fff" strokeWidth="2" rx="4"
        />
        <circle cx={rx} cy={ry} r="3" fill="#fff" />

        {/* Label */}
        <text x={rx} y={ry - 18} fill="#111" fontFamily="Arial, sans-serif" fontSize="10" fontWeight="700" textAnchor="middle">
          ROBOT
        </text>
      </g>
    </svg>
  );
}

function describeCameraError(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "Camera access was denied.";
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

export default App;
