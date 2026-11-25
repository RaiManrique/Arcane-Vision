"""Motor de visión computacional en tiempo real para Arcane Vision.

Gestiona:
- Descarga automática de modelos oficiales .task (hand_landmarker y face_landmarker).
- Captura de webcam en hilo separado en modo espejo horizontal.
- Detección con MediaPipe Tasks (HandLandmarker + FaceLandmarker) en modo VIDEO.
- Conteo de dedos invariante a la inclinación, apertura bucal (jawOpen + MAR),
  escudo deflector angular (nudillos índice-meñique) e inclinación de cabeza (roll).
- Filtrado EMA y estabilización por cuadros (debounce).
"""

from __future__ import annotations

import math
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Lock, Thread
from time import monotonic_ns

import cv2
import mediapipe as mp
import numpy as np

import config


def ensure_models(progress_callback=None) -> tuple[Path, Path]:
    """Asegura que los modelos oficiales .task existan en Pc4/models/."""
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    targets = (
        ("HandLandmarker", config.HAND_MODEL_PATH, config.HAND_MODEL_URL),
        ("FaceLandmarker", config.FACE_MODEL_PATH, config.FACE_MODEL_URL),
    )

    for label, path, url in targets:
        if path.exists() and path.stat().st_size > 100_000:
            continue
        if progress_callback is not None:
            progress_callback(f"Descargando modelo {label}...")
        tmp_path = path.with_suffix(".task.tmp")
        req = urllib.request.Request(url, headers={"User-Agent": "ArcaneVision/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=45) as resp, tmp_path.open("wb") as out:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    out.write(chunk)
            if tmp_path.stat().st_size < 100_000:
                raise RuntimeError(f"Descarga incompleta para {label}")
            os.replace(tmp_path, path)
        except Exception:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise

    return config.HAND_MODEL_PATH, config.FACE_MODEL_PATH


class Debouncer:
    """Confirma un cambio de estado solo tras N cuadros consecutivos estables."""

    def __init__(self, initial_value, required_frames: int) -> None:
        self.value = initial_value
        self.required_frames = max(1, required_frames)
        self._candidate = initial_value
        self._streak = 0

    def update(self, raw_value):
        if raw_value == self.value:
            self._candidate = raw_value
            self._streak = 0
            return self.value
        if raw_value == self._candidate:
            self._streak += 1
            if self._streak >= self.required_frames:
                self.value = raw_value
                self._streak = 0
        else:
            self._candidate = raw_value
            self._streak = 1
        return self.value

    def reset(self, value) -> None:
        self.value = value
        self._candidate = value
        self._streak = 0


class AngleEMA:
    """Suavizado exponencial circular para ángulos en radianes (sin saltos en +-pi)."""

    def __init__(self, alpha: float) -> None:
        self.alpha = alpha
        self._cos: float | None = None
        self._sin: float | None = None

    def update(self, angle_rad: float) -> float:
        c = math.cos(angle_rad)
        s = math.sin(angle_rad)
        if self._cos is None or self._sin is None:
            self._cos, self._sin = c, s
        else:
            self._cos = (1.0 - self.alpha) * self._cos + self.alpha * c
            self._sin = (1.0 - self.alpha) * self._sin + self.alpha * s
            norm = math.hypot(self._cos, self._sin)
            if norm > 1e-6:
                self._cos /= norm
                self._sin /= norm
        return math.atan2(self._sin, self._cos)

    def reset(self) -> None:
        self._cos = None
        self._sin = None


@dataclass(slots=True)
class VisionState:
    """Estado biométrico filtrado correspondiente al cuadro más reciente."""

    frame_rgb: np.ndarray | None = None
    camera_available: bool = False
    camera_status: str = "Abriendo cámara..."

    # Mano dominante (hechizos y ataque)
    dominant_present: bool = False
    dominant_pos: tuple[float, float] = (config.SCREEN_WIDTH * 0.65, config.SCREEN_HEIGHT * 0.60)
    dominant_fingers: int = 0
    selected_spell: int = 1
    rapid_fire_active: bool = False

    # Mano secundaria (escudo deflector angular)
    shield_present: bool = False
    shield_active: bool = False
    shield_pos: tuple[float, float] = (config.SCREEN_WIDTH * 0.35, config.SCREEN_HEIGHT * 0.60)
    shield_angle: float = 0.0
    shield_fingers: int = 0

    # Rostro (boca + inclinación lateral de cabeza)
    face_present: bool = False
    mouth_open: bool = False
    mouth_metric: float = 0.0
    jaw_open: float = 0.0
    mouth_mar: float = 0.0
    head_roll_deg: float = 0.0
    head_move: float = 0.0

    # Configuración de lateralidad
    left_handed: bool = False


class _WebcamStream:
    """Hilo dedicado para capturar fotogramas de webcam sin bloquear Pygame."""

    def __init__(self, camera_index: int = 0) -> None:
        self.camera_index = camera_index
        self._lock = Lock()
        self._stop_event = Event()
        self.finished = Event()
        self.opened = Event()
        self._latest: tuple[int, np.ndarray] | None = None
        self._thread = Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        cap = None
        try:
            cap = cv2.VideoCapture(self.camera_index)
            if not cap.isOpened():
                return
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.DEFAULT_CAMERA_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.DEFAULT_CAMERA_HEIGHT)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.opened.set()

            while cap.isOpened() and not self._stop_event.is_set():
                ok, frame_bgr = cap.read()
                if not ok or frame_bgr is None:
                    break
                mirrored = cv2.flip(frame_bgr, 1)
                frame_rgb = cv2.cvtColor(mirrored, cv2.COLOR_BGR2RGB)
                ts_ms = monotonic_ns() // 1_000_000
                with self._lock:
                    self._latest = (ts_ms, frame_rgb)
        finally:
            if cap is not None:
                cap.release()
            self.finished.set()

    def read(self) -> tuple[int, np.ndarray] | None:
        with self._lock:
            sample = self._latest
            self._latest = None
        return sample

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=2.0)


