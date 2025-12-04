
# Routing Service – Quick Test & Security Guide

The routing service is responsible for:

* **Message routing & TTL/hop enforcement**
* **Queueing + retries + backoff to BLE**
* **Per-peer IDS (rate limiting, blocking, duplicate suppression)**
* **Device auth + role-based admin endpoints**
* **Payload size limits for envelopes/ciphertext (DoS protection)**

All tests live in `services/routing_service/test/`.

---

## 1️⃣ Start the Routing Service

From project root:

<pre class="overflow-visible!" data-start="864" data-end="1001"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-bash"><span><span>cd</span><span> resilient-mesh-messaging

uvicorn services.routing_service.routing_api:app \
  --host 0.0.0.0 \
  --port 9002 \
  --reload
</span></span></code></div></div></pre>

On startup the router:

* Initializes SQLite at `services/routing_service/routing.db`
* Starts the async `routing_loop()` that drains the queue every ~2s

The base URL is:

<pre class="overflow-visible!" data-start="1176" data-end="1209"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-text"><span><span>http://localhost:9002
</span></span></code></div></div></pre>

The dev device credentials (used by tests and the gateway) are:

<pre class="overflow-visible!" data-start="1276" data-end="1351"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-text"><span><span>X-Device-Fp: DEV-ROUTER-CLIENT
X-Device-Token: dev-router-token
</span></span></code></div></div></pre>

---

## 2️⃣ Start the Mock BLE Adapter

The router forwards outgoing chunks to a BLE adapter (or mock) via:

<pre class="overflow-visible!" data-start="1473" data-end="1588"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-python"><span><span>BLE_ADAPTER_URL = ROUTING_CFG.get(
    </span><span>"ble_adapter_url"</span><span>, </span><span>"http://localhost:7003/v1/ble/send_chunk"</span><span>
)
</span></span></code></div></div></pre>

Typical dev command (adjust to your project layout):

<pre class="overflow-visible!" data-start="1644" data-end="1734"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-bash"><span><span>uvicorn services.ble_adapter_service.mock_ble:app \
  --port 7003 \
  --reload
</span></span></code></div></div></pre>

The router will POST JSON like:

<pre class="overflow-visible!" data-start="1769" data-end="1821"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>
  </span><span>"chunk"</span><span>:</span><span></span><span>{</span><span> ...MessageEnvelope... </span><span>}</span><span>
</span><span>}</span><span>
</span></span></code></div></div></pre>

to `http://localhost:7003/v1/ble/send_chunk`.

---

## 3️⃣ Manual Router Smoke Test

### Enqueue a message

Use the **authenticated** dev headers and `/v1/router/enqueue`:

<pre class="overflow-visible!" data-start="1996" data-end="2508"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-bash"><span><span>curl -X POST http://localhost:9002/v1/router/enqueue \
  -H </span><span>"Content-Type: application/json"</span><span> \
  -H </span><span>"X-Device-Fp: DEV-ROUTER-CLIENT"</span><span> \
  -H </span><span>"X-Device-Token: dev-router-token"</span><span> \
  -d '{
        "header": {
          "sender_fp": "A",
          "recipient_fp": "B",
          "msg_id": "test-123",
          "nonce": "dummy-nonce",
          "ttl": 4,
          "hop_count": 0,
          "ts": 1700000000
        },
        "ciphertext": "deadbeef",
        "chunks": {},
        "routing": {}
      }'
</span></span></code></div></div></pre>

Expected response (simplified):

<pre class="overflow-visible!" data-start="2543" data-end="2599"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>
  </span><span>"queued"</span><span>:</span><span></span><span>true</span><span></span><span>,</span><span>
  </span><span>"msg_id"</span><span>:</span><span></span><span>"test-123"</span><span>
</span><span>}</span><span>
</span></span></code></div></div></pre>

> **Note – payload limits:**
>
> If the serialized envelope or `ciphertext` exceeds the configured limits
>
> (`max_envelope_bytes`, `max_ciphertext_bytes`), the router returns
>
> **HTTP 413** with error code `INVALID_INPUT` and logs `ENVELOPE_TOO_LARGE` or
>
> `CIPHERTEXT_TOO_LARGE` to the IDS log.

