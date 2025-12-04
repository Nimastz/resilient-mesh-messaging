# **Please add your short service review here**

# **Crypto service**

# **BLE adapter** 

# **Routing service**

Routing service is a central message relay that accepts encrypted message envelopes from authenticated devices, enqueues them with TTL/hop limits, and forwards them to a BLE adapter with retries and backoff. It maintains a persistent SQLite queue, runs a periodic `routing_loop()` to drain outgoing messages, and exposes debug/admin endpoints (when enabled) to inspect queue state, stats, and IDS logs.

**Main functional features**

* **Message routing with TTL/hops** – Enforces minimum/maximum TTL, hop count, and timestamp freshness, and drops “too old” or invalid messages instead of forwarding.
* **Queue + retry engine** – Stores outgoing envelopes in SQLite, retries delivery to the BLE adapter with exponential backoff and jitter, and removes messages marked as dropped.
* **BLE adapter integration** – Forwards chunks as JSON to a configured BLE adapter URL and can run against a mock BLE service in development.
* **Admin/debug endpoints (guarded)** – Optional `/queue_debug`, `/stats`, and `/ids_log_tail` endpoints for inspecting queue contents, router stats, and IDS logs when debug mode and admin role are enabled.
* **Tested behavior** – In-process and end-to-end tests verify TTL policy, size limits, rate limiting, IDS behavior, queue-full handling, and BLE ingress logic.

---

### Security coverage from different angles

**1. Authentication & access control**

* **Device authentication:** Every API call requires `X-Device-Fp` and `X-Device-Token`; bad or missing credentials yield `401 UNAUTHORIZED`.
* **Role-based authorization:** Special roles (e.g., `admin`) gate access to sensitive debug/inspection endpoints, so only authorized management clients can see queue contents and IDS logs.

**2. Integrity, freshness & replay resistance**

* **TTL and timestamp checks:** Enforce TTL bounds and reject or logically drop too-old or future-dated envelopes; BLE ingress enforces similar rules.
* **Duplicate suppression:** Maintains a per-message ID cache with TTL to drop replays and duplicates, covering integrity against simple replay attacks.
* **Consistent routing decisions:** Normalizes peer identity to `header.sender_fp` for IDS, preventing spoofed `link_meta.peer` from bypassing per-peer controls.

**3. Availability & DoS/abuse resistance**

* **Per-peer IDS & rate limiting:** Sliding-window rate limiting per peer and per-IP auth limiter (`auth:<ip>`) throttle floods and brute-force auth attempts, returning `429` when limits are hit.
* **Payload size limits:** Hard caps on serialized envelope and ciphertext size (`MAX_ENVELOPE_BYTES`, `MAX_CIPHERTEXT_BYTES`) return `413` and log IDS events, mitigating body-size DoS.
* **Queue safety:** Enforces `max_queue_size` and returns `DB_ERROR` instead of letting storage grow unbounded; dropped rows are removed from outgoing so they are not retried forever.
* **Backoff to BLE:** Exponential backoff and jitter when the BLE adapter is unhealthy reduces the chance that routing service or BLE endpoint are taken down by tight retry loops.

**4. Monitoring, logging & intrusion detection**

* **Per-peer IDS:** Tracks suspicious events, can block peers after a configurable threshold, and automatically unblocks them after a TTL, giving rate-based intrusion detection and mitigation.
* **Anonymized security logging:** IDS logs hash or anonymize sensitive identifiers (peer IDs, message IDs) while still giving operators enough data to analyze attacks.
* **Controlled debug surface:** Admin/debug endpoints are only exposed when both debug mode and admin role are present; otherwise they appear as `404`, reducing attack surface.

**5. Confidentiality & data handling**

* **Opaque payload handling:** Treats `ciphertext` and envelope fields as opaque and does not log sensitive payload content; logging focuses on metadata and anonymized identifiers.
* **Separation of concerns:** Routing layer focuses on authenticity, integrity, availability, and intrusion detection; confidentiality of message content is expected to be provided by end-to-end cryptography at higher layers.

Put together, routing service acts as a **hardened message switch** that enforces authentication, integrity/freshness, and strong availability/DoS defenses, backed by IDS and privacy-aware logging, while keeping content-level confidentiality in the crypto layer above.
