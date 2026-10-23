# Optional integrations

Use only capabilities that are available and materially useful. A selected app does not become a runtime dependency of the resulting website. Skills instruct an agent; they do not install services, grant access, or supply API credentials.

| Capability | Use when | Fallback / boundary |
| --- | --- | --- |
| Context7 | Verify framework or SDK APIs for the installed version | Official docs; resolve actual library IDs and use non-sensitive queries |
| Writing Style | Compose copy from relevant user-authored samples | Use the brief if unavailable; do not claim a retrieved match or copy private facts |
| Image generation | Create illustrative assets, architecture concepts, or requested edits | Approved assets or explicit placeholders; never fabricate a completed property |
| Amazing Drawing | User wants to sketch a layout or visual idea | Text brief or code-based wireframe; do not block a build waiting for a sketch |
| Zillow | Authorized current context for a real-property task | Approved data or omit unknown facts; verify dates and publication rights |
| SharePoint / OneDrive | Approved brand files, documents, photos, or project data | Supplied files; keep private originals and access links out of public source |
| Upstash Redis | Server-side caching, expiring sessions, or shared rate limiting | No Redis for a static site; choose an appropriate durable record system |
| Presentations | User also requests an editable property or project deck | Reuse approved copy/assets and the presentation workflow; do not substitute slides for a site |
| Sites | Build or update a ChatGPT Site | Follow its canonical project and publishing workflow |
| GitHub | Review code, preserve history, or commit authorized work | Supply a complete patch if writes are unavailable |

## SharePoint content flow

Resolve the requested source through the connector, then fetch the chosen file before relying on it. Record version/date and permission scope. A search hit is not publication permission. Extract only what the site needs; do not bulk export a private drive. Temporary access URLs are not durable public asset URLs.

For ongoing synchronization, implement server-side authentication, transformation, failure handling, and an update policy. A one-time development connector read does not create a live website integration. Claim automatic updates only when implemented and tested.

## Zillow and other property sources

Use currently exposed supported tools, not assumed endpoints. Keep current facts distinct from fixtures. Attribute data where required and confirm photo/data reuse rights. Do not scrape or build an unlicensed listing feed as a shortcut. Never hardcode credentials in browser code.

## Upstash Redis boundary

Read the relevant current Upstash skill/docs before implementing. For JavaScript, `@upstash/redis` supports a server-side client initialized from `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`. Keep these server-only; never use a public/browser prefix or put tokens in source.

- Define key namespaces, TTLs, tenant boundaries, and invalidation before caching.
- Cache only permitted data; include freshness information where stale facts matter.
- Define timeout/outage behavior. Cache fallback, rate-limit failure, and authorization failure need deliberate policies.
- Rate-limit real inquiry endpoints and validate on the server. Use a supported atomic implementation, not a read/increment sketch.
- Do not default to Redis as a durable lead database. Confirm retention, backup, access, and cost needs before making it the record system.
- Never use a temporary database for production. Use synthetic local test data and test real integrations separately.

This package contains no credentials, live connections, or mandatory MCP dependencies.
