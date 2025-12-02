# Day-0 API Contracts

Resilient Mesh Messaging — CS 166 (Fall 2025)
Team 11

This document defines **the shared APIs and message envelope format** agreed upon on Day-0.
All three services (Crypto, Router, BLE Adapter) must follow these contracts so they can be
developed independently and integrated successfully.

---

# 1. Envelope Schema (Shared)

Defined in: `contracts/envelope_schema.json`

```jsonc
{
  "version": "1.0",
  "header": {
    "sender_fp": "base64-32",
    "recipient_fp": "base64-32",
    "msg_id": "uuid-v4",
    "nonce": "base64-12",
    "ttl": 8,
    "hop_count": 0,
    "ts": 1730000000
  },
  "ciphertext": "base64",
  "chunks": {
    "index": 0,
    "total": 1
  },
  "routing": {
    "priority": "normal",
    "dup_suppress": true
  }
}
```



# Crypto Service API (Person 3)

Base URL: `http://localhost:7001`

### GET `/v1/crypto/public_key`

Response:

<pre class="overflow-visible!" data-start="3824" data-end="3915"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>
  </span><span>"curve"</span><span>:</span><span></span><span>"X25519"</span><span>,</span><span>
  </span><span>"public_key"</span><span>:</span><span></span><span>"base64"</span><span>,</span><span>
  </span><span>"fingerprint"</span><span>:</span><span></span><span>"base64-32"</span><span>
</span><span>}</span><span>
</span></span></code></div></div></pre>

### POST `/v1/crypto/derive_session_key`

Request:

<pre class="overflow-visible!" data-start="3967" data-end="4048"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span></span><span>"peer_public_key"</span><span>:</span><span></span><span>"base64"</span><span>,</span><span></span><span>"context"</span><span>:</span><span></span><span>"pair-qr|pair-code|adhoc"</span><span></span><span>}</span><span>
</span></span></code></div></div></pre>

Response:

<pre class="overflow-visible!" data-start="4059" data-end="4116"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span></span><span>"session_id"</span><span>:</span><span></span><span>"uuid"</span><span>,</span><span></span><span>"expires_in"</span><span>:</span><span></span><span>86400</span><span></span><span>}</span><span>
</span></span></code></div></div></pre>

### POST `/v1/crypto/encrypt`

Request:

<pre class="overflow-visible!" data-start="4157" data-end="4260"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span></span><span>"session_id"</span><span>:</span><span></span><span>"uuid"</span><span>,</span><span></span><span>"nonce"</span><span>:</span><span></span><span>"base64-12"</span><span>,</span><span></span><span>"plaintext"</span><span>:</span><span></span><span>"base64"</span><span>,</span><span></span><span>"aad"</span><span>:</span><span></span><span>"base64|null"</span><span></span><span>}</span><span>
</span></span></code></div></div></pre>

### POST `/v1/crypto/decrypt`

Request:

<pre class="overflow-visible!" data-start="4301" data-end="4405"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span></span><span>"session_id"</span><span>:</span><span></span><span>"uuid"</span><span>,</span><span></span><span>"nonce"</span><span>:</span><span></span><span>"base64-12"</span><span>,</span><span></span><span>"ciphertext"</span><span>:</span><span></span><span>"base64"</span><span>,</span><span></span><span>"aad"</span><span>:</span><span></span><span>"base64|null"</span><span></span><span>}</span><span>
</span></span></code></div></div></pre>

Errors:

* `NONCE_REUSE` (409)
* `INVALID_SESSION` (401)
* `REPLAY_DETECTED` (409)
* `AUTH_FAILED` (401)

---

# 3. Routing / Store-and-Forward API (Person 2)

Base URL: `http://localhost:7002`

### POST `/v1/router/enqueue`

Request:

<pre class="overflow-visible!" data-start="4639" data-end="4674"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span></span><span>"<MessageEnvelope>"</span><span></span><span>}</span><span>
</span></span></code></div></div></pre>

Response:

<pre class="overflow-visible!" data-start="4685" data-end="4733"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span></span><span>"queued"</span><span>:</span><span></span><span>true</span><span></span><span>,</span><span></span><span>"msg_id"</span><span>:</span><span></span><span>"uuid"</span><span></span><span>}</span><span>
</span></span></code></div></div></pre>

### GET `/v1/router/outgoing_chunks?limit=50`

Response:

<pre class="overflow-visible!" data-start="4791" data-end="4890"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>
  </span><span>"items"</span><span>:</span><span></span><span>[</span><span>
    </span><span>{</span><span></span><span>"chunk"</span><span>:</span><span></span><span>"<MessageEnvelope>"</span><span>,</span><span></span><span>"target_peer"</span><span>:</span><span></span><span>"fingerprint"</span><span></span><span>}</span><span>
  </span><span>]</span><span>