### Check queue / stats (admin role)

With dev credentials (which have `admin` role), you can inspect:

<pre class="overflow-visible!" data-start="3006" data-end="3155"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-bash"><span><span>curl -X GET http://localhost:9002/v1/router/queue_debug \
  -H </span><span>"X-Device-Fp: DEV-ROUTER-CLIENT"</span><span> \
  -H </span><span>"X-Device-Token: dev-router-token"</span><span>
</span></span></code></div></div></pre>

and:

<pre class="overflow-visible!" data-start="3163" data-end="3306"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-bash"><span><span>curl -X GET http://localhost:9002/v1/router/stats \
  -H </span><span>"X-Device-Fp: DEV-ROUTER-CLIENT"</span><span> \
  -H </span><span>"X-Device-Token: dev-router-token"</span><span>
</span></span></code></div></div></pre>

> Note: These endpoints are only available when `ROUTER_DEBUG=1`.

---

## 4️⃣ Running the Test Suites

### A. Routing Config & API Behavior (in-process)

These tests use `TestClient` directly against `routing_api.app` and monkey-patch config values.

<pre class="overflow-visible!" data-start="3560" data-end="3634"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-bash"><span><span>pytest services/routing_service/test/routing_config_test.py -v
</span></span></code></div></div></pre>

This suite verifies:

#### TTL policy & enqueue validation

* `test_enqueue_rejects_ttl_below_min`
* `test_enqueue_rejects_ttl_above_max`
* `test_enqueue_uses_default_ttl_when_none`

Checks that `/v1/router/enqueue`:

* Rejects TTL outside [`ttl_min`, `max_ttl`] → `400 INVALID_INPUT`
* Applies `ttl_default` if client omits TTL

#### **Payload size limits (DoS protection)**

* `test_enqueue_rejects_oversized_ciphertext`

This test temporarily forces a very low `MAX_CIPHERTEXT_BYTES` and sends an envelope with an oversized `ciphertext`.

Expected behavior:

* `/v1/router/enqueue` returns **HTTP 413 (Payload Too Large)**
* Error code is still `INVALID_INPUT`
* Internally, `_check_envelope_size()` logs a `CIPHERTEXT_TOO_LARGE` event to the IDS log.

In normal operation, the size limits are loaded from the YAML config:

<pre class="overflow-visible!" data-start="4463" data-end="4645"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-yaml"><span><span># config/routing_config.yaml</span><span>
</span><span>max_envelope_bytes:</span><span></span><span>16384</span><span></span><span># ~16 KB max serialized envelope size</span><span>
</span><span>max_ciphertext_bytes:</span><span></span><span>16384</span><span></span><span># ~16 KB max ciphertext (per message)</span><span>
</span></span></code></div></div></pre>

These values feed into the module-level constants:

<pre class="overflow-visible!" data-start="4699" data-end="4850"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-python"><span><span>MAX_ENVELOPE_BYTES = ROUTING_CFG.get(</span><span>"max_envelope_bytes"</span><span>, </span><span>16_384</span><span>)
MAX_CIPHERTEXT_BYTES = ROUTING_CFG.get(</span><span>"max_ciphertext_bytes"</span><span>, </span><span>16_384</span><span>)
</span></span></code></div></div></pre>

so you can tighten or loosen them without code changes.

#### Timestamp freshness on enqueue

* `test_enqueue_drops_too_old_message`

Ensures old messages are logically dropped with:

<pre class="overflow-visible!" data-start="5036" data-end="5086"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>"queued"</span><span>:</span><span></span><span>false</span><span></span><span>,</span><span></span><span>"reason"</span><span>:</span><span></span><span>"too_old"</span><span>}</span><span>
</span></span></code></div></div></pre>

#### Auth & auth-level rate limiting

* `test_missing_auth_headers_returns_401`
* `test_bad_token_returns_401`
* `test_bad_device_fp_returns_401`
* `test_auth_rate_limit_returns_429`

Verifies that:

