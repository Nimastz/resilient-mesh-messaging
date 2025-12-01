start router server by running  main -> uvicorn start on `http://0.0.0.0:9002`

cd "D:\fall 2025\Information security\project\resilient-mesh-messaging"
python -m services.routing_service.main

Once routing service is running, from another terminal you can enqueue a fake message. here is the corrected CMD version:

curl -X POST http://localhost:9002/enqueue_message ^ -H "Content-Type: application/json" ^ -d "{\"msg_id\":\"test-123\",\"envelope\":\"{\\\"msg_id\\\":\\\"test-123\\\",\\\"sender\\\":\\\"A\\\",\\\"recipient\\\":\\\"B\\\",\\\"ttl\\\":3,\\\"hops\\\":0,\\\"nonce\\\":\\\"n1\\\",\\\"ciphertext\\\":\\\"abc\\\"}\",\"ttl\":3}"



* **Port 9001** → `mock_ble_adapter`
  * Only has: `POST /send_chunk`
  * It does **NOT** have `/enqueue_message` → that’s why you see `404 Not Found`.
* **Port 9002** → `routing_service` (Person 2)
  * Has:
    * `POST /enqueue_message`
    * `GET /outgoing_chunks`
    * `POST /mark_delivered`

So:

> ❌ `curl ... http://localhost:9001/enqueue_message` → always 404
>
> ✅ `curl ... http://localhost:9002/enqueue_message` → correct for routing



test BLE mock with its real endpoint `/send_chunk`:

<pre class="overflow-visible!" data-start="1284" data-end="1444"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-cmd"><span>curl -X POST http://localhost:9001/send_chunk ^
  -H "Content-Type: application/json" ^
  -d "{\"envelope\":{\"msg_id\":\"dummy\",\"sender\":\"X\"}}"
</span></code></div></div></pre>

In the BLE terminal you should see:

<pre class="overflow-visible!" data-start="1483" data-end="1586"><div class="contain-inline-size rounded-2xl relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-text"><span><span>[MOCK BLE] Received chunk:
{
  "envelope": {
    "msg_id": "dummy",
    "sender": "X"
  }
}</span></span></code></div></div></pre>

test the full pipeline:


curl -X POST http://localhost:9002/enqueue_message ^
  -H "Content-Type: application/json" ^
  -d "{\"msg_id\":\"test-123\",\"envelope\":\"{\\\"msg_id\\\":\\\"test-123\\\",\\\"sender\\\":\\\"A\\\",\\\"recipient\\\":\\\"B\\\",\\\"ttl\\\":3,\\\"hops\\\":0,\\\"nonce\\\":\\\"n1\\\",\\\"ciphertext\\\":\\\"abc\\\"}\",\"ttl\":3}"
You should get back:

json
Copy code
{"status":"queued"}


run ble:

uvicorn services.ble_adapter_service.mock_ble:app --port 7003 --reload
