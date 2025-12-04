# Routing Service - Quick Test Guide

This service handles  **message routing** ,  **TTL + hop count** ,  **queueing** ,  **retry/backoff** , and forwarding chunks to the BLE adapter.

---

## 🚀 1. Start the Routing Service

From project root:

<pre class="overflow-visible!" data-start="444" data-end="567"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-bash"><span><span>cd</span><span></span><span>" resilient-mesh-messaging"</span><span>
pytest services/routing_service/test/routing_ids.py -v
</span></span></code></div></div></pre>

This launches FastAPI via Uvicorn on:

<pre class="overflow-visible!" data-start="608" data-end="635"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>http:</span><span>//0.0.0.0:9002</span><span>
</span></span></code></div></div></pre>

On startup the router:

* Initializes SQLite (`routing.db`)
* Starts the async routing loop (`routing_loop()`) that drains the queue every 2 seconds

---

## 📡 2. Start the Mock BLE Adapter (optional)

<pre class="overflow-visible!" data-start="840" data-end="922"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-bash"><span><span>uvicorn services.ble_adapter_service.mock_ble:app --port 7003 --reload
</span></span></code></div></div></pre>

Router will POST outgoing chunks to:

<pre class="overflow-visible!" data-start="962" data-end="1009"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>http://localhost:7003/v1/ble/send_chunk
</span></span></code></div></div></pre>

---

## 📨 3. Enqueue a Message (manual test)

Windows-compatible example:

<pre class="overflow-visible!" data-start="1087" data-end="1422"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-cmd"><span>curl -X POST http://localhost:9002/enqueue_message ^
  -H "Content-Type: application/json" ^
  -d "{\"msg_id\":\"test-123\",\"envelope\":\"{\\\"msg_id\\\":\\\"test-123\\\",\\\"sender\\\":\\\"A\\\",\\\"recipient\\\":\\\"B\\\",\\\"ttl\\\":3,\\\"hops\\\":0,\\\"nonce\\\":\\\"n1\\\",\\\"ciphertext\\\":\\\"abc\\\"}\",\"ttl\":3}"
</span></code></div></div></pre>

Expected:

<pre class="overflow-visible!" data-start="1435" data-end="1467"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>"status"</span><span>:</span><span></span><span>"queued"</span><span>}</span><span>
</span></span></code></div></div></pre>

The router loop then forwards the envelope to the BLE mock and marks it delivered.

---

## 🔌 4. Test BLE Mock Directly

Port **9001 is NOT the router** — it's the BLE adapter and only exposes `/send_chunk`.

<pre class="overflow-visible!" data-start="1679" data-end="1839"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-cmd"><span>curl -X POST http://localhost:9001/send_chunk ^
  -H "Content-Type: application/json" ^
  -d "{\"envelope\":{\"msg_id\":\"dummy\",\"sender\":\"X\"}}"
</span></code></div></div></pre>

BLE mock output:

<pre class="overflow-visible!" data-start="1859" data-end="1958"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>[MOCK BLE]</span><span> Received chunk:
{
  "envelope": {
    "msg_id": </span><span>"dummy"</span><span>,
    </span><span>"sender"</span><span>: </span><span>"X"</span><span>
  }
}
</span></span></code></div></div></pre>

---

## 🔄 5. End-to-End Pipeline Test

1. Start routing service (9002)
2. Start BLE mock (7003)
3. Enqueue a message:

<pre class="overflow-visible!" data-start="2084" data-end="2419"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-cmd"><span>curl -X POST http://localhost:9002/enqueue_message ^
  -H "Content-Type: application/json" ^
  -d "{\"msg_id\":\"test-123\",\"envelope\":\"{\\\"msg_id\\\":\\\"test-123\\\",\\\"sender\\\":\\\"A\\\",\\\"recipient\\\":\\\"B\\\",\\\"ttl\\\":3,\\\"hops\\\":0,\\\"nonce\\\":\\\"n1\\\",\\\"ciphertext\\\":\\\"abc\\\"}\",\"ttl\":3}"
</span></code></div></div></pre>

The router loop will:

* Read row from SQLite
* Decrement TTL / increment hop count
* Send to BLE via `/v1/ble/send_chunk`
* Mark as delivered or retry with exponential backoff

---

