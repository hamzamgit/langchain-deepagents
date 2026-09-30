## Technical Support

### Support hours
Technical support is available **Monday–Friday, 9:00–18:00 UTC**.
Critical outages are monitored 24/7.

### Known issue: PDF upload crash (Android)
**Symptom**: App crashes when uploading a PDF on Android.
**Affected versions**: 3.1.x – 3.2.0
**Workaround**:
1. Update to app version **3.2.1 or later**.
2. Compress the PDF under 10 MB before upload.
3. Upload over Wi‑Fi rather than cellular if the file is large.
If the crash continues after updating, create a support ticket with device model and app version.

### API errors
HTTP 429 means rate limiting — wait and retry with exponential backoff.
HTTP 503 indicates a temporary service disruption — check status before opening a ticket.

### Login / session errors
Clear app cache, ensure system clock is correct, then retry. If MFA is enabled, confirm the authenticator time is synced.