* Missing/incorrect dev credentials → `401 UNAUTHORIZED`
* When the **auth-level rate limiter** (`is_rate_limited("auth:<ip>")`) triggers, `/enqueue` returns **429** with error code `UNAUTHORIZED`.

#### BLE ingress behavior

* `test_on_chunk_received_action_final_by_default`
* `test_on_chunk_received_action_forward_when_enabled`
* `test_on_chunk_received_rejects_future_timestamp`
* `test_on_chunk_received_drops_old_message`
* `test_on_chunk_received_rejects_ttl_above_max`
* `test_peer_normalization_uses_sender_fp_for_ids`

These check `/v1/router/on_chunk_received`:

* Uses `"action": "final"` when `forwarding_enabled = false`.
* Uses `"action": "forward"` when `forwarding_enabled = true`.
* Rejects messages with future timestamps (`INVALID_INPUT`).
* Drops old messages logically (`accepted: false, action: "drop"`).
* Enforces TTL bounds and validity.
* **Normalizes peer identity** to `header.sender_fp` for IDS, even if `link_meta.peer` is spoofed.

#### Debug/admin endpoints & log anonymization

* `test_queue_debug_disabled_when_debug_mode_false`
* `test_queue_debug_enabled_when_debug_mode_true`
* `test_stats_disabled_when_debug_mode_false`
* `test_ids_log_tail_anonymizes_identifiers`

Confirms:

* Admin/debug endpoints are gated by `DEBUG_MODE` + admin role.
* `/v1/router/ids_log_tail` returns anonymized `peer` / `msg_id` (no raw identifiers).

#### IDS & DB behavior

* `test_block_peer_after_threshold`
* `test_blocked_peer_auto_unblocks_after_ttl`
* `test_duplicate_ttl_eviction`
* `test_queue_full_returns_db_error`
* `test_mark_dropped_removes_from_outgoing`

These verify:

* Peers are blocked after a configurable number of suspicious events and auto-unblocked after `BLOCK_PEER_TTL`.
* Duplicate detection has a TTL window and evicts old msg_ids.
* When the queue is full, `/enqueue` returns `500 DB_ERROR`.
* `mark_dropped()` removes rows from `get_outgoing()` so dropped messages are not retried.

---

### B. IDS-focused tests (if you keep a separate file)

If you have a dedicated IDS test file (e.g. `routing_ids.py`), run:

<pre class="overflow-visible!" data-start="7351" data-end="7417"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-bash"><span><span>pytest services/routing_service/test/routing_ids.py -v
</span></span></code></div></div></pre>

This typically covers:

* Sliding-window rate limiting edge cases
* Duplicate cache behavior
* Suspicious logging format

(Adjust filename if your IDS tests live elsewhere.)

---

### C. End-to-End Router + IDS Scenarios (real running service)

These tests hit the **real router** on `http://localhost:9002` using `httpx.AsyncClient`, so **you must have uvicorn running** as in step 1.

<pre class="overflow-visible!" data-start="7806" data-end="7873"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-bash"><span><span>pytest services/routing_service/test/routing_test.py -v
</span></span></code></div></div></pre>

It verifies security behavior under realistic conditions:

#### 1. Message storm / rate limiting

`test_message_storm_triggers_rate_limit`

* Sends ~40 messages from a single peer.
* Expects:
  * Some `accepted`
  * Some `dropped` due to `is_rate_limited(peer)`

Confirms the **per-peer sliding-window rate limiter** engages during a flood.

#### 2. Node churn with multiple peers

`test_node_churn_multiple_peers_ok`

* Simulates 5 peers, each sending 3 messages.
* Expects:
  * All HTTP responses `200`
  * Majority of messages `accepted` (no over-aggressive blocking)

This checks the router stays healthy under  **normal mesh activity** , not just attack scenarios.

#### 3. Partition / TTL expired behavior

`test_partition_ttl_expired`

* Sends envelopes with `ttl=0`.
* Expects:
  * HTTP **410** with error code `TTL_EXPIRED`.

This proves your TTL guard works as a  **routing loop + misconfiguration defense** .
