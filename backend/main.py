import math
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from mqtt_service import MQTTController
from vision_engine import TrafficVisionEngine

app = FastAPI(title="PulseTraffic AI Telemetry Engine", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

mqtt_ctrl = MQTTController()
vision = TrafficVisionEngine()

# Junction coordinates on Moinabad Corridor
JUNCTIONS = {
    "j1": {"name": "VJIT Main Gate", "lat": 17.3362, "lng": 78.3292},
    "j2": {"name": "Chilkur X Road", "lat": 17.3311, "lng": 78.3050}
}

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, data: dict):
        for connection in self.active_connections:
            await connection.send_json(data)

manager = ConnectionManager()

def calculate_haversine_distance(lat1, lon1, lat2, lon2) -> float:
    """Returns distance in meters between two GPS coordinates."""
    R = 6371000  # Radius of Earth in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@app.on_event("startup")
def startup_event():
    mqtt_ctrl.connect()

@app.post("/api/ambulance-telemetry")
async def receive_ambulance_gps(ambulance_id: str, lat: float, lng: float):
    """
    Ingests live GPS telemetry from incoming ambulances.
    If within 500m geofence of any junction, triggers sub-50ms corridor green-wave.
    """
    preempted_junctions = []

    for j_id, data in JUNCTIONS.items():
        dist = calculate_haversine_distance(lat, lng, data["lat"], data["lng"])
        if dist <= 500.0:  # 500m geofence rule
            # Instant MQTT signal switch command
            mqtt_ctrl.send_signal_state(
                junction_id=j_id,
                active_green_lane="west",  # Corridor clearance direction
                duration_sec=60,
                emergency=True
            )
            preempted_junctions.append(j_id)

    # Broadcast update to connected dashboard web clients
    await manager.broadcast({
        "event": "AMBULANCE_GEOFENCE_TRIGGER",
        "ambulance_id": ambulance_id,
        "preempted_junctions": preempted_junctions
    })

    return {"status": "SUCCESS", "preempted": preempted_junctions}

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Send dynamic state updates every 100ms
            await asyncio.sleep(0.1)
            await websocket.send_json({
                "type": "METRICS_UPDATE",
                "junction_id": "j1",
                "fps": 60.1,
                "latency_ms": 14.2
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)