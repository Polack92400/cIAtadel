# ADR 0003 — Authentication transport

**Decision.** Django issues short-lived access + rotating refresh JWTs
(SimpleJWT) set as `HttpOnly; SameSite=Lax; Secure` cookies. The browser only
talks to Next.js, which rewrites `/api/*` to Django on the internal network,
so cookies are first-party and Django/MinIO/Ollama are never exposed. CSRF is
enforced with Django's double-submit token on unsafe methods. JWTs carry only
the user id; tenant and role are looked up per request.

**Future.** `User.external_subject` stores the OIDC `sub` so Keycloak / Cognito
can authenticate users without changing the data model; a DRF authenticator
for OIDC tokens can replace or sit next to the local one.
