
# Please add your service info here, then we integrate and make updated one for the app

# Routing Service – Quick Start

This service handles  **message routing** ,  **TTL + hop count** ,  **queueing** ,  **retry/backoff** , and **forwarding** chunks to the BLE adapter.

---

## 🚀 1. Start the Routing Service

From project root:

<pre class="overflow-visible!" data-start="523" data-end="646"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-bash"><span><span>cd</span><span></span><span>"D:\fall 2025\Information security\project\resilient-mesh-messaging"</span><span>
python -m services.routing_service.main
</span></span></code></div></div></pre>

This launches FastAPI via Uvicorn on:

<pre class="overflow-visible!" data-start="687" data-end="714"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>http:</span><span>//0.0.0.0:9002</span><span>
</span></span></code></div></div></pre>

On startup the router:

* Initializes SQLite (`routing.db`) router_db
* Starts the async routing loop (`routing_loop()`) that drains the queue every 2 seconds router_loop

---

## 📡 2. Start the Mock BLE Adapter (optional)

<pre class="overflow-visible!" data-start="997" data-end="1079"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-bash"><span><span>uvicorn services.ble_adapter_service.mock_ble:app --port 7003 --reload
</span></span></code></div></div></pre>

Router will POST outgoing chunks to:

<pre class="overflow-visible!" data-start="1119" data-end="1166"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>http://localhost:7003/v1/ble/send_chunk
</span></span></code></div></div></pre>

---

## 📨 3. Enqueue a Message (manual test)

Use this Windows-compatible `curl`:

<pre class="overflow-visible!" data-start="1252" data-end="1587"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-cmd"><span>curl -X POST http://localhost:9002/enqueue_message ^
  -H "Content-Type: application/json" ^
  -d "{\"msg_id\":\"test-123\",\"envelope\":\"{\\\"msg_id\\\":\\\"test-123\\\",\\\"sender\\\":\\\"A\\\",\\\"recipient\\\":\\\"B\\\",\\\"ttl\\\":3,\\\"hops\\\":0,\\\"nonce\\\":\\\"n1\\\",\\\"ciphertext\\\":\\\"abc\\\"}\",\"ttl\":3}"
</span></code></div></div></pre>

Expected response:

<pre class="overflow-visible!" data-start="1609" data-end="1640"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>"status"</span><span>:</span><span>"queued"</span><span>}</span><span>
</span></span></code></div></div></pre>

The router loop will then forward the envelope to the BLE mock and mark it delivered.

---

## 🔌 4. Test BLE Mock Directly

Port  **9001 is NOT the router** —it belongs to the BLE adapter and only exposes `/send_chunk`.

To test BLE:

<pre class="overflow-visible!" data-start="1876" data-end="2036"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-cmd"><span>curl -X POST http://localhost:9001/send_chunk ^
  -H "Content-Type: application/json" ^
  -d "{\"envelope\":{\"msg_id\":\"dummy\",\"sender\":\"X\"}}"
</span></code></div></div></pre>

In BLE console you should see:

<pre class="overflow-visible!" data-start="2070" data-end="2169"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre!"><span><span>[MOCK BLE]</span><span> Received chunk:
{
  "envelope": {
    "msg_id": </span><span>"dummy"</span><span>,
    </span><span>"sender"</span><span>: </span><span>"X"</span><span>
  }
}
</span></span></code></div></div></pre>

---

## 🔄 5. End-to-End Pipeline Test

1. **Start routing service (9002)**
2. **Start BLE mock (7003)**
3. Enqueue a message:

<pre class="overflow-visible!" data-start="2299" data-end="2634"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-cmd"><span>curl -X POST http://localhost:9002/enqueue_message ^
  -H "Content-Type: application/json" ^
  -d "{\"msg_id\":\"test-123\",\"envelope\":\"{\\\"msg_id\\\":\\\"test-123\\\",\\\"sender\\\":\\\"A\\\",\\\"recipient\\\":\\\"B\\\",\\\"ttl\\\":3,\\\"hops\\\":0,\\\"nonce\\\":\\\"n1\\\",\\\"ciphertext\\\":\\\"abc\\\"}\",\"ttl\":3}"
</span></code></div></div></pre>

Then the router loop:

* Reads row from SQLite
* Decrements TTL / increments hop count
* Sends to BLE via `/v1/ble/send_chunk`
* Marks as delivered or retries with exponential backoff router_loop

---

## 🧪 6. Running Unit Tests

The routing tests use `pytest`.

<pre class="overflow-visible!" data-start="2926" data-end="2992"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-bash"><span><span>pytest services/routing_service/test/routing_ids.py -v
</span></span></code></div></div></pre>

This covers IDS behavior (`duplicate`, `rate limiting`, suspicious logging) implemented in `ids_module.py`
