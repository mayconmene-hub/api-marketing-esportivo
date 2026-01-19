import cv2
import os
import numpy as np
from datetime import timedelta

class ExternalAuditEngine:
def init(self, upload_folder="temp_files"):
self.upload_folder = upload_folder
os.makedirs(upload_folder, exist_ok=True)

def calculate_audience_decay(self, appearance_time, total_duration, total_views):
    # início = 100% dos views, fim = 40%
    if total_duration == 0:
        return total_views
    position_percent = appearance_time / total_duration
    retention_factor = 1.0 - (position_percent * 0.6)
    return int(total_views * retention_factor)

def scan(self, video_path, logo_path, metadata, cpm=25.00):
    img_logo = cv2.imread(logo_path, cv2.IMREAD_GRAYSCALE)
    if img_logo is None:
        raise ValueError("Não foi possível ler a imagem da logo.")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Não foi possível abrir o vídeo para análise.")

    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    total_frames_video = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    # Se a duração não veio da API, calcula pela mídia
    if not metadata.get("duration") and fps > 0:
        metadata["duration"] = int(total_frames_video / fps)

    total_duration = int(metadata.get("duration", 0) or 0)
    total_views = int(metadata.get("view_count", 0) or 0)

    sift = cv2.SIFT_create()
    kp_logo, des_logo = sift.detectAndCompute(img_logo, None)
    if des_logo is None:
        raise ValueError("Não foi possível extrair features da logo (imagem ruim/pequena).")

    index_params = dict(algorithm=1, trees=5)
    search_params = dict(checks=50)
    flann = cv2.FlannBasedMatcher(index_params, search_params)

    detections = []
    current_event = None
    frame_skip = 10
    frame_count = 0
    accumulated_media_value = 0.0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        if frame_count % frame_skip != 0:
            continue

        frame_mini = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        frame_gray = cv2.cvtColor(frame_mini, cv2.COLOR_BGR2GRAY)
        kp_frame, des_frame = sift.detectAndCompute(frame_gray, None)

        is_visible = False
        if des_frame is not None and len(des_frame) > 0:
            matches = flann.knnMatch(des_logo, des_frame, k=2)
            good = [m for m, n in matches if m.distance < 0.7 * n.distance]
            if len(good) > 12:
                is_visible = True

        current_seconds = (frame_count / fps) if fps > 0 else 0.0

        if is_visible:
            estimated_viewers = self.calculate_audience_decay(
                current_seconds, total_duration, total_views
            )

            cpm_per_second = cpm / 30.0
            frame_duration = (frame_skip / fps) if fps > 0 else 0.0
            instant_value = (estimated_viewers / 1000.0) * cpm_per_second * frame_duration
            accumulated_media_value += instant_value

            if current_event is None:
                current_event = {"start": current_seconds, "end": current_seconds}
            else:
                current_event["end"] = current_seconds
        else:
            if current_event:
                if (current_event["end"] - current_event["start"]) > 1.0:
                    detections.append(current_event)
                current_event = None

    cap.release()

    result_clips = []
    for d in detections:
        result_clips.append({
            "start": str(timedelta(seconds=int(d["start"]))),
            "end": str(timedelta(seconds=int(d["end"]))),
            "seconds_raw": round(d["start"], 2),
            "duration": round(d["end"] - d["start"], 2),
        })

    return {
        "video_title": metadata.get("title"),
        "channel": metadata.get("channel"),
        "total_views": total_views,
        "total_screen_time_seconds": sum(c["duration"] for c in result_clips),
        "media_value_brl": round(accumulated_media_value, 2),
        "timeline_clips": result_clips,
    }
