# Feature Specification: Mind system — receipt capture, AI processing, admin review, and SIE export

**Feature Branch**: `[001-mind-system-receipt]`  
**Created**: 2025-09-19  
**Status**: Draft  
**Input**: User description: "Receipt capture on mobile, tagging, optional geolocation, AI text extraction and classification, admin review with validation and accounting proposal, company card matching, and SIE export"

## Execution Flow (main)
```
1. Parse user description from Input
	→ If empty: ERROR "No feature description provided"
2. Extract key concepts from description
	→ Identify: actors, actions, data, constraints
3. For each unclear aspect:
	→ Mark with [NEEDS CLARIFICATION: specific question]
4. Fill User Scenarios & Testing section
	→ If no clear user flow: ERROR "Cannot determine user scenarios"
5. Generate Functional Requirements
	→ Each requirement must be testable
	→ Mark ambiguous requirements
6. Identify Key Entities (if data involved)
7. Run Review Checklist
	→ If any [NEEDS CLARIFICATION]: WARN "Spec has uncertainties"
	→ If implementation details found: ERROR "Remove tech details"
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

### Section Requirements
- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave as "N/A")

### For AI Generation
When creating this spec from a user prompt:
1. **Mark all ambiguities**: Use [NEEDS CLARIFICATION: specific question] for any assumption you'd need to make
2. **Don't guess**: If the prompt doesn't specify something (e.g., "login system" without auth method), mark it
3. **Think like a tester**: Every vague requirement should fail the "testable and unambiguous" checklist item
4. **Common underspecified areas**:
	- User types and permissions
	- Data retention/deletion policies  
	- Performance targets and scale
	- Error handling behaviors
	- Integration requirements
	- Security/compliance needs

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
As a mobile user, I want to quickly capture a receipt (single or multi‑page), tag it, optionally include location, and submit it so that the system can extract information and prepare it for accounting. An admin reviews and approves, and an accountant can export all approved entries as an SIE file.

### Acceptance Scenarios
1. Given the public main screen, when the user taps "Take Photo" and confirms pages (with option to add pages), then the user can select one or more tags and choose Yes/No for location, and on submit sees a success confirmation.
2. Given an uploaded multi‑page receipt, when the user adds pages and taps Finished, then all pages are treated as a single receipt entry.
3. Given a receipt is submitted, when automated processing completes, then its status is updated to Passed/Failed/Manual Review based on validation results.
4. Given an admin opens a receipt with Failed or Manual Review, when the admin edits any extracted field, then the validation report updates and the admin can Approve once issues are resolved.
5. Given approved receipts within a date range, when the admin generates an export, then an SIE file is produced for download containing the approved accounting entries.
6. Given a company card invoice is uploaded, when matching runs, then receipts marked as "company card" are matched; the admin can correct mismatches.

### Edge Cases
- Multi‑page receipt where page order is incorrect → admin can reorder pages before approval [NEEDS CLARIFICATION: is page reordering required?].
- Low OCR confidence on merchant/date/amount → status becomes Manual Review and highlights fields with low confidence.
- VAT totals do not match line items → status Failed with clear message.
- Duplicate submission of the same receipt → system flags possible duplicate for review [NEEDS CLARIFICATION: duplicate criteria, e.g., same date+amount+merchant?].
- Missing organization number → skip enrichment while allowing approval with rationale.
- Non‑receipt document types (Invoice/Other) → processing stops per rules and routes to appropriate queue. The invoices should be saved in the folder "Invoices", and the rest of the files in the folder "Misc"
- Network interruption during upload → user gets clear retry guidance without data loss.
- Very long or faint receipts → ensure image guidance and review workflow handle legibility issues.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001**: The public interface MUST allow capturing a new photo or selecting from gallery.
- **FR-002**: The system MUST support multi‑page receipts within a single submission.
- **FR-003**: Users MUST be able to assign one or more tags during submission.
- **FR-004**: Users MUST be prompted to opt‑in/out of storing location data (Yes/No only).
- **FR-005**: The system MUST store the submission with images, tags, and location choice.
- **FR-006**: The system MUST automatically extract text from images and classify the document as Receipt/Invoice/Other.
- **FR-007**: For receipts, the system MUST extract merchant name, orgnr, purchase date/time, totals (gross/net), VAT breakdown by rate (25/12/6/0), and line items.
- **FR-008**: The system MUST determine whether the receipt is company card vs. reimbursable based on configured rules.
- **FR-009**: The system MUST validate arithmetic consistency and set status to Passed/Failed/Manual Review accordingly.
- **FR-010**: If orgnr is present, the system MUST enrich with official company name from a trusted registry.
- **FR-011**: The system MUST propose accounting entries using the Swedish BAS chart of accounts based on extracted data and rules.
- **FR-012**: An admin MUST be able to review a receipt, edit any extracted field, review validation results, and approve.
- **FR-013**: The admin UI MUST highlight fields on the image corresponding to extracted data and show field names on hover.
- **FR-014**: The admin MUST be able to manage accounting rules (create, edit, delete) to influence account selection.
- **FR-015**: The system MUST provide a dashboard with sortable columns and powerful filtering (e.g., by status, date, tags, merchant, user).
- **FR-016**: The system MUST support uploading a company card invoice and automatically matching line items to receipts, with admin overrides.
- **FR-017**: The system MUST allow exporting approved entries to an SIE file for a chosen date range.
- **FR-018**: The system MUST log reasons for Failed or Manual Review statuses and display them clearly to admins.
- **FR-019**: The system MUST prevent sensitive data leakage in error messages shown to users.
- **FR-020**: The system MUST provide auditability: who submitted, who edited, who approved, and when.

Ambiguities to clarify:
- **FR-021**: Authentication & roles via: user types — public submitter vs. authenticated account? admin permissions? - for now only one type of user - but prepare for more.].
- **FR-022**: Data retention policies via how long to keep images and extracted data? deletion rights? This will be handled in phase 2].
- **FR-023**: Location data storage via consent scope and purpose limitation; can users later revoke? This will be handled in phase 2].
- **FR-024**: Internationalization via languages supported — Swedish and English].
- **FR-025**: Performance targets via [NEEDS CLARIFICATION: target p95 for upload, processing turnaround SLAs].
- **FR-026**: SIE variant via [NEEDS CLARIFICATION: Sie type 5 swedish version required by accountant].

### Key Entities *(include if feature involves data)*
- **Receipt**: Submitted expense evidence composed of one or more pages; attributes: merchant, orgnr, date/time, totals, VAT breakdown, tags, location choice, status, confidence.
- **LineItem**: Item on a receipt; attributes: description, quantity, unit price, VAT rate, total.
- **Tag**: User‑selectable category markers applied at submission; attributes: name, description.
- **User**: Person who submits a receipt or administers the system; attributes: role, name, contact - will be handled in phase 2.
- **Company**: Vendor information enriched from org registry; attributes: orgnr, legal name.
- **CompanyCardInvoice**: Monthly statement for company card; attributes: period, line items, matching status.
- **AccountingRule**: Configurable mapping logic that derives accounts based on patterns (merchant names, line items, tags).
- **ValidationReport**: Result of automatic checks with messages and severity.
- **AccountingEntry**: Journal proposal derived from BAS mapping; attributes: accounts, amounts, VAT distribution, notes.
- **ExportJob**: Generated SIE export with date range, created by, created at.

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [ ] No implementation details (languages, frameworks, APIs)
- [ ] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
- [ ] All mandatory sections completed

### Requirement Completeness
- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] Requirements are testable and unambiguous  
- [ ] Success criteria are measurable
- [ ] Scope is clearly bounded
- [ ] Dependencies and assumptions identified

---

## Execution Status
*Updated by main() during processing*

- [ ] User description parsed
- [ ] Key concepts extracted
- [ ] Ambiguities marked
- [ ] User scenarios defined
- [ ] Requirements generated
- [ ] Entities identified
- [ ] Review checklist passed

---
