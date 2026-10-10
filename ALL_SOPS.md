# ALL_SOPS.md
# Standard Operating Procedures — Balbird Industries & Task Orch

**Document ID:** BB-TO-SOP-MASTER-001  
**Version:** 1.0  
**Prepared:** 9 October 2026  
**Document owner:** Operations / Process Owner (to be assigned)  
**Status:** Consolidated working draft — requires management review and approval

> **Important status note**
>
> This master file consolidates procedures supported by the available Task Orch workflow and Balbird project context. Procedures marked **[EXISTING WORKFLOW]** describe steps or fields visible in the available workflow artifacts. Procedures marked **[PROPOSED — VALIDATE]** are recommended operating procedures created to fill gaps; they are not represented as already approved company policy. No SOP in this file should be treated as formally approved until the designated owner reviews and signs it off.

---

## Table of Contents

1. [Document Control and SOP Conventions](#1-document-control-and-sop-conventions)
2. [Governance, Ownership, and Escalation](#2-governance-ownership-and-escalation)
3. [Balbird Industries SOPs](#3-balbird-industries-sops)
   - [BB-01: Customer Requirement Intake and RFQ Qualification](#bb-01-customer-requirement-intake-and-rfq-qualification)
   - [BB-02: Vendor Onboarding and Pre-Qualification](#bb-02-vendor-onboarding-and-pre-qualification)
   - [BB-03: Manufacturing Capacity Matching](#bb-03-manufacturing-capacity-matching)
   - [BB-04: Quotation and Costing](#bb-04-quotation-and-costing)
   - [BB-05: Design for Manufacturability and Technical Review](#bb-05-design-for-manufacturability-and-technical-review)
   - [BB-06: Production Planning and Order Handover](#bb-06-production-planning-and-order-handover)
   - [BB-07: Welding and Fabrication Quality Control](#bb-07-welding-and-fabrication-quality-control)
   - [BB-08: Inspection, Non-Conformance, and Corrective Action](#bb-08-inspection-non-conformance-and-corrective-action)
   - [BB-09: Logistics and Dispatch](#bb-09-logistics-and-dispatch)
   - [BB-10: Customer Communication and Account Management](#bb-10-customer-communication-and-account-management)
   - [BB-11: Document, Drawing, and IP Protection](#bb-11-document-drawing-and-ip-protection)
   - [BB-12: Supplier Performance Review](#bb-12-supplier-performance-review)
4. [Task Orch SOPs](#4-task-orch-sops)
   - [TO-01: Daily Goal Submission](#to-01-daily-goal-submission)
   - [TO-02: Monthly Department Goal Submission](#to-02-monthly-department-goal-submission)
   - [TO-03: Task Creation and Assignment](#to-03-task-creation-and-assignment)
   - [TO-04: Meeting Transcript Analysis](#to-04-meeting-transcript-analysis)
   - [TO-05: Live Task and Goal Updates](#to-05-live-task-and-goal-updates)
   - [TO-06: Task Status, Deadline, and Blocker Management](#to-06-task-status-deadline-and-blocker-management)
   - [TO-07: Daily Review and Manager Reporting](#to-07-daily-review-and-manager-reporting)
   - [TO-08: Dashboard Review and Reporting](#to-08-dashboard-review-and-reporting)
   - [TO-09: Data Quality, Access, and Automation Failure Handling](#to-09-data-quality-access-and-automation-failure-handling)
5. [Forms, Checklists, and Record Templates](#5-forms-checklists-and-record-templates)
6. [Proposed KPIs](#6-proposed-kpis)
7. [Open Decisions and Approval Register](#7-open-decisions-and-approval-register)
8. [Revision History](#8-revision-history)

---

## 1. Document Control and SOP Conventions

### 1.1 Purpose

Provide one working reference for repeatable operational procedures across Balbird Industries' manufacturing-network and RFQ activities and the Task Orch goal/task-management system.

### 1.2 Status labels

- **[EXISTING WORKFLOW]** — directly supported by the available Task Orch / n8n workflow artifacts or related project context.
- **[PROPOSED — VALIDATE]** — recommended procedure that needs review by the process owner before implementation.
- **[MIXED]** — combines existing workflow behavior with proposed controls or missing steps.

### 1.3 Standard SOP fields

Every controlled SOP should have:
- SOP ID and title
- Process owner and approver
- Version and effective date
- Scope and trigger
- Inputs and prerequisites
- Procedure and decision points
- Required records / evidence
- Exceptions and escalation route
- Review date

### 1.4 General operating rules [PROPOSED — VALIDATE]

1. Use the latest approved drawing, specification, workflow, or form.
2. Record decisions in the designated system rather than relying only on private messages.
3. Do not mark a task or order complete without evidence appropriate to the work.
4. Do not invent missing technical, commercial, or customer requirements. Raise a clarification.
5. Restrict customer drawings, quotations, supplier data, and personal information to authorized personnel.
6. Retain records according to a company-approved retention schedule; this document does not define a legal retention period.
7. Where safety, product conformity, contractual compliance, or data security may be affected, stop the affected activity and escalate.

---

## 2. Governance, Ownership, and Escalation

### 2.1 Proposed ownership model [PROPOSED — VALIDATE]

| Role | Core accountability |
|---|---|
| Process Owner | Maintains the SOP, measures performance, and proposes revisions |
| Department Lead | Assigns work, confirms priorities, reviews evidence, and escalates blockers |
| Task Owner / Operator | Executes assigned work, updates status, and supplies completion evidence |
| Quality Owner | Defines inspection requirements, controls non-conforming outputs, and approves disposition within delegated authority |
| Commercial / Account Owner | Confirms customer requirements, commercial assumptions, and customer communications |
| System Administrator | Manages system access, integrations, backups, and automation incidents |
| Approver / Management | Approves controlled procedures, exceptions, and major commercial or operational decisions |

### 2.2 Escalation rules [PROPOSED — VALIDATE]

Escalate promptly when:
- A deadline is at risk or has passed.
- Required inputs, drawings, approvals, materials, capacity, or customer clarifications are missing.
- A quality defect, safety issue, data leak, or suspected unauthorized disclosure occurs.
- The task owner and requester disagree about scope or acceptance criteria.
- An automation creates duplicate, incorrect, or incomplete records.

The escalation message should contain: record ID, issue, impact, actions already taken, decision required, owner, and required decision date.

---

# 3. Balbird Industries SOPs

## BB-01: Customer Requirement Intake and RFQ Qualification

**Status:** [PROPOSED — VALIDATE]  
**Owner:** Sales / RFQ Coordinator  
**Trigger:** New customer enquiry, drawing package, or Request for Quotation (RFQ)

### Objective
Capture enough reliable information to decide whether the opportunity can be quoted and executed.

### Inputs
Customer enquiry; part/assembly drawings; bill of materials (BOM), quantity, material, finish, quality requirements, delivery location, target date, and commercial terms where available.

### Procedure
1. Create a unique RFQ / opportunity record.
2. Record customer identity, contact, enquiry date, required response date, and source.
3. List every supplied file with revision, date, and confidentiality classification.
4. Check that quantities, units, materials, tolerances, finishes, inspection requirements, packaging, and delivery expectations are understandable.
5. Identify missing or conflicting information. Send a numbered clarification list to the customer.
6. Conduct an initial capability screen: manufacturing process, dimensions, material, capacity, quality requirements, delivery feasibility, and required approvals.
7. Record the go / no-go decision and rationale. Do not promise a delivery date before capacity and supply assumptions have been checked.
8. Assign an RFQ owner and next action with a deadline.
9. Proceed to DFM, vendor matching, and costing only when sufficient information is available; clearly label any assumptions.

### Required records
RFQ register; customer clarification log; file/revision list; feasibility decision; quotation due date.

### Acceptance criteria
The RFQ has an owner, a traceable ID, a clear scope, and either a documented next step or a documented reason for holding / declining it.

---

## BB-02: Vendor Onboarding and Pre-Qualification

**Status:** [PROPOSED — VALIDATE]  
**Owner:** Vendor Network / Procurement  
**Trigger:** New manufacturing partner or re-qualification request

### Objective
Establish a documented basis for deciding whether a vendor is suitable for a specific class of work.

### Procedure
1. Create a vendor profile with legal entity name, address, contacts, capabilities, and authorized representatives.
2. Collect applicable company, tax, banking, quality, and statutory documents through an approved secure channel. Verify them using the company's chosen validation process.
3. Record manufacturing processes, equipment, work envelope, materials handled, capacity, typical lead times, and geographic constraints.
4. Review quality-management credentials and certificates for scope, validity, and issuing body where applicable.
5. Assess calibration, inspection, traceability, material controls, subcontracting, and corrective-action practices as relevant to the intended work.
6. Execute an NDA and other required agreements before sharing protected customer information. Legal review should be obtained where required.
7. Conduct a technical audit, sample review, or trial order when risk or customer requirements justify it.
8. Set vendor status: **Under Review**, **Approved for Defined Scope**, **Conditionally Approved**, or **Suspended**.
9. Record approval date, approver, approved processes / limits, expiry or review date, and unresolved gaps.
10. Re-verify expired or materially changed documents before relying on them.

### Required records
Vendor master; verification checklist; certificates and expiry dates; NDA / agreement status; audit results; approval decision.

### Control
A vendor must not be described as fully vetted unless the required checks are completed and recorded. This proposed procedure expands on Balbird project concepts around pre-verified vendor onboarding and quality credentials; it is not proof that a live approval process already exists.

---

## BB-03: Manufacturing Capacity Matching

**Status:** [PROPOSED — VALIDATE]  
**Owner:** Vendor Network / Production Planning  
**Trigger:** Qualified RFQ requires a suitable manufacturing partner

### Objective
Match work to vendors with demonstrable technical capability, available capacity, quality readiness, and delivery feasibility.

### Procedure
1. Convert the RFQ into structured requirements: process, material, dimensions, tolerances, quantity, target delivery, quality level, location, and documentation.
2. Filter out vendors lacking mandatory capabilities, valid approvals, or required agreements.
3. Compare remaining vendors against machine/process fit, capacity window, material sourcing, quality history, logistics, and commercial constraints.
4. Request explicit capacity confirmation for the proposed quantity and dates; do not treat a profile's stated capacity as current availability.
5. Document assumptions, exclusions, and unresolved risks.
6. Prepare a shortlist with the reason each vendor qualifies and any trade-offs.
7. Obtain the required internal approval before sharing customer-controlled files or committing to a supplier.
8. Record the selected vendor and the basis for selection.
9. Reconfirm capacity before purchase/order release and whenever the scope or schedule changes.

### Required records
Matching matrix; capacity confirmations; risk notes; selection approval; date of last confirmation.

### Control
Any automated match should be treated as a recommendation until required human approvals and vendor confirmations are recorded.

---

## BB-04: Quotation and Costing

**Status:** [PROPOSED — VALIDATE]  
**Owner:** Costing / Commercial  
**Trigger:** RFQ passes initial qualification

### Objective
Produce a traceable quotation based on explicit technical and commercial assumptions.

### Procedure
1. Verify that the drawing/BOM revision and quantity basis match the RFQ record.
2. Identify raw material grade, density/weight basis, yield, scrap allowance, bought-out parts, and material price source.
3. Estimate each process step and its setup, cycle time, machine rate, labour, tooling, consumables, finishing, inspection, and packaging requirements.
4. Include subcontracting, freight, duties/taxes where applicable, overhead, contingency, and margin according to approved company rules.
5. Record the source and date for volatile material prices and machine-rate assumptions.
6. Check quote validity, minimum order quantity, batch assumptions, lead time, payment terms, delivery terms, exclusions, and change-order conditions.
7. Have a second authorized person review high-value, unusual, low-margin, or technically risky quotations according to thresholds set by management.
8. Issue the quotation with a unique number and revision. Keep calculations and approvals linked to it.
9. When requirements change, revise the quote rather than silently changing the original.
10. After award, reconcile quoted assumptions with the order and hand over risks to production planning.

### Required records
Cost sheet; rate sources and dates; quotation revision; approval; customer submission; assumptions and exclusions.

### Automation note
Balbird project materials describe a target direction involving automated BOM calculation, live material indices, standard machine rates, and faster quoting. Treat this as a proposed capability unless a production implementation is separately verified.

---

## BB-05: Design for Manufacturability and Technical Review

**Status:** [PROPOSED — VALIDATE]  
**Owner:** Engineering / Technical Review  
**Trigger:** New part, assembly, drawing revision, or process uncertainty

### Procedure
1. Confirm drawing revision, units, material specification, tolerances, weld symbols, surface finish, and inspection criteria.
2. Review whether the part can be produced using available processes, machines, tooling, and vendor capabilities.
3. Identify difficult-to-manufacture features, inaccessible welds, distortion risks, excessive tolerances, material availability issues, and inspection constraints.
4. Evaluate assembly fit, interfaces, datum strategy, handling, transport, and service requirements where relevant.
5. Record every proposed change as a question or recommendation; do not alter customer-controlled design intent without authorization.
6. Obtain written customer / engineering approval for deviations before production.
7. Update the DFM review and ensure the approved revision is used by costing and production.
8. Transfer open risks and inspection points to the production and quality plans.

### Required records
DFM checklist; clarification log; deviation approvals; approved drawing revision.

---

## BB-06: Production Planning and Order Handover

**Status:** [PROPOSED — VALIDATE]  
**Owner:** Production / Order Coordinator  
**Trigger:** Customer order or internal release authorization

### Procedure
1. Confirm the accepted order, scope, price, quantity, delivery date, and applicable terms.
2. Verify that the order matches the latest approved quote, drawings, BOM, and customer requirements.
3. Confirm vendor selection, capacity, material availability, tooling, process sequence, inspection plan, and packaging.
4. Build a milestone plan with accountable owners and dates.
5. Identify critical path items, long-lead materials, outsourced processes, and customer hold points.
6. Conduct a handover review with commercial, technical, quality, vendor, and logistics owners as applicable.
7. Release work only when mandatory inputs and approvals are complete.
8. Track planned versus actual progress and update the risk register.
9. Route scope, cost, or schedule changes through documented change control.
10. At completion, ensure inspection records and dispatch documents are ready.

### Required records
Order handover checklist; production schedule; risk log; change log; milestone updates.

---

## BB-07: Welding and Fabrication Quality Control

**Status:** [PROPOSED — VALIDATE]  
**Owner:** Quality / Fabrication Lead  
**Applies to:** Welded and fabricated assemblies, including stainless-steel tanks, brackets, and similar products where relevant

> This is a general control framework, not a welding procedure specification (WPS). Applicable codes, qualified personnel, approved WPS/PQR requirements, and customer specifications take precedence.

### Procedure
1. Confirm approved drawings, material grade, thickness, joint design, weld symbols, acceptance criteria, and applicable welding procedure.
2. Verify material identity and traceability before cutting or fit-up.
3. Check preparation, cleanliness, joint gap, alignment, fixtures, and tack welds before welding.
4. Confirm the approved process, filler material, consumables, settings, and welder qualifications required by the governing specification.
5. Inspect during fabrication for fit-up, sequence, distortion, visible defects, and compliance with the approved process.
6. Perform visual and dimensional inspection at defined hold points.
7. For pressure/fluid-containing assemblies, apply the specified leak or pressure test only under an approved test procedure, with safe isolation and documented acceptance limits.
8. If micro-porosity, leakage, cracking, incomplete fusion, or other unacceptable indications are suspected, stop release and follow BB-08.
9. Record repairs, re-inspections, and final acceptance.
10. Preserve traceability between the assembly, material, weld/inspection records, and shipment.

### Required records
Material certificates where required; inspection reports; welding records; test reports; repair records; final release.

### Safety
Never improvise pressure-test limits or procedures. Use approved equipment, trained personnel, barriers, and applicable safety controls.

---

## BB-08: Inspection, Non-Conformance, and Corrective Action

**Status:** [PROPOSED — VALIDATE]  
**Owner:** Quality  
**Trigger:** Failed inspection, customer complaint, suspected defect, or process deviation

### Procedure
1. Identify and contain the affected item, batch, or shipment. Prevent unintended use or dispatch.
2. Record a non-conformance ID, part/lot, revision, quantity affected, detection point, defect description, evidence, and date.
3. Assess severity, customer impact, safety/regulatory implications, and whether other lots may be affected.
4. Notify quality and the responsible operational owner. Notify the customer when contractually or procedurally required.
5. Determine disposition through authorized personnel: rework, repair, use-as-is concession, return, or scrap. Obtain customer approval where required.
6. Define rework/repair instructions and acceptance criteria before work begins.
7. Re-inspect and document results before release.
8. Perform root-cause analysis proportionate to risk and recurrence; distinguish containment from corrective action.
9. Assign corrective actions with owners and due dates.
10. Verify effectiveness after implementation and close only when evidence supports closure.

### Required records
Non-conformance report; containment log; disposition approval; rework records; root-cause analysis; corrective-action verification.

---

## BB-09: Logistics and Dispatch

**Status:** [PROPOSED — VALIDATE]  
**Owner:** Logistics  
**Trigger:** Order is approved for shipment

### Procedure
1. Verify the order, destination, requested delivery date, quantity, packaging, labels, and special handling requirements.
2. Confirm that quality release and required customer documentation are complete.
3. Inspect packaging for protection against movement, corrosion, contamination, moisture, and handling damage as appropriate.
4. Verify dimensions, weight, lifting points, load restraint, and vehicle suitability where relevant.
5. Prepare packing list, delivery note, transport documents, and any required certificates.
6. Record carrier, vehicle / tracking details, dispatch date, and expected delivery.
7. Photograph the packed shipment and visible identification when permitted and useful for traceability.
8. Send dispatch confirmation to the designated customer contact.
9. Capture proof of delivery and record shortages, damage, delays, or discrepancies.
10. Escalate any delivery risk before the committed date where possible.

### Required records
Dispatch checklist; packing list; inspection release; transport details; proof of delivery; incident record.

---

## BB-10: Customer Communication and Account Management

**Status:** [PROPOSED — VALIDATE]  
**Owner:** Sales / Account Owner

### Procedure
1. Maintain a named owner and approved communication channel for each customer opportunity/order.
2. Acknowledge new enquiries and record the expected next response date.
3. Use clear, version-controlled references for quotations, drawings, specifications, and change requests.
4. Communicate only confirmed capacity and delivery commitments.
5. For delays, defects, or scope changes, communicate the issue, impact, containment, proposed recovery, and next update time.
6. Record decisions and approvals in the opportunity/order record.
7. Escalate commercial disputes, contractual interpretation, or unapproved concessions to authorized management.
8. Close the loop after delivery and record feedback, claims, or follow-up opportunities.

### Required records
Customer interaction log; action register; approvals; complaint / feedback record.

---

## BB-11: Document, Drawing, and IP Protection

**Status:** [PROPOSED — VALIDATE]  
**Owner:** System Administrator / Commercial / Legal as applicable

### Procedure
1. Classify information as public, internal, confidential, or customer-restricted using the company-approved classification scheme.
2. Verify the recipient and business need before sharing files.
3. Confirm that required NDA / contractual permissions are in place before sharing restricted information.
4. Use approved storage and transfer channels with access controls; avoid public links for confidential documents.
5. Use revision numbers and preserve the original source file.
6. Share only the minimum information needed by each vendor or partner.
7. Keep an access / sharing record for sensitive packages where feasible.
8. Revoke access when work ends or authorization expires.
9. Report suspected leakage, misdirected email, unauthorized access, or lost devices immediately.
10. Preserve evidence and follow the incident-response process; do not conceal or independently destroy records.

### Required records
Document register; access/share log where applicable; NDA status; incident report; revocation confirmation.

---

## BB-12: Supplier Performance Review

**Status:** [PROPOSED — VALIDATE]  
**Owner:** Vendor Network / Quality / Procurement

### Procedure
1. Review supplier performance at a management-defined frequency and after major incidents.
2. Evaluate on-time delivery, quality acceptance, responsiveness, documentation, cost reliability, capacity accuracy, and corrective-action effectiveness.
3. Use a consistent scoring method and evidence period.
4. Discuss material performance gaps with the supplier and agree actions, owners, and deadlines.
5. Reassess risk and approval scope where recurring issues exist.
6. Suspend or restrict a supplier only through the authorized process and communicate the decision to affected teams.
7. Retain the scorecard and follow-up actions.

### Required records
Supplier scorecard; evidence; meeting notes; corrective-action log; approval-status history.

---

# 4. Task Orch SOPs

## Task Orch operating context

**[EXISTING WORKFLOW]** The available `Stauff - Monthly Tasks Updater` n8n workflow shows a form-based input router with options for **Daily Goals**, **Monthly Goals**, **Daily Transcript**, and **Live Updates**. It includes paths for formatting/upserting daily goals, monthly goals, transcript-derived tasks and reports, and live updates. The workflow uses task/goal records with fields such as IDs, descriptions, assignee, assigner, department, deadline, priority, status, reason, source, updated by, and last updated. The exact current behavior should be confirmed against the deployed version before operational reliance.

The available workflow also maps example team members to departments:
- Shreyash — SO department
- Ganesh — PO department
- Shruti — Sales Department
- Vaishnavi — Logistics Department

**Important:** Treat these mappings as workflow-specific configuration, not a universal org chart. Update them if team responsibilities change.

## TO-01: Daily Goal Submission

**Status:** [MIXED]  
**Owner:** Team Lead / Goal Giver and Task Owner  
**Trigger:** Start-of-day planning or reassignment

### Objective
Capture clear, actionable work for the day and link it to the responsible person.

### Inputs
Team member, goal/task description, assigner, department, deadline, priority, and relevant context.

### Procedure
1. The goal giver defines a specific outcome rather than a vague activity.
2. Confirm the task owner and department.
3. Add a deadline and priority when applicable. If the work is time-bound, a deadline should be mandatory under the proposed control.
4. Include the expected deliverable and acceptance criteria.
5. Submit through the Task Orch input form using **Daily Goals** and the expected JSON structure.
6. The existing workflow formats daily goal data and upserts task records into the task store / sheet.
7. Verify that each submitted goal appears once with the correct owner, assigner, department, deadline, priority, and initial status.
8. Resolve duplicates or mapping errors before work begins.

### Proposed quality rule
A goal is not ready for execution if the owner, expected result, or required deadline is ambiguous.

### Example JSON shape
```json
{
  "goals": {
    "Shreyash": {
      "goal": "Complete and test the workflow prototype",
      "deadline": "2026-10-09",
      "priority": "High"
    }
  }
}
```

Use the exact schema required by the deployed workflow; this example illustrates the intent and may need adaptation.

---

## TO-02: Monthly Department Goal Submission

**Status:** [MIXED]  
**Owner:** Department Lead / Management

### Objective
Translate monthly outcomes into measurable goals and align daily tasks with them.

### Procedure
1. Define each department's outcome for the month.
2. State measurable completion criteria, target value where applicable, owner, and deadline.
3. Submit using **Monthly Goals** and the expected JSON structure.
4. The available workflow has a monthly-goal formatting path and upsert action.
5. Verify department name, month/time frame, goal description, assigner, deadline, status, and update metadata.
6. Break monthly goals into milestones and daily tasks; record the relationship between the daily work and the monthly outcome.
7. Review progress at a regular cadence and revise through a documented update rather than silently replacing the goal.
8. At month-end, mark the goal complete, partially achieved, or not achieved with evidence and a brief explanation.

### Example JSON shape
```json
{
  "goals": {
    "SO department": {
      "goal": "Qualify 10 manufacturing opportunities",
      "month": "October 2026",
      "deadline": "2026-10-31"
    }
  }
}
```

### Control gap to validate
The inspected workflow snippet defaults some monthly-goal fields such as time frame, month, and deadline. Confirm that the deployed workflow preserves user-provided deadlines and month values rather than overwriting them with defaults.

---

## TO-03: Task Creation and Assignment

**Status:** [MIXED]  
**Owner:** Task Creator / Department Lead

### Required task fields
- Task ID
- Date created
- Task description
- Assigned to
- Assigned by
- Department
- Deadline
- Priority
- Status
- Reason / blocker notes
- Source
- Updated by
- Last updated

### Procedure
1. Create a task only when there is a clear action or deliverable.
2. Record **who assigned the task to whom**. Do not use a generic assigner label if the actual person is known.
3. Assign one directly accountable owner. Add collaborators separately if the system supports them.
4. Set a unique Task ID using the system's ID-generation method.
5. Set a deadline, priority, department, and initial status.
6. Include the source: daily goal, transcript, live update, or another approved source.
7. Check for an existing matching task before creating a new record.
8. Confirm the task is visible in the source of truth.
9. If a task changes owner, scope, or deadline, preserve the change history where possible.

### Status model [PROPOSED — VALIDATE]
`Pending` → `In Progress` → `Blocked` (when applicable) → `Completed`

Use `Cancelled` only with a reason and appropriate authorization. Do not mark a task completed merely because it was discussed in a meeting.

---

## TO-04: Meeting Transcript Analysis

**Status:** [MIXED]  
**Owner:** Meeting Facilitator / Task Orch Operator  
**Trigger:** A meeting has ended and the transcript is available

### Objective
Convert meeting discussion into traceable tasks, next actions, and performance summaries without inventing commitments.

### Procedure
1. Confirm meeting date and identify participants where possible.
2. Gather the correct daily goals and relevant monthly goals before analysis.
3. Paste the transcript into the approved workflow input. The available `BalPigeon` artifact demonstrates a JSON input containing a date, `todays_goals`, and a transcript. Another workflow accepts a selected input type and a JSON payload.
4. Check the transcript for transcription errors, speaker attribution issues, and missing sections.
5. Run the transcript-analysis workflow.
6. Review generated task descriptions, owners, assigners, deadlines, and reports for factual grounding.
7. Create tasks only for explicit commitments or clearly justified actions. If ownership or deadline is not stated, mark it as **Needs confirmation** rather than inventing it.
8. Preserve the distinction between what was said, what the AI inferred, and what the manager approved.
9. Verify that transcript-derived tasks and reports were written to the correct records.
10. Send the action list to the relevant owners for confirmation.

### Quality controls
- Do not infer that an absent participant completed or failed a task.
- Do not treat an AI-generated performance summary as a disciplinary finding.
- Flag conflicting transcript statements for human review.
- Do not upload sensitive meeting content to an unapproved AI service.

### Required records
Meeting date; transcript source; participants; generated actions; reviewer; corrections; final task IDs.

---

## TO-05: Live Task and Goal Updates

**Status:** [MIXED]  
**Owner:** Task Owner / Manager  
**Trigger:** A task changes, new work is assigned, or progress is reported

### Procedure
1. Identify the existing task or goal by its unique ID whenever possible.
2. State the new information: progress, status, deadline change, owner change, blocker, or scope change.
3. Include who provided the update and when.
4. Submit using **Live Updates** and the expected payload format.
5. The available workflow contains a live-update formatting path with upsert actions for tasks and goals.
6. Verify that the intended record was updated and that unrelated records were not overwritten.
7. If the update creates a new task, ensure a new ID is generated and the source is recorded.
8. If the update changes a deadline or owner, retain the prior value in a history/audit log where supported.
9. Notify the responsible person when the change affects their commitments.

### Required records
Original record ID; update text; updater; timestamp; fields changed; resulting status.

---

## TO-06: Task Status, Deadline, and Blocker Management

**Status:** [PROPOSED — VALIDATE]  
**Owner:** Task Owner; Department Lead accountable for review

### Procedure
1. The task owner updates progress at the cadence agreed by the department.
2. Set the status to reflect reality: Pending, In Progress, Blocked, Completed, or Cancelled.
3. If blocked, record the blocker, its impact, the decision/support needed, and the next follow-up date.
4. If a deadline is at risk, notify the assigner before the deadline and propose a revised plan.
5. Do not change the deadline silently; record who approved the change and why.
6. On completion, attach or link evidence such as a file, output, customer response, test result, or approved deliverable.
7. The assigner or reviewer checks the evidence against the acceptance criteria.
8. Close the task only after acceptance; reopen it if the deliverable fails the agreed criteria.

### Minimum update format
- Task ID:
- Current status:
- Work completed:
- Remaining work:
- Blocker / risk:
- Help or decision required:
- Deadline status:
- Evidence / link:
- Next update date:

---

## TO-07: Daily Review and Manager Reporting

**Status:** [MIXED]  
**Owner:** Department Lead / Manager

### Objective
Review execution against daily goals and create a useful, evidence-based plan for the next work period.

### Procedure
1. Collect current daily goals and relevant monthly goals.
2. Review task status and latest updates.
3. Compare evidence against the stated acceptance criteria.
4. Summarize completed work, incomplete work, blockers, risks, and support required.
5. For each owner, identify next actions that are concrete, assigned, and time-bound.
6. Use transcript-generated reports as a draft; the available `BalPigeon` workflow is configured to produce a `boss_report` and `tomorrows_tasks` for a defined set of team members.
7. Check all generated statements against the transcript and task data before sharing.
8. Record carry-forward tasks with the correct owner, assigner, and deadline.
9. Escalate repeated blockers or missed commitments using consistent criteria.
10. Keep feedback specific, professional, and focused on work outcomes rather than personal assumptions.

### Required records
Daily review summary; accepted tasks; carry-forward list; blockers; approvals / escalations.

---

## TO-08: Dashboard Review and Reporting

**Status:** [PROPOSED — VALIDATE]  
**Owner:** Manager / Dashboard Administrator

### Objective
Provide a reliable view of goals, tasks, updates, and departmental workload.

### Procedure
1. Open the approved Task Orch dashboard or source sheet.
2. Filter by department, owner, assigner, status, priority, deadline, and date range where those fields exist.
3. Review overdue tasks, blocked tasks, tasks without owners, tasks without deadlines, and recently changed records.
4. Compare daily execution with monthly departmental goals.
5. Check for duplicate IDs, inconsistent statuses, missing update timestamps, and mismatched department mappings.
6. Treat dashboard metrics as provisional if underlying records are incomplete.
7. Export or share reports only with authorized recipients.
8. Record key decisions, assigned actions, and review date.

### Suggested dashboard views
- All open tasks
- Overdue / at-risk tasks
- Tasks grouped by department and owner
- Tasks grouped by assigner
- Monthly goals and progress
- Blocked tasks awaiting decisions
- Recently updated tasks
- Tasks missing deadline / acceptance criteria

---

## TO-09: Data Quality, Access, and Automation Failure Handling

**Status:** [MIXED]  
**Owner:** System Administrator / Workflow Owner

### Procedure
1. Before submitting input, validate that JSON is syntactically valid and uses the expected schema.
2. Confirm the selected input type matches the payload.
3. Confirm required fields are present and use consistent date formats.
4. If the workflow fails, capture the execution ID, error, timestamp, and affected records.
5. Do not repeatedly retry an uncertain write operation until duplicate risk has been checked.
6. Verify the output in the destination sheet/database after a successful execution.
7. If data was written incorrectly, stop downstream use and correct it through a traceable process.
8. Keep workflow credentials in the approved credential store; never embed API keys or passwords in SOPs or shared JSON files.
9. Limit write access to authorized users and periodically review access.
10. Test workflow changes on non-production data before deploying them.
11. Maintain a documented recovery and backup approach appropriate to the production system.
12. Escalate failures that affect deadlines, customer commitments, or data integrity.

### Required records
Workflow execution ID; error details; affected record IDs; retries; correction; verification; incident owner.

---

# 5. Forms, Checklists, and Record Templates

## 5.1 RFQ intake checklist [PROPOSED]

- [ ] Customer and contact recorded
- [ ] RFQ ID and response deadline recorded
- [ ] Quantity and delivery location confirmed
- [ ] Drawings/BOM and revision recorded
- [ ] Material, tolerances, finish, and quality requirements identified
- [ ] Inspection / certification requirements identified
- [ ] Missing information listed and clarification owner assigned
- [ ] Capability / capacity review completed
- [ ] Go / no-go decision recorded

## 5.2 Vendor onboarding checklist [PROPOSED]

- [ ] Legal identity and contact details verified
- [ ] Capability and equipment profile completed
- [ ] Quality credentials reviewed where applicable
- [ ] Required NDA / agreement completed
- [ ] Audit / sample / trial requirements assessed
- [ ] Approved scope and restrictions documented
- [ ] Approval status, approver, and review date recorded
- [ ] Expiry reminders assigned where needed

## 5.3 Order handover checklist [PROPOSED]

- [ ] Accepted order matches the approved quotation
- [ ] Latest drawing / BOM revision confirmed
- [ ] Quantity, schedule, and delivery location confirmed
- [ ] Vendor and capacity confirmed
- [ ] Material, tooling, and process sequence confirmed
- [ ] Quality plan and hold points defined
- [ ] Packaging and logistics requirements defined
- [ ] Risks, assumptions, and open issues assigned
- [ ] Work release approved

## 5.4 Task creation checklist [MIXED]

- [ ] Unique Task ID
- [ ] Clear action and expected deliverable
- [ ] Assigned To
- [ ] Assigned By
- [ ] Department
- [ ] Deadline
- [ ] Priority
- [ ] Status
- [ ] Source (daily goal / transcript / live update / other)
- [ ] Acceptance criteria / evidence expectation
- [ ] Duplicate check completed

## 5.5 Meeting action review checklist [PROPOSED]

- [ ] Meeting date and source transcript recorded
- [ ] Relevant daily and monthly goals included
- [ ] Speaker attribution checked
- [ ] Each action has a clear owner or is marked for confirmation
- [ ] Deadlines are stated or explicitly marked missing
- [ ] AI-generated summary reviewed by a human
- [ ] Duplicate tasks checked
- [ ] Tasks written to the correct records
- [ ] Owners informed of their actions

## 5.6 Non-conformance record template [PROPOSED]

```text
NC ID:
Date detected:
Customer / order / part / lot:
Drawing revision:
Description of non-conformance:
Quantity affected:
Containment action:
Potential customer or safety impact:
Disposition:
Required approvals:
Root cause:
Corrective action / owner / due date:
Re-inspection result:
Effectiveness verification:
Closure approved by / date:
```

## 5.7 Task update template [PROPOSED]

```text
Task ID:
Updated by:
Update date/time:
Current status:
Progress / completed work:
Remaining work:
Blocker or risk:
Deadline status:
Decision/support required:
Evidence link:
Next action and owner:
Next update date:
```

## 5.8 SOP change request template [PROPOSED]

```text
SOP ID and version:
Requested by:
Date:
Reason for change:
Current procedure / issue:
Proposed change:
Impact on quality, safety, cost, systems, or customers:
Training required:
Approver:
Effective date:
```

---

# 6. Proposed KPIs

**All metrics below are suggestions, not confirmed current Balbird or Task Orch KPIs. Define targets and calculation rules with management before reporting.**

## Balbird
- RFQ response time
- RFQ-to-quotation conversion rate
- Quote accuracy / post-award variance
- Vendor capacity confirmation time
- On-time delivery rate
- First-pass quality acceptance
- Non-conformance rate by process / supplier
- Corrective-action closure time
- Customer complaint recurrence
- Supplier document validity rate

## Task Orch
- Percentage of tasks with owner, assigner, and deadline
- On-time task completion rate
- Overdue open-task count
- Blocked-task age
- Daily goals linked to monthly goals
- Percentage of transcript-derived tasks reviewed by a human
- Duplicate / incorrectly mapped record rate
- Automation execution success rate
- Median time from update submission to verified record update
- Percentage of completed tasks with evidence

### KPI governance
For every KPI, define owner, formula, source fields, refresh frequency, exclusions, target, and response when the threshold is missed. Avoid comparing teams without accounting for differences in task complexity and workload.

---

# 7. Open Decisions and Approval Register

The following require owner confirmation before this file becomes controlled policy:

1. **Department ownership:** Confirm current names, roles, and department mappings.
2. **Task schema:** Confirm the authoritative database/sheet, required fields, accepted statuses, and unique-ID rules.
3. **Deadlines:** Confirm whether deadlines are mandatory for all tasks and how changes are approved.
4. **Monthly goals:** Verify that submitted month and deadline values are preserved by the deployed workflow.
5. **Transcript workflow:** Confirm which workflow is production, who reviews AI-generated reports, and where final outputs are stored.
6. **Vendor qualification:** Approve the exact legal, quality, capability, audit, and requalification requirements.
7. **RFQ / costing authority:** Set quotation approval thresholds and approved costing assumptions.
8. **Quality requirements:** Identify applicable customer specifications, codes, inspection plans, and authorized disposition roles.
9. **Document security:** Approve classification levels, transfer channels, access review, incident response, and retention policy.
10. **Escalation:** Define contacts, severity levels, response times, and after-hours process.
11. **System reliability:** Define backup, restore, access control, test environment, and automation incident ownership.
12. **KPI targets:** Approve formulas, baselines, targets, and reporting cadence.

## Approval register

| SOP group | Process owner | Approver | Status | Effective date |
|---|---|---|---|---|
| Balbird RFQ and commercial | To be assigned | To be assigned | Draft | Pending |
| Balbird vendor network | To be assigned | To be assigned | Draft | Pending |
| Balbird production and quality | To be assigned | To be assigned | Draft | Pending |
| Balbird logistics and customer service | To be assigned | To be assigned | Draft | Pending |
| Task Orch goals and tasks | To be assigned | To be assigned | Draft | Pending |
| Task Orch automation and data | To be assigned | To be assigned | Draft | Pending |

---

# 8. Revision History

| Version | Date | Change | Author / owner | Approval |
|---|---|---|---|---|
| 1.0 | 2026-10-09 | Initial consolidated working draft; existing workflow behavior separated from proposed procedures | Draft prepared from available project context | Pending |

---

## End of document

**Release rule:** Before publishing this file as an official SOP manual, assign accountable owners, validate each proposed procedure against actual company practices and customer / legal requirements, replace placeholders, and record formal approval.
