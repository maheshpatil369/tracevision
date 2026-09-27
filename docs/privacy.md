# Privacy

TRACEVISION processes CCTV footage and derives biometric-adjacent data
(468-point facial landmarks, geometric feature vectors). This is
sensitive data. This document describes what the software does and does
not do about that — it is not legal advice.

## What the software does

- **No cloud upload of footage**: video, evidence frames, and facial data
  never leave the machine running the backend unless you configure a
  remote database/storage yourself.
- **Deletion**: `DELETE /api/videos/{id}` removes both the database row and
  the file on disk. `DELETE /api/cases/{id}` cascades to delete every
  video, analysis, detection, face, evidence frame, and report belonging to
  that case (`cascade="all, delete-orphan"` on every relevant relationship
  in `app/models/`).
- **Archiving**: `POST /api/cases/{id}/archive` sets `status=archived`
  without deleting data, for cases that must be retained but are no longer
  active.
- **Demo data is labeled**: any simulated/demo output is required to carry
  a `"DEMO MODE"` banner (spec section 42) and is never mixed silently with
  real analysis results.

## Your responsibility as the deployer

**You are responsible for lawful handling of CCTV footage and any
biometric/facial data it produces**, including compliance with applicable
laws in your jurisdiction (e.g. GDPR in the EU/UK, BIPA in Illinois, and
similar biometric-privacy statutes elsewhere). This includes, at minimum:
having a lawful basis to process the footage, informing data subjects
where required, honoring data-subject deletion requests via the endpoints
above, and restricting access to the deployed instance (see
`docs/security.md` for what access control is/isn't currently built in).

TRACEVISION does not claim chain-of-custody compliance (spec section 26):
provenance fields (SHA-256 hash, upload timestamp, processing
configuration, model versions) are recorded to support an investigation,
but no legal chain-of-custody attestation process is implemented.
