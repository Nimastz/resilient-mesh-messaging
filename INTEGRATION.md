
## target architecture 

This is thefinal picture:

* **React/Vite web app** (QR pairing + messaging UI) → talks to a **single backend “Gateway API”** (FastAPI)

  → which orchestrates:

  * **Crypto / Keystore service** (AES-GCM, ECDH, key hierarchy, keystore DB)
  * **Routing / Store-and-Forward service** (SQLite queue, TTL, hops, IDS)
  * **BLE transport daemon** (real + mock, chunking, device discovery)

the goal is *not* to merge databases, but to define:

> **Which service is source of truth for what, and how the others call it.**



Rough ownership:

* **Crypto service DB:** identity keys, session keys, key history, keystore config.
* **Routing service DB:** message queue, routing state, hop counts, delivery logs.
* **BLE service DB (if any):** known neighbors, link health metrics, maybe cached advertisements.
* **Gateway / Web DB:** user accounts & sessions only, no keys/messages.


**inter-service APIs in one `INTEGRATION.md`**

* Crypto: `/v1/encrypt`, `/v1/decrypt`, `/v1/derive_session_key`, `/v1/public_key_for_qr`
* Routing: `/v1/router/enqueue`, `/v1/router/outgoing`, `/v1/router/mark_delivered`
* BLE: `/v1/ble/send_chunk`, `/v1/ble/on_chunk_received` (webhook target)
* Gateway: `/v1/app/login`, `/v1/app/pair`, `/v1/app/send_message`, `/v1/app/messages`


# Decide DB boundaries & cleanup


Because each service already has its own DB, the best practice is:

* **Never let one service touch another service’s DB directly.**
* Force every interaction through HTTP/IPC API → easier to audit & secure.



## Introduce a Gateway API for the React app

Project React/Vite app should  **talk to exactly one backend URL** , not three microservices. The gateway hides complexity and enforces security.

**Gateway responsibilities:**

1. **Authentication + sessions (if use accounts)**
   * Handle user login, store salted + hashed passwords (bcrypt/argon2).
   * Issue session tokens or JWT style tokens, rotate periodically.
2. **Pairing via QR**
   * Frontend scans QR → sends payload to `/v1/app/pair`.
   * Gateway calls crypto service:
     * `/v1/public_key_for_qr` to show *our* identity.
     * `/v1/derive_session_key` using scanned peer public key.
   * Crypto persists keys; gateway only sees fingerprints.
3. **Send message flow**
   * `POST /v1/app/send_message` with plaintext + recipient fingerprint.
   * Gateway:
     1. Calls crypto `/v1/encrypt` → gets `MessageEnvelope`.
     2. Calls routing `/v1/router/enqueue` with that envelope.
     3. Returns message ID + status `QUEUED` to UI.
4. **Receive / list messages**
   * React polls `/v1/app/messages` or uses WebSocket.
   * Gateway queries routing for new envelopes → decrypts via crypto → returns plaintext to UI.
5. **Message status**
   * Expose `status` from routing DB: `queued`, `in_transit`, `delivered`, `expired`, `failed`.
   * This directly answers to “know if message is received or failed”.

This keeps React extremely thin and moves all security-sensitive logic into backend services.



## Local multi-service integration with mock BLE

Before touching real Bluetooth, integrate everything using a mock BLE adapter.

**Setup:**

* Use `docker-compose.yml` (or a simple `make dev-all`) to run:
  * `crypto_service`
  * `routing_service`
  * `ble_service_mock`
  * `gateway_service`
* Each service:
  * Listens on `localhost` ports, not exposed to public network.
  * Uses env vars for URLs of other services.

**Mock BLE behavior:**

* `/v1/ble/send_chunk` just simulates a neighbor and calls back:
  * POST to routing `/v1/router/enqueue` on another node instance.
* Add integration tests that:
  1. Start two “nodes” (Node A, Node B) with separate DBs.
  2. A sends message to B’s fingerprint.
  3. Assert: A’s routing DB logs delivery; B’s gateway can show plaintext to UI.