</span><span>}</span><span>
</span></span></code></div></div></pre>

### POST `/v1/router/mark_delivered`

Request:

<pre class="overflow-visible!" data-start="4938" data-end="5011"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span></span><span>"msg_id"</span><span>:</span><span></span><span>"uuid"</span><span>,</span><span></span><span>"chunk_index"</span><span>:</span><span></span><span>0</span><span>,</span><span></span><span>"peer"</span><span>:</span><span></span><span>"fingerprint"</span><span></span><span>}</span><span>
</span></span></code></div></div></pre>

### POST `/v1/router/on_chunk_received`

Request:

<pre class="overflow-visible!" data-start="5062" data-end="5163"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>
  </span><span>"chunk"</span><span>:</span><span></span><span>"<MessageEnvelope>"</span><span>,</span><span>
  </span><span>"link_meta"</span><span>:</span><span></span><span>{</span><span></span><span>"rssi"</span><span>:</span><span></span><span>-55</span><span>,</span><span></span><span>"peer"</span><span>:</span><span></span><span>"fingerprint"</span><span></span><span>}</span><span>
</span><span>}</span><span>
</span></span></code></div></div></pre>

Response:

<pre class="overflow-visible!" data-start="5174" data-end="5238"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span></span><span>"accepted"</span><span>:</span><span></span><span>true</span><span></span><span>,</span><span></span><span>"action"</span><span>:</span><span></span><span>"forward|drop|final"</span><span></span><span>}</span><span>
</span></span></code></div></div></pre>

Errors:

* `TTL_EXPIRED` (410)
* `DUPLICATE` (200, `{accepted:false}`)
* `RATE_LIMITED` (200, `{accepted:false}`)

---

# 4. BLE Transport Adapter (Person 1)

Base URL: `http://localhost:7003`

### POST `/v1/ble/send_chunk`

Request:

<pre class="overflow-visible!" data-start="5471" data-end="5545"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span></span><span>"chunk"</span><span>:</span><span></span><span>"<MessageEnvelope>"</span><span>,</span><span></span><span>"target_peer"</span><span>:</span><span></span><span>"fingerprint"</span><span></span><span>}</span><span>
</span></span></code></div></div></pre>

Response:

<pre class="overflow-visible!" data-start="5556" data-end="5606"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span></span><span>"queued"</span><span>:</span><span></span><span>true</span><span></span><span>,</span><span></span><span>"estimate_ms"</span><span>:</span><span></span><span>150</span><span></span><span>}</span><span>
</span></span></code></div></div></pre>

### GET `/v1/ble/neighbors`

Response:

<pre class="overflow-visible!" data-start="5646" data-end="5746"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>
  </span><span>"peers"</span><span>:</span><span></span><span>[</span><span>
    </span><span>{</span><span></span><span>"fingerprint"</span><span>:</span><span></span><span>"..."</span><span>,</span><span></span><span>"rssi"</span><span>:</span><span></span><span>-48</span><span>,</span><span></span><span>"last_seen"</span><span>:</span><span></span><span>17300000123</span><span></span><span>}</span><span>
  </span><span>]</span><span>
</span><span>}</span><span>
</span></span></code></div></div></pre>

### POST `/v1/ble/mock_incoming`  *(dev/test only)*

Request:

<pre class="overflow-visible!" data-start="5809" data-end="5876"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span></span><span>"chunk"</span><span>:</span><span></span><span>"<MessageEnvelope>"</span><span>,</span><span></span><span>"from"</span><span>:</span><span></span><span>"fingerprint"</span><span></span><span>}</span><span>
</span></span></code></div></div></pre>

---

# Error Format (all services)

Every service returns errors in the format:

<pre class="overflow-visible!" data-start="5959" data-end="6072"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>
  </span><span>"error"</span><span>:</span><span></span><span>{</span><span>
    </span><span>"code"</span><span>:</span><span></span><span>"STRING_CODE"</span><span>,</span><span>
    </span><span>"detail"</span><span>:</span><span></span><span>"human message"</span><span>,</span><span>
    </span><span>"retryable"</span><span>:</span><span></span><span>false</span><span>
  </span><span>}</span><span>
</span><span>}</span><span>
</span></span></code></div></div></pre>

Codes include:

`INVALID_INPUT`, `NOT_FOUND`, `UNAUTHORIZED`,

`REPLAY_DETECTED`, `NONCE_REUSE`, `DB_ERROR`,

`BLE_UNAVAILABLE`, `RATE_LIMITED`, `TTL_EXPIRED`,

`INTERNAL_ERROR`.
