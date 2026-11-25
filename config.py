"""Configuración global de Arcane Vision: Duelo de Magos.

Centraliza resolución lógica, ventana grande/pantalla completa, paleta cromática,
grimorio de 4 hechizos, umbrales biométricos, factores EMA, debounce y tiempos de oleada.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

# ---------------------------------------------------------------------------
# Rutas y modelos oficiales de MediaPipe Tasks
# ---------------------------------------------------------------------------
PROJECT_DIR: Final[Path] = Path(__file__).resolve().parent
MODELS_DIR: Final[Path] = PROJECT_DIR / "models"
HAND_MODEL_PATH: Final[Path] = MODELS_DIR / "hand_landmarker.task"
FACE_MODEL_PATH: Final[Path] = MODELS_DIR / "face_landmarker.task"

HAND_MODEL_URL: Final[str] = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
FACE_MODEL_URL: Final[str] = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)

# ---------------------------------------------------------------------------
# Pantalla, ventana grande y pantalla completa
# ---------------------------------------------------------------------------
SCREEN_WIDTH: Final[int] = 1280
SCREEN_HEIGHT: Final[int] = 720
FPS: Final[int] = 60

# La ventana inicial se abre grande (~86 % del monitor manteniendo 16:9)
WINDOW_SCALE_RATIO: Final[float] = 0.86
MIN_WINDOW_WIDTH: Final[int] = 960
MIN_WINDOW_HEIGHT: Final[int] = 540
WINDOW_TITLE: Final[str] = "Arcane Vision: Duelo de Magos"

# Opacidad del video de cámara en el fondo (0..255)
CAMERA_BG_ALPHA: Final[int] = 68

# Zona de juego recortada dentro del lienzo 1280x720 (la detección de cámara usa el 100%)
ARENA_LEFT: Final[int] = 190
ARENA_RIGHT: Final[int] = SCREEN_WIDTH - 190      # 1090 (ancho jugable: 900 px)
ARENA_TOP: Final[int] = 90
ARENA_BOTTOM: Final[int] = SCREEN_HEIGHT - 52     # 668
ARENA_WIDTH: Final[int] = ARENA_RIGHT - ARENA_LEFT

# Sub-región cómoda de la cámara que se mapea hasta los bordes exactos de la arena
# (MediaPipe sigue detectando fuera de este rango en 0.0..1.0 sin recorte)
HAND_MAP_X_MIN: Final[float] = 0.17
HAND_MAP_X_MAX: Final[float] = 0.83
HAND_MAP_Y_MIN: Final[float] = 0.15
HAND_MAP_Y_MAX: Final[float] = 0.86

# ---------------------------------------------------------------------------
# Paleta cromática arcana (RGB)
# ---------------------------------------------------------------------------
COLOR_BG_DARK: Final[tuple[int, int, int]] = (8, 10, 24)
COLOR_BG_TINT: Final[tuple[int, int, int]] = (14, 18, 40)
COLOR_LETTERBOX: Final[tuple[int, int, int]] = (4, 5, 12)

COLOR_TEXT_MAIN: Final[tuple[int, int, int]] = (240, 244, 255)
COLOR_TEXT_MUTED: Final[tuple[int, int, int]] = (165, 178, 210)
COLOR_TEXT_GOLD: Final[tuple[int, int, int]] = (255, 216, 105)

COLOR_PANEL_BG: Final[tuple[int, int, int, int]] = (12, 16, 36, 195)
COLOR_PANEL_BORDER: Final[tuple[int, int, int]] = (84, 112, 178)

COLOR_HP_HIGH: Final[tuple[int, int, int]] = (64, 232, 145)
COLOR_HP_MID: Final[tuple[int, int, int]] = (255, 196, 68)
COLOR_HP_LOW: Final[tuple[int, int, int]] = (255, 76, 94)

COLOR_SHIELD_PRIMARY: Final[tuple[int, int, int]] = (88, 238, 255)
COLOR_SHIELD_GLOW: Final[tuple[int, int, int]] = (205, 252, 255)
COLOR_SHIELD_OVERHEAT: Final[tuple[int, int, int]] = (255, 86, 68)

COLOR_OVERCHARGE_CORE: Final[tuple[int, int, int]] = (255, 250, 220)
COLOR_OVERCHARGE_AURA: Final[tuple[int, int, int]] = (255, 206, 78)
COLOR_SPECIAL_SCATTER: Final[tuple[int, int, int]] = (82, 245, 218)
COLOR_SPECIAL_HEAVY: Final[tuple[int, int, int]] = (255, 174, 62)
COLOR_LOCK_ACTIVE: Final[tuple[int, int, int]] = (255, 212, 84)

COLOR_ENEMY_ORB: Final[tuple[int, int, int]] = (255, 68, 86)
COLOR_ENEMY_ORB_CORE: Final[tuple[int, int, int]] = (255, 218, 170)
COLOR_REFLECTED_ORB: Final[tuple[int, int, int]] = (108, 255, 232)

COLOR_LASER_WARN: Final[tuple[int, int, int]] = (255, 42, 68)
COLOR_LASER_BEAM: Final[tuple[int, int, int]] = (196, 56, 255)
COLOR_LASER_CORE: Final[tuple[int, int, int]] = (255, 232, 255)

COLOR_MEDITATION: Final[tuple[int, int, int]] = (96, 245, 185)
COLOR_VOID_LORD: Final[tuple[int, int, int]] = (165, 58, 235)
COLOR_WRAITH: Final[tuple[int, int, int]] = (130, 152, 220)
COLOR_PYROMANCER: Final[tuple[int, int, int]] = (255, 108, 62)
COLOR_SWARM: Final[tuple[int, int, int]] = (92, 224, 196)


# ---------------------------------------------------------------------------
# Grimorio: Definición de los 4 hechizos elementales
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class SpellSpec:
    spell_id: int
    name: str
    short_name: str
    color: tuple[int, int, int]
    core_color: tuple[int, int, int]
    speed: float
    damage: float
    cooldown: float
    radius: int
    projectile_count: int
    spread_deg: float
    crit_chance: float
    crit_multiplier: float
    overcharge_damage: float
    overcharge_radius: int
    overcharge_speed: float
    description: str


SPELLS: Final[dict[int, SpellSpec]] = {
    1: SpellSpec(
        spell_id=1,
        name="Rayo Arcano",
        short_name="Arcano",
        color=(72, 188, 255),
        core_color=(220, 246, 255),
        speed=900.0,
        damage=26.0,
        cooldown=0.22,
        radius=9,
        projectile_count=1,
        spread_deg=0.0,
        crit_chance=0.08,
        crit_multiplier=1.5,
        overcharge_damage=130.0,
        overcharge_radius=34,
        overcharge_speed=650.0,
        description="Azul, disparo veloz y preciso.",
    ),
    2: SpellSpec(
        spell_id=2,
        name="Orbe Ígneo",
        short_name="Ígneo",
        color=(255, 132, 42),
        core_color=(255, 236, 165),
        speed=620.0,
        damage=48.0,
        cooldown=0.38,
        radius=15,
        projectile_count=1,
        spread_deg=0.0,
        crit_chance=0.10,
        crit_multiplier=1.5,
        overcharge_damage=170.0,
        overcharge_radius=42,
        overcharge_speed=560.0,
        description="Naranja, gran impacto y daño alto.",
    ),
    3: SpellSpec(
        spell_id=3,
        name="Espinas Esmeralda",
        short_name="Esmeralda",
        color=(56, 234, 138),
        core_color=(215, 255, 228),
        speed=770.0,
        damage=20.0,
        cooldown=0.33,
        radius=8,
        projectile_count=3,
        spread_deg=15.0,
        crit_chance=0.12,
        crit_multiplier=1.5,
        overcharge_damage=145.0,
        overcharge_radius=36,
        overcharge_speed=620.0,
        description="Verde, disparo triple en abanico.",
    ),
    4: SpellSpec(
        spell_id=4,
        name="Tormenta Voltaica",
        short_name="Voltaica",
        color=(188, 96, 255),
        core_color=(244, 218, 255),
        speed=980.0,
        damage=35.0,
        cooldown=0.29,
        radius=11,
        projectile_count=1,
        spread_deg=0.0,
        crit_chance=0.45,
        crit_multiplier=1.85,
        overcharge_damage=185.0,
        overcharge_radius=40,
        overcharge_speed=720.0,
        description="Violeta, velocidad y daño críticos.",
    ),
}

# ---------------------------------------------------------------------------
# Umbrales biométricos, EMA y estabilidad por cuadros (debounce)
# ---------------------------------------------------------------------------
# Conteo de dedos relativo a la muñeca (invariante a rotación)
FINGER_TIP_PIP_RATIO: Final[float] = 1.13
FINGER_TIP_MCP_RATIO: Final[float] = 1.28
THUMB_PINKY_RATIO: Final[float] = 1.15
THUMB_WRIST_RATIO: Final[float] = 1.08

# Apertura bucal (combinación jawOpen blendshape + relación geométrica MAR)
MOUTH_JAW_WEIGHT: Final[float] = 0.62
MOUTH_MAR_WEIGHT: Final[float] = 0.38
MOUTH_MAR_REFERENCE: Final[float] = 0.68
MOUTH_OPEN_THRESHOLD: Final[float] = 0.32
MOUTH_CLOSE_THRESHOLD: Final[float] = 0.21

# Carga y liberación de proyectil especial bucal (requiere barra especial al 100%)
CHARGE_FILL_RATE: Final[float] = 1.05       # Carga bucal completa en ~0.95 s cuando la barra está lista
CHARGE_DECAY_RATE: Final[float] = 1.85      # Decae si se cierra antes del umbral
OVERCHARGE_MIN_CHARGE: Final[float] = 0.38  # Mínimo de canalización bucal para liberar el especial

# Barra de energía del tiro especial (0..100, evita spam)
SPECIAL_ENERGY_MAX: Final[float] = 100.0
SPECIAL_ENERGY_PASSIVE_REGEN: Final[float] = 2.4   # Recarga pasiva lenta por segundo
SPECIAL_ENERGY_PER_HIT: Final[float] = 2.6         # Al impactar enemigos
SPECIAL_ENERGY_PER_KILL: Final[float] = 9.0        # Al derrotar enemigos
SPECIAL_ENERGY_PER_SHIELD_BREAK: Final[float] = 10.0
SPECIAL_ENERGY_PER_REFLECT: Final[float] = 16.0    # Recompensa alta por reflejar con escudo

# Dos tipos de tiro especial bucal:
# 1) "scatter": Nova Dispersa (para enemigos pequeños y dispersos)
SPECIAL_SCATTER_COUNT: Final[int] = 9
SPECIAL_SCATTER_SPREAD_DEG: Final[float] = 112.0
SPECIAL_SCATTER_SPEED: Final[float] = 690.0
SPECIAL_SCATTER_DAMAGE: Final[float] = 58.0
SPECIAL_SCATTER_RADIUS: Final[float] = 13.0
SPECIAL_SCATTER_TURN_RATE: Final[float] = 4.6      # Radianes/s de seguimiento suave

# 2) "heavy": Lanza Titánica (para enemigos grandes / Centinelas / Jefe)
SPECIAL_HEAVY_SPEED: Final[float] = 610.0
SPECIAL_HEAVY_DAMAGE: Final[float] = 260.0
SPECIAL_HEAVY_RADIUS: Final[float] = 44.0

# Bloqueo de tipo de ataque haciendo puño (0 dedos) en la mano dominante
FIST_DEBOUNCE_FRAMES: Final[int] = 5        # Frames estables de puño para alternar candado
FIST_TOGGLE_COOLDOWN: Final[float] = 0.55   # Segundos mínimos entre alternancias de candado
LOCKED_FIRE_MIN_FINGERS: Final[int] = 4     # Con ataque bloqueado, 4-5 dedos disparan sin cambiar hechizo

# Gesto de oración (juntar ambas manos) para intercambiar mano de ataque y escudo
PRAYER_PALM_DIST_RATIO: Final[float] = 1.15   # Distancia máxima entre centros de palmas (en unidades de palma)
PRAYER_WRIST_DIST_RATIO: Final[float] = 1.30  # Distancia máxima entre muñecas
PRAYER_TIP_DIST_RATIO: Final[float] = 1.10    # Distancia máxima entre puntas de dedos (índice o medio)
PRAYER_MIN_ALIGNMENT: Final[float] = 0.25     # Ambas manos orientadas en dirección similar
PRAYER_DEBOUNCE_FRAMES: Final[int] = 8        # Frames estables juntos para confirmar el intercambio
PRAYER_SWAP_COOLDOWN: Final[float] = 1.35     # Enfriamiento mínimo entre intercambios de mano

# Escudo deflector angular (mano secundaria): barra temporal, regeneración lenta y cooldown
SHIELD_OPEN_FINGERS_ON: Final[int] = 5      # Activa con palma abierta completa
SHIELD_OPEN_FINGERS_HOLD: Final[int] = 4    # Histéresis suave para evitar parpadeo
SHIELD_HALF_LENGTH: Final[float] = 88.0
SHIELD_THICKNESS: Final[float] = 15.0
SHIELD_ENERGY_MAX: Final[float] = 100.0
SHIELD_MAX_ACTIVE_SECONDS: Final[float] = 4.0       # ~4 s de uso continuo antes de agotarse
SHIELD_DRAIN_PER_SEC: Final[float] = SHIELD_ENERGY_MAX / SHIELD_MAX_ACTIVE_SECONDS
SHIELD_REGEN_DELAY: Final[float] = 0.45             # Breve pausa al bajar el escudo antes de recuperar
SHIELD_REGEN_PER_SEC: Final[float] = 11.5           # Recuperación lenta (~8.7 s para llenarse)
SHIELD_OVERHEAT_COOLDOWN: Final[float] = 4.5        # Tiempo de enfriamiento obligatorio si se agota toda la barra
SHIELD_POST_COOLDOWN_ENERGY: Final[float] = 35.0    # Energía disponible al terminar el enfriamiento

# Inclinación de cabeza (roll entre ambos ojos) para esquive lateral
HEAD_ROLL_DEADZONE_DEG: Final[float] = 4.0
HEAD_ROLL_MAX_DEG: Final[float] = 20.0

# Factores de suavizado exponencial (EMA): 0 = congelado, 1 = sin suavizado
EMA_HAND_POS: Final[float] = 0.42
EMA_SHIELD_ANGLE: Final[float] = 0.35
EMA_HEAD_ROLL: Final[float] = 0.30
EMA_MOUTH_METRIC: Final[float] = 0.45

# Confirmación por estabilidad de cuadros (debounce)
SPELL_DEBOUNCE_FRAMES: Final[int] = 4
FIRE_PALM_DEBOUNCE_FRAMES: Final[int] = 2
SHIELD_DEBOUNCE_FRAMES: Final[int] = 2

# Asistencia suave de puntería en disparos básicos
AIM_ASSIST_RANGE: Final[float] = 560.0
AIM_ASSIST_MAX_ANGLE_DEG: Final[float] = 18.0
AIM_ASSIST_STRENGTH: Final[float] = 0.50

# ---------------------------------------------------------------------------
# Jugador, oleadas, pausas anti-fatiga y combate
# ---------------------------------------------------------------------------
PLAYER_MAX_HP: Final[float] = 100.0
PLAYER_Y: Final[float] = 648.0
PLAYER_RADIUS: Final[float] = 26.0
PLAYER_MAX_SPEED: Final[float] = 580.0
PLAYER_INVULN_TIME: Final[float] = 0.70

WAVE_DURATION: Final[float] = 35.0
MEDITATION_DURATION: Final[float] = 6.0
MEDITATION_HEAL_PER_SEC: Final[float] = 5.5
BOSS_MIN_WAVE: Final[int] = 5

LASER_WARNING_DURATION: Final[float] = 1.4
LASER_ACTIVE_DURATION: Final[float] = 0.72
LASER_HALF_WIDTH: Final[float] = 28.0
LASER_DAMAGE: Final[float] = 24.0

ENEMY_ORB_DAMAGE: Final[float] = 14.0
ENEMY_BREACH_DAMAGE: Final[float] = 15.0
REFLECTED_ORB_DAMAGE: Final[float] = 75.0
REFLECTED_ORB_SPEED_MULT: Final[float] = 1.45

# Cámara por defecto
DEFAULT_CAMERA_WIDTH: Final[int] = 640
DEFAULT_CAMERA_HEIGHT: Final[int] = 480