This satisfies the “test harness + network simulation



## Integrate “smart” BLE behavior (permissions + auto-connect)

Now that the backend path is stable with mock BLE, can focus on real BLE and earlier requirement:

> “Get permission once, keep scanning, and auto-connect only if both devices have the app installed and permission granted.”

**Design guidelines:**

1. **App-specific BLE service UUID**
   * Use a unique service UUID so devices only attempt auto-connect to peers that:
     * Advertise that UUID.
     * Present a fingerprint/public key in keystore.
2. **Permission model**
   * On each OS (desktop, iPhone, etc.), ask for:
     * Bluetooth permission.
     * Background scanning permission if available.
   * After user accepts, persist a flag in app/daemon config .
   * Still gracefully handle OS-level revocation (permissions can be revoked any time).
3. **Auto-connect conditions**
   * Only auto-connect if:
     * Peer advertises the app UUID.
     * Peer fingerprint is already in keystore as “paired”.
     * Rate limits are respected (no rapid re-connect storms).
4. **BLE → routing interface stays the same**
   * The real BLE daemon still only calls `/v1/ble/on_chunk_received` or `routing.enqueue` with envelopes.
   * That way, routing/crypto/gateway code doesn’t care whether BLE is mock or real.

This is exactly the “BLE transport & link layer” piece integrated with security requirements (rate-limit, spoofing defense, MTU sanity checks).

## Add secure inter-service authentication

Even if everything runs on one machine, treat services as if they’re exposed to an attacker.

**Best practice:**

1. **Bind to localhost**
   * All internal services (`crypto`, `routing`, `ble`) bind to `127.0.0.1` only.
   * Only `gateway` is reachable from the browser.
2. **Service-to-service authentication**
   * Give each internal service a shared secret (e.g. `INTERNAL_API_TOKEN`).
   * Add `Authorization: Bearer <token>` in every internal call.
   * Services reject calls without correct token.
3. **Input validation**
   * Validate envelope schema at edges.
   * Check nonce uniqueness, TTL ranges, field lengths.
   * Fail-closed: any validation error → drop + log with `INVALID_INPUT`.
4. **Logging (without secrets)**
   * Log msg_ids, fingerprints, TTL, error codes.
   * Never log plaintext, keys, nonces, GCM tags, or raw tokens.



## Security integration checklist (end-to-end)

Use the explicit project security checklist as the basis for final integration tests.

For each item, write at least one test:

* **Crypto & keys**
  * Nonce reuse test (should fail and log `NONCE_REUSE`).
  * Replay test (replay old envelope → rejected with `REPLAY_DETECTED`).
* **Routing & IDS**
  * Flood one node with duplicates → IDS logs event, rate limiting kicks in.
  * Loop prevention: TTL goes to 0 → message dropped, log reason.
* **Web & API**
  * Try simple SQLi in any text field → DB not corrupted; query uses parameters.
  * Try basic `<script>alert(1)</script>` in messages → UI escapes it; no XSS.
* **BLE**
  * Simulate spoofed advertiser → fails fingerprint/UUID checks; logged as suspicious.
  * Malformed chunk: wrong size / invalid envelope → dropped and logged.

Document the expected outcome and actual outcome → that becomes **Security Test Report** deliverable.

---

## 9. Observability + evaluation hooks

The final deliverables include latency, delivery rate, energy-usage evaluation.

For integration:

* Add **metrics export** (even simple JSON/CSV):
  * Per message: `msg_id`, enqueue time, first send time, delivery time, status.
  * Per node: #msgs sent/received, #retries, #drops due to TTL/IDS.
* Use these logs to:
  * Compute latency CDFs.
  * Compute delivery rate under simulated partitions and churn.
* Expose a tiny admin dashboard or CLI to:
  * Inspect routing queues.
  * Inspect IDS logs.
  * Trigger synthetic test scenarios.

