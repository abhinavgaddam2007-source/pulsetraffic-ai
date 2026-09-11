import cv2
import numpy as np
from ultralytics import YOLO

class TrafficVisionEngine:
    def __init__(self, model_path: str = "yolov8n.pt"):
        # Load lightweight YOLOv8 nano model for high FPS (<15ms per frame)
        self.model = YOLO(model_path)
        # Class IDs for vehicles: 2=car, 3=motorcycle, 5=bus, 7=truck
        self.vehicle_classes = [2, 3, 5, 7]

    def process_frame(self, frame: np.ndarray, lane_rois: dict) -> dict:
        """
        Processes camera frame and calculates vehicle density per defined Lane ROI.
        """
        results = self.model(frame, verbose=False)[0]
        lane_counts = {lane: 0 for lane in lane_rois.keys()}

        for box in results.boxes:
            cls_id = int(box.cls[0])
            if cls_id in self.vehicle_classes:
                # Bounding box center coordinate
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                # Check which Lane Region Of Interest (ROI) contains the vehicle
                for lane, polygon in lane_rois.items():
                    if cv2.pointPolygonTest(np.array(polygon, np.int32), (cx, cy), False) >= 0:
                        lane_counts[lane] += 1
                        break

        return lane_counts