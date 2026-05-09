import type { DemoReplay, ProductContract } from "../api-client/types";

export const LOCAL_PRODUCT_CONTRACT = {
  primary_workflow: "robot_workcell_obstruction",
  observation_states: ["clear", "blocked", "uncertain", "camera_unavailable"],
  incident_states: [
    "clear",
    "dwell",
    "incident_open",
    "alert_pending",
    "alert_broadcast",
    "clearing",
    "verified_clear",
    "closed",
    "uncertain",
  ],
  severity_levels: ["low", "medium", "high", "critical"],
  zone_types: ["emergency_exit", "walkway", "forklift_lane"],
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
      provider: "local_audio",
      boundary: "voice",
      availability: "available",
      detail: "Local audio alerts are available for approved incidents.",
    },
    {
      provider: "mistral",
      boundary: "voice",
      availability: "unconfigured",
      detail: "Mistral voice output is unavailable until credentials are configured.",
    },
    {
      provider: "elevenlabs",
      boundary: "voice",
      availability: "unconfigured",
      detail:
        "ElevenLabs voice output is unavailable until credentials are configured.",
    },
    {
      provider: "local_clearance",
      boundary: "verification",
      availability: "available",
      detail: "Local clearance verification is active for the demo.",
    },
    {
      provider: "gemini_robotics_er",
      boundary: "verification",
      availability: "unconfigured",
      detail:
        "Gemini Robotics-ER scaffold is unavailable until credentials are configured.",
    },
    {
      provider: "local_review",
      boundary: "review_export",
      availability: "available",
      detail: "Local review export queue is available.",
    },
    {
      provider: "encord",
      boundary: "review_export",
      availability: "unconfigured",
      detail:
        "Encord review export is unavailable until credentials are configured.",
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
      { x: 0.14, y: 0.82 },
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

export const LOCAL_DEMO_REPLAY = {
  id: "blocked-workcell-a2",
  name: "Blocked workcell replay",
  zone: LOCAL_PRODUCT_CONTRACT.reference_zone,
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
          review_sample: null,
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
          review_sample: null,
        },
      },
    },
    {
      id: "replay-frame-still-blocked",
      label: "Still blocked",
      evidence_frame: {
        id: "frame-workcell-still-blocked",
        source: "replay",
        timestamp: "2026-05-08T12:00:40Z",
        image_ref: "assets/demo/workcell-blocked.svg",
        annotations: [{ label: "zone_overlap", confidence: 0.92 }],
      },
      observation: {
        zone_id: "zone-workcell-a2",
        observed_state: "blocked",
        dwell_duration_seconds: 40,
        evidence_frame_id: "frame-workcell-still-blocked",
        confidence: 0.92,
      },
      assessment: {
        incident_state: "clearing",
        policy_reason:
          "After evidence still shows an obstruction in the critical zone.",
        incident: {
          id: "incident-zone-workcell-a2-frame-workcell-sustained-blocked",
          zone_id: "zone-workcell-a2",
          state: "clearing",
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
          verification: {
            verdict: "still_blocked",
            confidence: 0.92,
            rationale:
              "After evidence still shows an obstruction in the critical zone.",
            after_evidence_frame_id: "frame-workcell-still-blocked",
          },
          audit_packet: null,
          review_sample: null,
        },
      },
    },
    {
      id: "replay-frame-verified-clear",
      label: "Verified clear",
      evidence_frame: {
        id: "frame-workcell-after-clear",
        source: "replay",
        timestamp: "2026-05-08T12:00:45Z",
        image_ref: "assets/demo/workcell-clear.svg",
        annotations: [{ label: "zone_clear", confidence: 0.97 }],
      },
      observation: {
        zone_id: "zone-workcell-a2",
        observed_state: "clear",
        dwell_duration_seconds: 0,
        evidence_frame_id: "frame-workcell-after-clear",
        confidence: 0.97,
      },
      assessment: {
        incident_state: "closed",
        policy_reason: "After evidence shows the critical zone is clear.",
        incident: {
          id: "incident-zone-workcell-a2-frame-workcell-sustained-blocked",
          zone_id: "zone-workcell-a2",
          state: "closed",
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
          verification: {
            verdict: "clear",
            confidence: 0.97,
            rationale: "After evidence shows the critical zone is clear.",
            after_evidence_frame_id: "frame-workcell-after-clear",
          },
          audit_packet: {
            incident_id: "incident-zone-workcell-a2-frame-workcell-sustained-blocked",
            before_frame_id: "frame-workcell-sustained-blocked",
            after_frame_id: "frame-workcell-after-clear",
            before_timestamp: "2026-05-08T12:00:30+00:00",
            after_timestamp: "2026-05-08T12:00:45+00:00",
            alert_transcript:
              "Robotics notice: clear the obstruction at Robot Workcell A-2.",
            verification_verdict: "clear",
          },
          review_sample: {
            incident_id: "incident-zone-workcell-a2-frame-workcell-sustained-blocked",
            before_frame_id: "frame-workcell-sustained-blocked",
            after_frame_id: "frame-workcell-after-clear",
            labels: ["blocked_robot_workcell", "verified_clear"],
            human_decision: "pending",
            export_status: "local_only",
          },
        },
      },
    },
  ],
} satisfies DemoReplay;
