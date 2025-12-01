# ble_adapter/mock_ble.py
from fastapi import FastAPI
import json

app = FastAPI()

@app.post("/v1/ble/send_chunk")
def receive_chunk(payload: dict):
    print("[MOCK BLE] Received chunk:")
    print(json.dumps(payload, indent=2))
    return {"queued": True, "estimate_ms": 150}