---

## 10. Final integration & demo script

Once everything hangs together:

1. Start two or three nodes (A, B, C) with BLE mock or real BLE.
2. Pair A↔B, B↔C via QR from the React app.
3. From A’s UI, send an encrypted message to C:
   * Show “queued → in transit → delivered” transitions in UI.
   * Show routing logs on B (as intermediate hop).
4. Rotate keys mid-demo:
   * Trigger key rotation; send again; show old messages still safe.
5. Show security tools:
   * Replay attack demo → message rejected; log shows `REPLAY_DETECTED`.

That hits *all* the course requirements: crypto, routing, BLE, security tests, evaluation, plus a clean UI.

---

## Comprehensive integration memo


> After implementing and unit-testing each backend component in isolation, the next step was to securely integrate them into a single end-to-end system. We designed the final architecture around four cooperating services: a crypto/keystore service that manages AES-GCM encryption and ECDH key exchange, a routing and store-and-forward engine backed by SQLite, a BLE transport daemon responsible for neighbor discovery and chunked delivery, and a Gateway API that exposes a simple HTTPS interface to a React/Vite web client. Each service maintains its own local database and never accesses another service’s storage directly; all cross-component communication is performed through narrow, authenticated HTTP APIs. This separation of concerns allows us to reason clearly about data ownership and security boundaries.
>
> Integration is driven by a shared Day-0 contract: a tiny JSON `MessageEnvelope` schema, a common `EnvelopeHeader` structure (sender and recipient fingerprints, message ID, nonce, TTL, hop count), and a standard error format used by all services. We consolidated these definitions into a common `lib/` module and a JSON schema, which every inbound envelope is validated against. The Gateway API becomes the only interface the browser ever talks to. For pairing, the web client scans a QR code and sends the result to the gateway, which calls the crypto service to derive and persist session keys using ECDH and device fingerprints. For sending a message, the client posts plaintext and a recipient fingerprint to the gateway; the gateway invokes the crypto service to encrypt the payload into a `MessageEnvelope`, then passes the envelope to the routing service for persistence in the store-and-forward queue. The routing engine applies TTL limits, deduplication, and retry policies, and hands message chunks to the BLE daemon, which in turn discovers nearby peers and transmits the data over Bluetooth.
>
> We built a mock BLE adapter first, wiring all services together using `docker-compose` so we could verify the complete path—QR pairing, encryption, routing, and delivery—without relying on physical radios. Once the mock pipeline was stable, we replaced the mock with a real BLE daemon that preserves the same `/send_chunk` and callback interfaces but uses a project-specific service UUID and OS-level Bluetooth APIs to manage advertising, scanning, and connections. Devices only auto-connect when they advertise the correct service UUID, are already paired in the keystore, and the user has granted Bluetooth permissions. This preserves user privacy, avoids unwanted connections, and satisfies our requirement that BLE behavior remain unobtrusive after initial consent.
>
> Security checks are integrated at every layer. The crypto service enforces unique nonces per key and direction, rejects any AES-GCM tag failure, and logs replay and nonce-reuse attempts. The routing engine implements hop-count limits, rate limiting, and an intrusion-detection shim that flags message floods, abnormal TTL patterns, and suspicious duplicates. The Gateway API authenticates users (if accounts are used), stores only salted and hashed passwords, and applies strict input validation, parameterized SQL queries, and output encoding to resist SQL injection and XSS. All internal service-to-service calls are authenticated with shared tokens and bound to localhost, and no secrets (keys, nonces, plaintexts, or session tokens) ever appear in logs. Finally, we extended our test harness to simulate MITM on key exchange, replay of old envelopes, BLE floods, and basic web attacks, and we record for each scenario the expected and observed behavior. This integration strategy yields a coherent, secure, and observable mesh messaging prototype that aligns with the project’s confidentiality, integrity, and availability goals while remaining realistic within the course’s time and scope constraints.
>
