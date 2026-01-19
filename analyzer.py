import cv2
import yt_dlp
import os
import numpy as np
from datetime import timedelta

class ExternalAuditEngine:
    def __init__(self, upload_folder="temp_files"):
        self.upload_folder = upload_folder
        os.makedirs(upload_folder, exist_ok=True)

    def download_video_data(self, youtube_url):
        # Baixa metadados PÚBLICOS e o arquivo de vídeo
        print(f"📥 Coletando dados: {youtube_url}...")
        ydl_opts = {
            'format': 'best[height<=720]',
            'outtmpl': os.path.join(self.upload_folder, '%(id)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            filename = ydl.prepare_filename(info)
            
            metadata = {
                "title": info.get('title'),
                "channel": info.get('uploader'),
                "view_count": info.get('view_count', 0),
                "duration": info.get('duration', 0),
                "thumbnail": info.get('thumbnail')
            }
            return filename, metadata

    def calculate_audience_decay(self, appearance_time, total_duration, total_views):
        # Estimativa de quantas pessoas viram naquele segundo (Decaimento linear)
        if total_duration == 0: return total_views
        
        position_percent = appearance_time / total_duration
        # Começa com 100% (1.0) e cai até 40% (0.4) no final
        retention_factor = 1.0 - (position_percent * 0.6)
        
        return int(total_views * retention_factor)

    def scan(self, video_path, logo_path, metadata, cpm=25.00):
        print(f"👁️ Analisando vídeo '{metadata['title']}'...")
        
        img_logo = cv2.imread(logo_path, cv2.IMREAD_GRAYSCALE)
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Detector SIFT
        sift = cv2.SIFT_create()
        kp_logo, des_logo = sift.detectAndCompute(img_logo, None)
        
        # Configuracao do Matcher
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
            if not ret: break
            
            frame_count += 1
            if frame_count % frame_skip != 0: continue

            # Redimensiona para analisar rapido
            frame_mini = cv2.resize(frame, (0,0), fx=0.5, fy=0.5)
            frame_gray = cv2.cvtColor(frame_mini, cv2.COLOR_BGR2GRAY)
            kp_frame, des_frame = sift.detectAndCompute(frame_gray, None)

            is_visible = False
            if des_frame is not None and len(des_frame) > 0:
                matches = flann.knnMatch(des_logo, des_frame, k=2)
                good = [m for m, n in matches if m.distance < 0.7 * n.distance]
                if len(good) > 12: # Sensibilidade de detecção
                    is_visible = True

            current_seconds = frame_count / fps

            if is_visible:
                # Calcula valor financeiro deste instante
                estimated_viewers = self.calculate_audience_decay(
                    current_seconds, metadata['duration'], metadata['view_count']
                )
                
                # Matematica: Valor = (Viewers/1000) * (CPM/30s) * (DuracaoFrame)
                cpm_per_second = cpm / 30.0
                frame_duration = frame_skip / fps
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
                "start": str(timedelta(seconds=int(d['start']))),
                "end": str(timedelta(seconds=int(d['end']))),
                "seconds_raw": round(d['start'], 2),
                "duration": round(d['end'] - d['start'], 2)
            })

        return {
            "video_title": metadata['title'],
            "channel": metadata['channel'],
            "total_views": metadata['view_count'],
            "total_screen_time_seconds": sum([c['duration'] for c in result_clips]),
            "media_value_brl": round(accumulated_media_value, 2),
            "timeline_clips": result_clips
        }
