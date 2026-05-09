# RobotOps Sentinel — PRD

## 1. Problem

Robotic workcells already have cameras, but those cameras mostly record failures after the fact. A cart can block a robot cell during a busy shift, stay there long enough to matter, and disappear before the next walkthrough. The operations team may never know who saw it, whether anyone was alerted, how long it remained blocked, or whether the hazard was actually cleared.

The acute failure is not only detection. Critical-zone violations are easy to miss, slow to escalate, and hard to prove resolved. Robotics teams need a way to turn passive footage into a closed operational loop: notice the violation, route the alert through approved channels, verify the physical fix, and preserve evidence without claiming that AI replaces human supervision or site policy.

## 2. Appetite & Constraints

- **Appetite:** Hackathon prototype with a polished two-minute live demo and enough product depth to withstand sponsor/judge scrutiny.
- **Hard constraints:**
  - Must center on a real physical-world robotics workflow, not a generic AI dashboard.
  - Must demonstrate a closed loop: detect, approve, alert, verify, prove.
  - Must keep robotics authority human-supervised and policy-bound.
  - Must keep the demo reliable even if optional sponsor integrations are unavailable.
  - Must support pre-event development without paid ElevenLabs or Encord access.
  - Must be able to swap in event-provided sponsor tooling without changing the product story.
- **Out of bounds:** Full production deployment, certified compliance claims, autonomous emergency control, long-term customer integration work, and anything that depends on unconfirmed event credentials.

## 3. Solution Sketch

**Behavior:**
- Input: Video or image evidence from a monitored critical zone, plus site-defined zones and escalation policy.
- Output: A robotics incident with evidence, recommended response, alert transcript, visual clearance verification, and an audit packet.
- Preconditions: A critical zone has been defined, alert policy is configured, and the system can access at least one usable camera feed or replay clip.
- Postconditions: The hazard is either still open with escalation state, or closed with before/after evidence proving the zone was cleared.

**Key flows:**
1. A clear robot workcell is monitored → an obstruction remains in the zone long enough to violate policy → the system opens an incident with visible evidence.
2. A supervisor approves the alert → the system broadcasts a specific floor instruction → the incident remains open while awaiting clearance.
3. The obstruction is removed → the system verifies the zone is clear → it closes the incident and records a signed evidence packet for review.

## 4. Non-Goals

- **Not doing:** Generic PPE detection — *Reason:* It is overdone, less differentiated, and distracts from the closed-loop workflow.
- **Not doing:** Autonomous robotics officer claims — *Reason:* The product must support existing human oversight, not imply it replaces trained operators or site obligations.
- **Not doing:** Real-time motion-planning control — *Reason:* That creates higher liability and timing risk than the supervised workcell wedge.
- **Not doing:** Production VMS, ERP, CMMS, or access-control integrations — *Reason:* Integration plumbing would consume the hackathon without strengthening the core demo.
- **Not doing:** Guaranteed live Encord or ElevenLabs dependency — *Reason:* Access may arrive at the event, but the demo must work before those credentials exist.
- **Maybe later:** Multi-camera, multi-site analytics — *Reason:* Useful for a real product, but unnecessary for the winning demo.

## 5. Rabbit Holes

- **Model zoo:** Trying every new vision, audio, or robotics model could consume the build. Bound: use only models that visibly improve the closed-loop demo.
- **Safety liability language:** Overclaiming prevention or compliance can make the project look reckless. Bound: use monitoring, escalation, verification, and evidence language.
- **Perfect detection:** Chasing every object class and lighting condition is unbounded. Bound: first workflow is robot workcell obstruction with controlled evidence and explicit uncertainty states.
- **Sponsor bingo:** Adding sponsor logos without functional value weakens trust. Bound: mention only integrations that are working or clearly marked as event-ready extensions.
- **Operational integrations:** Real VMS/CMMS/warehouse systems are deep surfaces. Bound: prove the workflow with camera input, alert output, and audit export first.

## 6. I/O Examples

**Example 1: Blocked Workcell Opens Incident**
- Input: Video frame where a cart remains inside the robot workcell zone past the configured dwell threshold.
- Output: Open incident marked high severity with before frame, zone evidence, policy violation, and recommended action.
- Why this matters: Demonstrates that the system is monitoring a site-specific physical zone, not merely captioning an image.

**Example 2: Alert Requires Approval**
- Input: Supervisor reviews the incident and approves the floor alert.
- Output: A specific spoken or audible instruction is issued, and the incident state changes to awaiting verification.
- Why this matters: Preserves human authority while still moving faster than manual reporting.

**Example 3: Verified Closure**
- Input: Follow-up frame where the obstruction has been removed from the robot workcell zone.
- Output: Incident closes with after frame, verification verdict, timestamps, alert transcript, and review/eval record.
- Why this matters: Shows the product's differentiator: the verified closure contract.
