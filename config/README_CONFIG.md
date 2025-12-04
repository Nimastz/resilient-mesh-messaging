# Routing Config (Brief Explanation)

<pre class="overflow-visible!" data-start="189" data-end="329"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-yaml"><span><span>max_retries:</span><span></span><span>5</span><span>
</span><span>base_retry_backoff_ms:</span><span></span><span>500</span><span>
</span><span>max_ttl:</span><span></span><span>8</span><span>
</span><span>drop_on_duplicate:</span><span></span><span>true</span><span>

</span><span>ids:</span><span>
  </span><span>window_seconds:</span><span></span><span>5</span><span>
  </span><span>max_msgs_per_window:</span><span></span><span>20</span><span>
</span></span></code></div></div></pre>

### **`max_retries: 5`**

How many times the router will retry sending a message before giving up.

After the 5th failed attempt, the message is marked as  **dropped** .

---

### **`base_retry_backoff_ms: 500`**

Base delay (in milliseconds) used for **exponential backoff** when retrying sends.

Retry delays are:

* 1st retry → 500 ms
* 2nd retry → 1000 ms
* 3rd retry → 2000 ms
* 4th retry → 4000 ms
* … (until `max_retries`)

This prevents the router from spamming BLE during failures.

---

### **`max_ttl: 8`**

The maximum allowed TTL (hop count) a message may carry.

Messages with TTL > 8 or TTL ≤ 0 are  **rejected or dropped** .

This protects the mesh from routing loops and runaway hops.

---

### **`drop_on_duplicate: true`**

If set, the router will **drop duplicate message IDs** immediately.

This prevents replay attacks and flooding via repeated re-injections.

(Handled by `is_duplicate()` inside the IDS module.)

---

# 🔐 IDS (Intrusion Detection) Settings

<pre class="overflow-visible!" data-start="1325" data-end="1387"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-yaml"><span><span>ids:</span><span>
  </span><span>window_seconds:</span><span></span><span>5</span><span>
  </span><span>max_msgs_per_window:</span><span></span><span>20</span><span>
</span></span></code></div></div></pre>

### **`window_seconds: 5`**

Time window for per-peer message rate counting.

The router tracks how many messages each peer sends inside the last  **5 seconds** .

---

### **`max_msgs_per_window: 20`**

Threshold for triggering  **rate limiting** .

If a peer sends more than 20 messages inside the 5-second window:

* Router flags it as suspicious
* IDS returns `"accepted": false, "action": "drop"`
* Event is logged in `routing_suspicious.log`

This protects against spam bursts and denial-of-service attempts.
