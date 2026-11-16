# White-label market newsletter — product roadmap

## Implemented in feature branch
- HTML email rendering with plain-text fallback
- Optional watchlist and recipient-name fields
- Separate firm configuration validation, conservative story selection, and local preview command
- Duplicate-story clustering and basic publisher filtering
- Tests for escaping, firm IDs, filtering, and clustering

## Preview locally (does not email clients)
```bash
python overnight_digest.py
python newsletter_preview.py --firm demo-ria --profiles firms.example.json --output newsletter_preview.html
python -m unittest discover -s tests -v
```

## Required before production
1. Licensed or otherwise permitted full-article/news source access; publisher rights and provenance tracking.
2. Article-body retrieval and grounded synthesis with per-claim citations; explicit unsupported-claim rejection. Do not imply current headlines have been verified.
3. Firm-specific branded templates and recipient-specific rendering with tenant isolation.
4. Secure recipient storage, unsubscribe handling, bounce management, rate limits, and delivery audit logs.
5. Mandatory firm approval for client-facing editions; content versioning and retention per firm compliance policy.
6. Authenticated admin interface and billing. Do not store sensitive client holdings in the repository.
7. Tests for SMTP delivery, email-client rendering, and end-to-end scheduled workflow.

Current prototype does NOT automatically send to multiple firms or clients. The existing live schedule is untouched.