class VisionEngine:
    """Encapsula MediaPipe HandLandmarker + FaceLandmarker con EMA y debounce."""

    def __init__(self, camera_index: int = 0, left_handed: bool = False) -> None:
        self.camera_index = camera_index
        self.left_handed = left_handed
        self.state = VisionState(left_handed=left_handed)

        self._stream: _WebcamStream | None = None
        self._hand_landmarker = None
        self._face_landmarker = None
        self._last_timestamp_ms: int = -1
        self._running = False

        # Filtros EMA
        self._dom_pos_ema: tuple[float, float] | None = None
        self._shield_pos_ema: tuple[float, float] | None = None
        self._shield_angle_ema = AngleEMA(config.EMA_SHIELD_ANGLE)
        self._head_roll_ema: float = 0.0
        self._mouth_ema: float = 0.0

        # Debouncers para estabilidad de gestos
        self._spell_debouncer = Debouncer(1, config.SPELL_DEBOUNCE_FRAMES)
        self._fire_debouncer = Debouncer(False, config.FIRE_PALM_DEBOUNCE_FRAMES)
        self._shield_debouncer = Debouncer(False, config.SHIELD_DEBOUNCE_FRAMES)

    def start(self, progress_callback=None) -> None:
        """Descarga modelos si faltan, crea detectores en modo VIDEO y abre webcam."""
        hand_model, face_model = ensure_models(progress_callback=progress_callback)

        vision = mp.tasks.vision
        hand_options = vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_buffer=hand_model.read_bytes()),
            running_mode=vision.RunningMode.VIDEO,
            num_hands=2,
            min_hand_detection_confidence=0.52,
            min_hand_presence_confidence=0.52,
            min_tracking_confidence=0.48,
        )
        face_options = vision.FaceLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_buffer=face_model.read_bytes()),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
            min_face_detection_confidence=0.50,
            min_face_presence_confidence=0.50,
            min_tracking_confidence=0.48,
            output_face_blendshapes=True,
        )

        self._hand_landmarker = vision.HandLandmarker.create_from_options(hand_options)
        self._face_landmarker = vision.FaceLandmarker.create_from_options(face_options)

        self._stream = _WebcamStream(self.camera_index)
        self._stream.start()
        self._running = True

    def stop(self) -> None:
        """Libera cámara y detectores de MediaPipe."""
        self._running = False
        if self._stream is not None:
            self._stream.stop()
            self._stream = None
        if self._hand_landmarker is not None:
            self._hand_landmarker.close()
            self._hand_landmarker = None
        if self._face_landmarker is not None:
            self._face_landmarker.close()
            self._face_landmarker = None

    def toggle_handedness(self) -> bool:
        """Intercambia dinámicamente mano de ataque y mano de escudo (soporte zurdos)."""
        self.left_handed = not self.left_handed
        self.state.left_handed = self.left_handed
        self._dom_pos_ema = None
        self._shield_pos_ema = None
        self._shield_angle_ema.reset()
        self._fire_debouncer.reset(False)
        self._shield_debouncer.reset(False)
        return self.left_handed

    def update(self) -> VisionState:
        """Procesa el último fotograma disponible y devuelve el VisionState filtrado."""
        if not self._running or self._stream is None:
            return self.state

        sample = self._stream.read()
        if sample is None:
            if self._stream.finished.is_set() and not self._stream.opened.is_set():
                self.state.camera_available = False
                self.state.camera_status = "Cámara no disponible (controles de teclado activos)"
            return self.state

        capture_ms, frame_rgb = sample
        timestamp_ms = max(capture_ms, self._last_timestamp_ms + 1)
        self._last_timestamp_ms = timestamp_ms

        self.state.frame_rgb = frame_rgb
        self.state.camera_available = True
        self.state.camera_status = ""

        h, w = frame_rgb.shape[:2]
        aspect = w / max(h, 1)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        if self._hand_landmarker is not None:
            hand_result = self._hand_landmarker.detect_for_video(mp_image, timestamp_ms)
            self._process_hands(hand_result, aspect)

        if self._face_landmarker is not None:
            face_result = self._face_landmarker.detect_for_video(mp_image, timestamp_ms)
            self._process_face(face_result, aspect)

        return self.state

    # ------------------------------------------------------------------
    # Procesamiento de manos
    # ------------------------------------------------------------------
    def _process_hands(self, hand_result, aspect: float) -> None:
        landmarks_list = getattr(hand_result, "hand_landmarks", None) or []
        handedness_list = getattr(hand_result, "handedness", None) or []

        if not landmarks_list:
            self.state.dominant_present = False
            self.state.shield_present = False
            self.state.dominant_fingers = 0
            self.state.shield_fingers = 0
            self.state.rapid_fire_active = self._fire_debouncer.update(False)
            self.state.shield_active = self._shield_debouncer.update(False)
            return

        # Construimos lista de manos detectadas con etiqueta y coordenada X
        detected: list[tuple[str, float, list]] = []
        for idx, lms in enumerate(landmarks_list):
            label = "Right"
            if idx < len(handedness_list) and handedness_list[idx]:
                cat = handedness_list[idx][0].category_name
                if cat in ("Left", "Right"):
                    label = cat
            center_x = (lms[0].x + lms[5].x + lms[9].x + lms[17].x) * 0.25
            detected.append((label, center_x, lms))

        # Si aparecen 2 manos con la misma etiqueta, desempatar por lado en espejo
        if len(detected) >= 2 and detected[0][0] == detected[1][0]:
            detected.sort(key=lambda item: item[1])
            detected = [
                ("Left", detected[0][1], detected[0][2]),
                ("Right", detected[1][1], detected[1][2]),
            ]

        dominant_label = "Left" if self.left_handed else "Right"
        secondary_label = "Right" if self.left_handed else "Left"

        dom_lms = None
        sec_lms = None
        for label, _, lms in detected:
            if label == dominant_label and dom_lms is None:
                dom_lms = lms
            elif label == secondary_label and sec_lms is None:
                sec_lms = lms

        # --- Mano Dominante (selección de hechizo 1..4 y disparo rápido 5) ---
        if dom_lms is not None:
            self.state.dominant_present = True
            raw_pos = self._palm_screen_pos(dom_lms)
            self._dom_pos_ema = self._ema_point(self._dom_pos_ema, raw_pos, config.EMA_HAND_POS)
            self.state.dominant_pos = self._dom_pos_ema

            fingers = self._count_extended_fingers(dom_lms, aspect)
            self.state.dominant_fingers = fingers

            if 1 <= fingers <= 4:
                self.state.selected_spell = self._spell_debouncer.update(fingers)
                self.state.rapid_fire_active = self._fire_debouncer.update(False)
            elif fingers == 5:
                self.state.rapid_fire_active = self._fire_debouncer.update(True)
            else:
                self.state.rapid_fire_active = self._fire_debouncer.update(False)
        else:
            self.state.dominant_present = False
            self.state.dominant_fingers = 0
            self.state.rapid_fire_active = self._fire_debouncer.update(False)

        # --- Mano Secundaria (escudo deflector angular) ---
        if sec_lms is not None:
            self.state.shield_present = True
            raw_pos = self._palm_screen_pos(sec_lms)
            self._shield_pos_ema = self._ema_point(self._shield_pos_ema, raw_pos, config.EMA_HAND_POS)
            self.state.shield_pos = self._shield_pos_ema

            fingers = self._count_extended_fingers(sec_lms, aspect)
            self.state.shield_fingers = fingers

            # Histéresis para palma abierta sin parpadeos
            if self.state.shield_active:
                raw_shield_on = fingers >= config.SHIELD_OPEN_FINGERS_HOLD
            else:
                raw_shield_on = fingers >= config.SHIELD_OPEN_FINGERS_ON
            self.state.shield_active = self._shield_debouncer.update(raw_shield_on)

            # Ángulo entre nudillo índice (5) y nudillo meñique (17)
            p5 = sec_lms[5]
            p17 = sec_lms[17]
            dx = (p17.x - p5.x) * config.SCREEN_WIDTH
            dy = (p17.y - p5.y) * config.SCREEN_HEIGHT
            if math.hypot(dx, dy) > 1e-3:
                raw_angle = math.atan2(dy, dx)
                self.state.shield_angle = self._shield_angle_ema.update(raw_angle)
        else:
            self.state.shield_present = False
            self.state.shield_fingers = 0
            self.state.shield_active = self._shield_debouncer.update(False)

    @staticmethod
    def _palm_screen_pos(lms) -> tuple[float, float]:
        nx = (lms[0].x + lms[5].x + lms[9].x + lms[17].x) * 0.25
        ny = (lms[0].y + lms[5].y + lms[9].y + lms[17].y) * 0.25
        x = max(40.0, min(config.SCREEN_WIDTH - 40.0, nx * config.SCREEN_WIDTH))
        y = max(40.0, min(config.SCREEN_HEIGHT - 40.0, ny * config.SCREEN_HEIGHT))
        return (x, y)

    @staticmethod
    def _ema_point(
        prev: tuple[float, float] | None,
        current: tuple[float, float],
        alpha: float,
    ) -> tuple[float, float]:
        if prev is None:
            return current
        return (
            (1.0 - alpha) * prev[0] + alpha * current[0],
            (1.0 - alpha) * prev[1] + alpha * current[1],
        )

    @staticmethod
    def _dist2d(a, b, aspect: float) -> float:
        return math.hypot((a.x - b.x) * aspect, a.y - b.y)

    @classmethod
    def _count_extended_fingers(cls, lms, aspect: float) -> int:
        """Cuenta dedos extendidos usando distancias relativas a la muñeca (invariante a rotación)."""
        wrist = lms[0]
        count = 0

        # Índice (8,6,5), Medio (12,10,9), Anular (16,14,13), Meñique (20,18,17)
        for tip_i, pip_i, mcp_i in ((8, 6, 5), (12, 10, 9), (16, 14, 13), (20, 18, 17)):
            d_tip = cls._dist2d(lms[tip_i], wrist, aspect)
            d_pip = cls._dist2d(lms[pip_i], wrist, aspect)
            d_mcp = cls._dist2d(lms[mcp_i], wrist, aspect)
            if (
                d_pip > 1e-5
                and d_mcp > 1e-5
                and d_tip > d_pip * config.FINGER_TIP_PIP_RATIO
                and d_tip > d_mcp * config.FINGER_TIP_MCP_RATIO
            ):
                count += 1

        # Pulgar (4, 3, 2): relación respecto al nudillo meñique (17) y la muñeca (0)
        palm_scale = cls._dist2d(wrist, lms[9], aspect)
        d_thumb_tip_pinky = cls._dist2d(lms[4], lms[17], aspect)
        d_thumb_ip_pinky = cls._dist2d(lms[3], lms[17], aspect)
        d_thumb_tip_wrist = cls._dist2d(lms[4], wrist, aspect)
        d_thumb_ip_wrist = cls._dist2d(lms[3], wrist, aspect)
        d_thumb_index_mcp = cls._dist2d(lms[4], lms[5], aspect)

        if (
            palm_scale > 1e-5
            and d_thumb_ip_pinky > 1e-5
            and d_thumb_ip_wrist > 1e-5
            and d_thumb_tip_pinky > d_thumb_ip_pinky * config.THUMB_PINKY_RATIO
            and d_thumb_tip_wrist > d_thumb_ip_wrist * config.THUMB_WRIST_RATIO
            and d_thumb_index_mcp > palm_scale * 0.42
        ):
            count += 1

        return count

    # ------------------------------------------------------------------
    # Procesamiento de rostro (boca + inclinación de cabeza)
    # ------------------------------------------------------------------
    def _process_face(self, face_result, aspect: float) -> None:
        faces = getattr(face_result, "face_landmarks", None) or []
        if not faces:
            self.state.face_present = False
            self._mouth_ema *= 0.85
            self.state.mouth_metric = self._mouth_ema
            if self._mouth_ema <= config.MOUTH_CLOSE_THRESHOLD:
                self.state.mouth_open = False
            self._head_roll_ema *= 0.82
            self.state.head_roll_deg = self._head_roll_ema
            self.state.head_move = 0.0
            return

        self.state.face_present = True
        face = faces[0]

        # 1. Blendshape jawOpen
        jaw_open = 0.0
        has_blendshapes = False
        blendshapes = getattr(face_result, "face_blendshapes", None) or []
        if blendshapes:
            for cat in blendshapes[0]:
                if cat.category_name == "jawOpen":
                    jaw_open = float(cat.score)
                    has_blendshapes = True
                    break

        # 2. Relación geométrica de labios (MAR)
        mouth_w = self._dist2d(face[78], face[308], aspect)
        v_center = self._dist2d(face[13], face[14], aspect)
        v_left = self._dist2d(face[82], face[87], aspect)
        v_right = self._dist2d(face[312], face[317], aspect)
        mar = ((v_center + v_left + v_right) / 3.0) / max(mouth_w, 1e-5)
        mar_norm = max(0.0, min(1.0, mar / config.MOUTH_MAR_REFERENCE))

        if has_blendshapes:
            raw_mouth = config.MOUTH_JAW_WEIGHT * jaw_open + config.MOUTH_MAR_WEIGHT * mar_norm
        else:
            raw_mouth = mar_norm

        self._mouth_ema = (1.0 - config.EMA_MOUTH_METRIC) * self._mouth_ema + config.EMA_MOUTH_METRIC * raw_mouth
        self.state.jaw_open = jaw_open
        self.state.mouth_mar = mar
        self.state.mouth_metric = self._mouth_ema

        if not self.state.mouth_open and self._mouth_ema >= config.MOUTH_OPEN_THRESHOLD:
            self.state.mouth_open = True
        elif self.state.mouth_open and self._mouth_ema <= config.MOUTH_CLOSE_THRESHOLD:
            self.state.mouth_open = False

        # 3. Balanceo lateral de cabeza (roll entre comisuras exteriores de ambos ojos)
        eye_a = face[33]
        eye_b = face[263]
        if eye_a.x <= eye_b.x:
            left_eye, right_eye = eye_a, eye_b
        else:
            left_eye, right_eye = eye_b, eye_a

        dx = (right_eye.x - left_eye.x) * aspect
        dy = right_eye.y - left_eye.y
        raw_roll_deg = math.degrees(math.atan2(dy, max(dx, 1e-5)))

        self._head_roll_ema = (1.0 - config.EMA_HEAD_ROLL) * self._head_roll_ema + config.EMA_HEAD_ROLL * raw_roll_deg
        self.state.head_roll_deg = self._head_roll_ema

        abs_roll = abs(self._head_roll_ema)
        if abs_roll <= config.HEAD_ROLL_DEADZONE_DEG:
            self.state.head_move = 0.0
        else:
            span = max(config.HEAD_ROLL_MAX_DEG - config.HEAD_ROLL_DEADZONE_DEG, 1.0)
            mag = min(1.0, (abs_roll - config.HEAD_ROLL_DEADZONE_DEG) / span)
            self.state.head_move = math.copysign(mag, self._head_roll_ema)