## 🧪 6. Running Unit Tests

### IDS-only tests

<pre class="overflow-visible!" data-start="2661" data-end="2727"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-bash"><span><span>pytest services/routing_service/test/routing_ids.py -v
</span></span></code></div></div></pre>

Covers:

* Duplicate detection
* Per-peer rate limiting
* Suspicious logging
* Sliding-window behavior

---

## 🔐 7. Full Routing Security & Resilience Tests

To test **all security-critical router behaviors end-to-end** (not just IDS logic), use:

<pre class="overflow-visible!" data-start="2987" data-end="3054"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-bash"><span><span>pytest services/routing_service/test/routing_test.py -v
</span></span></code></div></div></pre>

This suite probes the *real running router* using `/v1/router/on_chunk_received`.

What it verifies:

### **1. Message Storm Handling (Rate Limit Defense)**

`test_message_storm_triggers_rate_limit` sends ~40 messages from one peer.

Expected:

* Early messages → `accepted`
* Later messages → `dropped`
* Confirms **sliding-window rate-limit** correctly triggers

### **2. Node Churn Simulation (Multiple Peers Healthy)**

`test_node_churn_multiple_peers_ok` spreads messages across 5 different peers.

Expected:

* Most messages accepted
* Ensures the router tolerates **normal mesh activity** without false positives

### **3. TTL Security Check / Partition Behavior**

`test_partition_ttl_expired` sends TTL=0 envelopes.

Expected:

* Router returns **HTTP 410**
* Standard error code `TTL_EXPIRED`
* Confirms enforced hop-limit & replay/loop protection

-------------------------------------------------------------------------------------------------

# 🧪 Routing Config – Quick Test Guide

These tests validate that the router actually **honors your YAML config** (TTL bounds, forwarding mode, IDS thresholds, queue limits).

Run from project root:

<pre class="overflow-visible!" data-start="201" data-end="275"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-bash"><span><span>pytest services/routing_service/test/routing_config_test.py -v
</span></span></code></div></div></pre>

The tests talk directly to the routing API using the dev auth headers and monkey-patch different config values to simulate edge cases.

---

### 2️⃣ What these tests are checking

**TTL policy & enqueue behavior**

* `test_enqueue_rejects_ttl_below_min`

  Ensures `/v1/router/enqueue` rejects messages with TTL < `ttl_min` → `400 INVALID_INPUT`.

  👉 Prevents misconfigured or malicious clients from injecting “dead” messages that should never be forwarded.
* `test_enqueue_rejects_ttl_above_max`

  Ensures messages with TTL > `max_ttl` are also rejected → `400 INVALID_INPUT`.

  👉 Prevents routing loops and run-away multi-hop flooding.
* `test_enqueue_uses_default_ttl_when_none`

  If TTL is missing, the router uses `ttl_default` instead of silently accepting `None`.

  👉 Prevents ambiguous TTL behavior and enforces a safe default.

---

**Forwarding mode vs final delivery**

* `test_on_chunk_received_action_final_by_default`

  With `forwarding_enabled=false`, incoming wireless chunks return `{"accepted": true, "action": "final"}`.

  👉 Confirms default behavior is local delivery only (no accidental multi-hop).
* `test_on_chunk_received_action_forward_when_enabled`

  With `forwarding_enabled=true`, the same chunk returns `{"accepted": true, "action": "forward"}`.

  👉 Ensures multi-hop routing is only enabled when explicitly configured.

---

**IDS blocking & duplicate suppression**

* `test_block_peer_after_threshold`

  With a low `block_peer_after` value, repeated suspicious events cause a peer to be treated as rate-limited/blocked.

  👉 Defends against persistent abusive senders by automatically quarantining them.
* `test_duplicate_ttl_eviction`

  With a short `duplicate_suppression_ttl`, a msg_id is considered duplicate only within that window, then evicted.

  👉 Prevents replay attacks in a time window **and** avoids unbounded memory growth in the duplicate cache.

---

**Queue saturation handling**

* `test_queue_full_returns_db_error`

  With `max_queue_size` forced to 0, the first enqueue fails with `500 DB_ERROR`.

  👉 Verifies the router fails closed when the queue is full (DoS / disk-full scenarios), instead of silently accepting messages it cannot store.
