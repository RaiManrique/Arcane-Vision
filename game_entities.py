"""Entidades procedurales/vectoriales de Arcane Vision: Duelo de Magos.

Incluye:
- Avatar del mago (esquive lateral por inclinación de cabeza).
- Proyectiles normales y sobrecargados (perforantes y rompe-escudos).
- Proyectiles enemigos reflejables mediante el escudo deflector angular.
- Rayos láser verticales telegrafiados (1.4 s de advertencia roja).
- Sistema de partículas, ondas de choque y textos flotantes.
- Los 5 arquetipos de enemigos:
  1. Espectro Errante
  2. Centinela Rúnico (escudo elemental con número 1..4)
  3. Invocador Ígneo (dispara orbes rojos reflejables)
  4. Enjambre Etéreo (grupos rápidos en zigzag)
  5. Señor del Vacío (Jefe, Oleada 5+: escudo elemental, ráfagas triples y láseres)
"""

from __future__ import annotations

import itertools
import math
import random
from dataclasses import dataclass, field

import pygame

import config

_ENTITY_ID_SEQ = itertools.count(1)


# ---------------------------------------------------------------------------
# Utilidades de dibujo procedural y geometría
# ---------------------------------------------------------------------------
def draw_glow_circle(
    surface: pygame.Surface,
    color: tuple[int, int, int],
    center: tuple[float, float],
    radius: float,
    core_color: tuple[int, int, int] | None = None,
    glow_layers: int = 3,
) -> None:
    """Dibuja un círculo energético con halo semitransparente procedural."""
    r = max(2, int(round(radius)))
    pad = r * 2 + 10
    glow_surf = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
    cx = cy = pad

    for i in range(glow_layers, 0, -1):
        layer_r = int(r * (1.0 + 0.42 * i))
        alpha = max(18, int(86 / (i + 0.4)))
        pygame.draw.circle(glow_surf, (*color, alpha), (cx, cy), layer_r)

    pygame.draw.circle(glow_surf, (*color, 235), (cx, cy), r)
    if core_color is not None and r >= 4:
        pygame.draw.circle(glow_surf, (*core_color, 255), (cx, cy), max(2, int(r * 0.52)))

    surface.blit(glow_surf, (int(center[0] - pad), int(center[1] - pad)))


def draw_runic_circle(
    surface: pygame.Surface,
    center: tuple[float, float],
    radius: float,
    color: tuple[int, int, int],
    angle: float,
    charge: float = 0.0,
    sides: int = 6,
    alpha: int = 210,
) -> None:
    """Dibuja un círculo mágico con anillos, polígonos inscritos y runas."""
    r = max(16, int(round(radius)))
    pad = r + 18
    tmp = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
    cx = cy = pad

    # Halo suave proporcional a la carga
    aura_alpha = int(min(130, 32 + charge * 95))
    pygame.draw.circle(tmp, (*color, aura_alpha), (cx, cy), int(r * (1.06 + 0.14 * charge)))
    pygame.draw.circle(tmp, (*color, min(255, alpha)), (cx, cy), r, width=2)
    pygame.draw.circle(tmp, (*color, min(255, int(alpha * 0.75))), (cx, cy), max(6, int(r * 0.78)), width=2)

    # Dos polígonos rúnicos contrarrotatorios
    for direction, scale in ((1.0, 0.94), (-1.35, 0.74)):
        pts = []
        rot = angle * direction
        for i in range(sides):
            a = rot + (2.0 * math.pi * i / sides)
            pts.append((cx + math.cos(a) * r * scale, cy + math.sin(a) * r * scale))
        pygame.draw.polygon(tmp, (*color, min(255, int(alpha * 0.85))), pts, width=2)

    # Marcas rúnicas en el borde
    ticks = sides * 2
    for i in range(ticks):
        a = angle * 0.6 + (2.0 * math.pi * i / ticks)
        x0 = cx + math.cos(a) * (r * 0.80)
        y0 = cy + math.sin(a) * (r * 0.80)
        x1 = cx + math.cos(a) * (r * 0.98)
        y1 = cy + math.sin(a) * (r * 0.98)
        pygame.draw.line(tmp, (*color, alpha), (x0, y0), (x1, y1), 2)

    # Núcleo dorado cuando la carga supera el umbral de sobrecarga
    if charge > 0.02:
        inner_r = max(4, int(r * 0.45 * charge))
        core_col = config.COLOR_OVERCHARGE_AURA if charge >= config.OVERCHARGE_MIN_CHARGE else color
        pygame.draw.circle(tmp, (*core_col, min(230, int(90 + charge * 140))), (cx, cy), inner_r)
        if charge >= config.OVERCHARGE_MIN_CHARGE:
            pygame.draw.circle(tmp, (*config.COLOR_OVERCHARGE_CORE, 240), (cx, cy), max(3, int(inner_r * 0.55)))

    surface.blit(tmp, (int(center[0] - pad), int(center[1] - pad)))


def draw_padlock_icon(
    surface: pygame.Surface,
    center: tuple[float, float],
    locked: bool,
    color: tuple[int, int, int],
    scale: float = 1.0,
) -> None:
    """Dibuja un ícono vectorial nítido de candado (cerrado o abierto)."""
    cx, cy = int(center[0]), int(center[1])
    bw = max(8, int(14 * scale))
    bh = max(7, int(11 * scale))
    shackle_r = max(4, int(5 * scale))

    # Arco superior del candado
    arc_rect = pygame.Rect(cx - shackle_r, cy - bh // 2 - shackle_r - 1, shackle_r * 2, shackle_r * 2 + 2)
    if locked:
        pygame.draw.arc(surface, color, arc_rect, 0.0, math.pi, max(2, int(2 * scale)))
        pygame.draw.line(surface, color, (arc_rect.left, cy - bh // 2 + 1), (arc_rect.left, arc_rect.centery), max(2, int(2 * scale)))
        pygame.draw.line(surface, color, (arc_rect.right - 1, cy - bh // 2 + 1), (arc_rect.right - 1, arc_rect.centery), max(2, int(2 * scale)))
    else:
        open_rect = arc_rect.move(int(3 * scale), -int(2 * scale))
        pygame.draw.arc(surface, color, open_rect, 0.0, math.pi, max(2, int(2 * scale)))
        pygame.draw.line(surface, color, (open_rect.right - 1, cy - bh // 2 + 1), (open_rect.right - 1, open_rect.centery), max(2, int(2 * scale)))

    # Cuerpo del candado
    body_rect = pygame.Rect(cx - bw // 2, cy - bh // 2 + 2, bw, bh)
    pygame.draw.rect(surface, color if locked else (48, 56, 86), body_rect, border_radius=3)
    pygame.draw.rect(surface, color, body_rect, width=2, border_radius=3)
    # Cerradura interior
    pygame.draw.circle(surface, (10, 12, 24) if locked else color, (cx, body_rect.centery), max(2, int(2 * scale)))


def segment_circle_collision(
    p1: tuple[float, float],
    p2: tuple[float, float],
    center: tuple[float, float],
    radius: float,
) -> tuple[bool, tuple[float, float]]:
    """Comprueba colisión entre segmento [p1, p2] y círculo; retorna (hit, normal_unitaria)."""
    sx = p2[0] - p1[0]
    sy = p2[1] - p1[1]
    seg_len_sq = sx * sx + sy * sy
    if seg_len_sq < 1e-6:
        dx = center[0] - p1[0]
        dy = center[1] - p1[1]
        d = math.hypot(dx, dy)
        if d <= radius and d > 1e-6:
            return True, (dx / d, dy / d)
        return False, (0.0, -1.0)

    t = ((center[0] - p1[0]) * sx + (center[1] - p1[1]) * sy) / seg_len_sq
    t = max(0.0, min(1.0, t))
    closest_x = p1[0] + t * sx
    closest_y = p1[1] + t * sy
    dx = center[0] - closest_x
    dy = center[1] - closest_y
    dist = math.hypot(dx, dy)
    if dist <= radius:
        if dist > 1e-6:
            return True, (dx / dist, dy / dist)
        seg_len = math.sqrt(seg_len_sq)
        return True, (-sy / seg_len, sx / seg_len)
    return False, (0.0, -1.0)


# ---------------------------------------------------------------------------
# Sistema de partículas, ondas de choque y textos flotantes
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: tuple[int, int, int]
    radius: float
    life: float
    max_life: float
    drag: float = 0.96

    def update(self, dt: float) -> bool:
        self.life -= dt
        if self.life <= 0.0:
            return False
        self.x += self.vx * dt
        self.y += self.vy * dt
        factor = self.drag ** (dt * 60.0)
        self.vx *= factor
        self.vy *= factor
        return True

    def draw(self, surface: pygame.Surface) -> None:
        ratio = max(0.0, self.life / self.max_life)
        r = max(1, int(round(self.radius * ratio)))
        col = (
            min(255, int(self.color[0] * (0.4 + 0.6 * ratio))),
            min(255, int(self.color[1] * (0.4 + 0.6 * ratio))),
            min(255, int(self.color[2] * (0.4 + 0.6 * ratio))),
        )
        pygame.draw.circle(surface, col, (int(self.x), int(self.y)), r)


@dataclass(slots=True)
class ShockwaveRing:
    x: float
    y: float
    color: tuple[int, int, int]
    radius: float
    max_radius: float
    life: float
    max_life: float
    width: int = 4

    def update(self, dt: float) -> bool:
        self.life -= dt
        if self.life <= 0.0:
            return False
        progress = 1.0 - (self.life / self.max_life)
        self.radius = 8.0 + (self.max_radius - 8.0) * (1.0 - (1.0 - progress) ** 2)
        return True

    def draw(self, surface: pygame.Surface) -> None:
        ratio = max(0.0, self.life / self.max_life)
        r = max(4, int(self.radius))
        pad = r + self.width + 4
        tmp = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
        alpha = int(220 * ratio)
        pygame.draw.circle(tmp, (*self.color, alpha), (pad, pad), r, width=max(1, int(self.width * ratio)))
        surface.blit(tmp, (int(self.x - pad), int(self.y - pad)))


class ParticleSystem:
    """Administra partículas, estelas y ondas expansivas."""

    def __init__(self) -> None:
        self.particles: list[Particle] = []
        self.rings: list[ShockwaveRing] = []

    def emit_burst(
        self,
        x: float,
        y: float,
        color: tuple[int, int, int],
        count: int = 16,
        speed_range: tuple[float, float] = (60.0, 260.0),
        radius_range: tuple[float, float] = (2.5, 6.0),
        life_range: tuple[float, float] = (0.25, 0.65),
    ) -> None:
        for _ in range(count):
            ang = random.uniform(0.0, math.tau)
            spd = random.uniform(*speed_range)
            life = random.uniform(*life_range)
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(ang) * spd,
                    vy=math.sin(ang) * spd,
                    color=color,
                    radius=random.uniform(*radius_range),
                    life=life,
                    max_life=life,
                )
            )
        # Límite de seguridad para mantener 60 FPS fluidos
        if len(self.particles) > 650:
            self.particles = self.particles[-650:]

    def emit_trail(
        self,
        x: float,
        y: float,
        color: tuple[int, int, int],
        radius: float = 4.0,
        life: float = 0.22,
    ) -> None:
        self.particles.append(
            Particle(
                x=x + random.uniform(-3.0, 3.0),
                y=y + random.uniform(-3.0, 3.0),
                vx=random.uniform(-24.0, 24.0),
                vy=random.uniform(-24.0, 24.0),
                color=color,
                radius=radius,
                life=life,
                max_life=life,
                drag=0.92,
            )
        )

    def emit_ring(
        self,
        x: float,
        y: float,
        color: tuple[int, int, int],
        max_radius: float = 75.0,
        duration: float = 0.35,
        width: int = 4,
    ) -> None:
        self.rings.append(
            ShockwaveRing(
                x=x,
                y=y,
                color=color,
                radius=10.0,
                max_radius=max_radius,
                life=duration,
                max_life=duration,
                width=width,
            )
        )

    def update(self, dt: float) -> None:
        self.particles = [p for p in self.particles if p.update(dt)]
        self.rings = [r for r in self.rings if r.update(dt)]

    def draw(self, surface: pygame.Surface) -> None:
        for ring in self.rings:
            ring.draw(surface)
        for p in self.particles:
            p.draw(surface)

    def clear(self) -> None:
        self.particles.clear()
        self.rings.clear()


@dataclass(slots=True)
class FloatingText:
    text: str
    x: float
    y: float
    color: tuple[int, int, int]
    life: float = 0.85
    max_life: float = 0.85
    vy: float = -58.0
    scale: str = "normal"

    def update(self, dt: float) -> bool:
        self.life -= dt
        self.y += self.vy * dt
        self.vy *= 0.96 ** (dt * 60.0)
        return self.life > 0.0

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        alpha = max(0, min(255, int(255 * (self.life / self.max_life))))
        shadow = font.render(self.text, True, (6, 8, 16))
        glyph = font.render(self.text, True, self.color)
        shadow.set_alpha(alpha)
        glyph.set_alpha(alpha)
        rect = glyph.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(shadow, rect.move(2, 2))
        surface.blit(glyph, rect)


# ---------------------------------------------------------------------------
# Avatar del mago (controlado por inclinación de cabeza)
# ---------------------------------------------------------------------------
class WizardAvatar:
    """Representación vectorial del mago en la franja inferior."""

    def __init__(self) -> None:
        self.x: float = config.SCREEN_WIDTH * 0.5
        self.y: float = config.PLAYER_Y
        self.radius: float = config.PLAYER_RADIUS
        self.hp: float = config.PLAYER_MAX_HP
        self.max_hp: float = config.PLAYER_MAX_HP
        self.invuln_timer: float = 0.0
        self.hit_flash: float = 0.0
        self.lean: float = 0.0
        self.anim_time: float = 0.0

    def reset(self) -> None:
        self.x = config.SCREEN_WIDTH * 0.5
        self.hp = self.max_hp
        self.invuln_timer = 0.0
        self.hit_flash = 0.0
        self.lean = 0.0

    def update(self, move_input: float, dt: float) -> None:
        self.anim_time += dt
        self.invuln_timer = max(0.0, self.invuln_timer - dt)
        self.hit_flash = max(0.0, self.hit_flash - dt)
        move_clamped = max(-1.0, min(1.0, move_input))
        self.x += move_clamped * config.PLAYER_MAX_SPEED * dt
        self.x = max(config.ARENA_LEFT + 34.0, min(config.ARENA_RIGHT - 34.0, self.x))
        self.lean += (move_clamped - self.lean) * min(1.0, dt * 12.0)

    def take_damage(self, amount: float) -> bool:
        if self.invuln_timer > 0.0 or self.hp <= 0.0:
            return False
        self.hp = max(0.0, self.hp - amount)
        self.invuln_timer = config.PLAYER_INVULN_TIME
        self.hit_flash = 0.25
        return True

    def heal(self, amount: float) -> None:
        self.hp = min(self.max_hp, self.hp + amount)

    def draw(
        self,
        surface: pygame.Surface,
        spell_color: tuple[int, int, int],
        meditating: bool = False,
    ) -> None:
        if self.invuln_timer > 0.0 and int(self.invuln_timer * 18) % 2 == 0:
            return

        cx, cy = self.x, self.y
        lean_px = self.lean * 12.0

        # Aura de meditación o círculo base del mago
        aura_color = config.COLOR_MEDITATION if meditating else spell_color
        pulse = 1.0 + 0.08 * math.sin(self.anim_time * 5.0)
        draw_runic_circle(
            surface,
            (cx, cy + 12),
            34.0 * pulse,
            aura_color,
            self.anim_time * (1.8 if meditating else 1.1),
            charge=0.55 if meditating else 0.12,
            sides=6,
            alpha=155,
        )

        # Capa y túnica del mago
        cloak_color = (255, 110, 110) if self.hit_flash > 0 else (38, 46, 98)
        trim_color = config.COLOR_MEDITATION if meditating else spell_color
        cloak_pts = [
            (cx - 24, cy + 28),
            (cx - 14 + lean_px * 0.4, cy - 4),
            (cx + 14 + lean_px * 0.4, cy - 4),
            (cx + 24, cy + 28),
        ]
        pygame.draw.polygon(surface, cloak_color, cloak_pts)
        pygame.draw.polygon(surface, trim_color, cloak_pts, width=2)

        # Cabeza / rostro brillante
        head_x = cx + lean_px * 0.65
        head_y = cy - 11
        pygame.draw.circle(surface, (28, 24, 52), (int(head_x), int(head_y)), 12)
        # Ojos arcanos luminosos
        pygame.draw.circle(surface, trim_color, (int(head_x - 4), int(head_y - 1)), 2)
        pygame.draw.circle(surface, trim_color, (int(head_x + 4), int(head_y - 1)), 2)

        # Sombrero puntiagudo de mago
        brim = [
            (head_x - 22, head_y - 8),
            (head_x + 22, head_y - 8),
            (head_x + 14, head_y - 13),
            (head_x - 14, head_y - 13),
        ]
        tip = [
            (head_x - 13, head_y - 11),
            (head_x + 13, head_y - 11),
            (head_x + lean_px * 0.85, head_y - 40),
        ]
        pygame.draw.polygon(surface, (28, 34, 78), brim)
        pygame.draw.polygon(surface, (34, 42, 96), tip)
        pygame.draw.polygon(surface, trim_color, tip, width=2)
        pygame.draw.line(surface, config.COLOR_TEXT_GOLD, (head_x - 13, head_y - 11), (head_x + 13, head_y - 11), 3)

        # Báculo mágico a un costado
        staff_x = cx + 22 + lean_px * 0.3
        pygame.draw.line(surface, (165, 130, 92), (staff_x, cy + 26), (staff_x + 4, cy - 22), 3)
        draw_glow_circle(surface, trim_color, (staff_x + 4, cy - 26), 5.5, config.COLOR_TEXT_MAIN, glow_layers=2)


# ---------------------------------------------------------------------------
# Escudo Deflector Angular (Mano Secundaria con barra temporal y enfriamiento)
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class AngularShield:
    x: float = config.SCREEN_WIDTH * 0.35
    y: float = config.SCREEN_HEIGHT * 0.60
    angle: float = 0.0
    half_length: float = config.SHIELD_HALF_LENGTH
    thickness: float = config.SHIELD_THICKNESS
    active: bool = False
    flash_timer: float = 0.0
    anim_time: float = 0.0

    # Barra de uso temporal, regeneración lenta y enfriamiento por agotamiento
    energy: float = config.SHIELD_ENERGY_MAX
    max_energy: float = config.SHIELD_ENERGY_MAX
    overheated: bool = False
    cooldown_timer: float = 0.0
    regen_delay_timer: float = 0.0

    def reset(self) -> None:
        self.active = False
        self.flash_timer = 0.0
        self.energy = self.max_energy
        self.overheated = False
        self.cooldown_timer = 0.0
        self.regen_delay_timer = 0.0

    def restore_during_meditation(self, dt: float) -> None:
        """Enfría y recarga el escudo cómodamente durante la Meditación Arcana."""
        if self.overheated:
            self.cooldown_timer = max(0.0, self.cooldown_timer - dt * 2.0)
            if self.cooldown_timer <= 0.0:
                self.overheated = False
                self.energy = max(self.energy, config.SHIELD_POST_COOLDOWN_ENERGY)
        else:
            self.energy = min(self.max_energy, self.energy + config.SHIELD_REGEN_PER_SEC * 2.4 * dt)

    @property
    def energy_ratio(self) -> float:
        return max(0.0, min(1.0, self.energy / max(self.max_energy, 1.0)))

    @property
    def cooldown_ratio(self) -> float:
        return max(0.0, min(1.0, self.cooldown_timer / max(config.SHIELD_OVERHEAT_COOLDOWN, 1e-4)))

    def endpoints(self) -> tuple[tuple[float, float], tuple[float, float]]:
        dx = math.cos(self.angle) * self.half_length
        dy = math.sin(self.angle) * self.half_length
        return ((self.x - dx, self.y - dy), (self.x + dx, self.y + dy))

    def update(
        self,
        want_active: bool,
        pos: tuple[float, float],
        angle: float,
        dt: float,
        allow_drain: bool = True,
    ) -> str | None:
        """Actualiza escudo, energía por tiempo, regeneración lenta y cooldown.

        Retorna 'overheated' si se agotó toda la barra, 'cooled_down' al terminar
        el enfriamiento, o None.
        """
        self.x, self.y = pos
        self.angle = angle
        self.anim_time += dt
        self.flash_timer = max(0.0, self.flash_timer - dt)

        # Estado de enfriamiento obligatorio (cooldown) tras agotar la barra
        if self.overheated:
            self.active = False
            self.cooldown_timer = max(0.0, self.cooldown_timer - dt)
            if self.cooldown_timer <= 0.0:
                self.overheated = False
                self.energy = config.SHIELD_POST_COOLDOWN_ENERGY
                self.regen_delay_timer = 0.0
                return "cooled_down"
            return None

        # Escudo levantado: consume barra proporcionalmente al tiempo
        if want_active and self.energy > 0.0:
            self.active = True
            self.regen_delay_timer = config.SHIELD_REGEN_DELAY
            if allow_drain:
                self.energy = max(0.0, self.energy - config.SHIELD_DRAIN_PER_SEC * dt)
                if self.energy <= 0.0:
                    self.active = False
                    self.overheated = True
                    self.cooldown_timer = config.SHIELD_OVERHEAT_COOLDOWN
                    return "overheated"
            return None

        # Escudo en reposo: se restablece lentamente conforme no se usa
        self.active = False
        if self.regen_delay_timer > 0.0:
            self.regen_delay_timer = max(0.0, self.regen_delay_timer - dt)
        else:
            self.energy = min(self.max_energy, self.energy + config.SHIELD_REGEN_PER_SEC * dt)
        return None

    def trigger_flash(self) -> None:
        self.flash_timer = 0.22

    def draw(self, surface: pygame.Surface) -> None:
        if not self.active:
            return

        low_energy = self.energy_ratio < 0.28
        if self.flash_timer > 0.0:
            col = config.COLOR_TEXT_GOLD
            core = config.COLOR_OVERCHARGE_CORE
        elif low_energy and int(self.anim_time * 16) % 2 == 0:
            col = config.COLOR_SHIELD_OVERHEAT
            core = config.COLOR_HP_MID
        else:
            col = config.COLOR_SHIELD_PRIMARY
            core = config.COLOR_SHIELD_GLOW

        # Halo energético semitransparente
        pad = int(self.half_length + 34)
        tmp = pygame.Surface((pad * 2, pad * 2), pygame.SRCALPHA)
        cx = cy = pad
        dx = math.cos(self.angle) * self.half_length
        dy = math.sin(self.angle) * self.half_length
        lp1 = (cx - dx, cy - dy)
        lp2 = (cx + dx, cy + dy)

        pygame.draw.line(tmp, (*col, 58), lp1, lp2, int(self.thickness * 2.1))
        pygame.draw.line(tmp, (*col, 155), lp1, lp2, int(self.thickness * 1.15))
        pygame.draw.line(tmp, (*core, 245), lp1, lp2, 5)

        # Nodos rúnicos en los extremos
        for pt in (lp1, lp2):
            pygame.draw.circle(tmp, (*col, 220), (int(pt[0]), int(pt[1])), 8)
            pygame.draw.circle(tmp, (*core, 255), (int(pt[0]), int(pt[1])), 4)

        # Indicador sutil de normal hacia arriba para ayudar a apuntar rebotes
        nx, ny = -math.sin(self.angle), math.cos(self.angle)
        if ny > 0:
            nx, ny = -nx, -ny
        tip = (cx + nx * 24, cy + ny * 24)
        pygame.draw.line(tmp, (*core, 175), (cx, cy), tip, 2)
        pygame.draw.circle(tmp, (*core, 210), (int(tip[0]), int(tip[1])), 3)

        surface.blit(tmp, (int(self.x - pad), int(self.y - pad)))

        # Mini barra de durabilidad justo bajo el escudo para lectura periférica
        bw, bh = 86, 6
        bx, by = int(self.x - bw // 2), int(self.y + 18)
        pygame.draw.rect(surface, (16, 20, 36), (bx, by, bw, bh), border_radius=3)
        bar_col = config.COLOR_SHIELD_OVERHEAT if low_energy else config.COLOR_SHIELD_PRIMARY
        pygame.draw.rect(surface, bar_col, (bx, by, int(bw * self.energy_ratio), bh), border_radius=3)


# ---------------------------------------------------------------------------
# Proyectiles (Jugador y Enemigos)
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class PlayerProjectile:
    x: float
    y: float
    vx: float
    vy: float
    spell_id: int
    damage: float
    radius: float
    color: tuple[int, int, int]
    core_color: tuple[int, int, int]
    overcharged: bool = False
    is_crit: bool = False
    special_kind: str = ""          # "" normal | "scatter" Nova Dispersa | "heavy" Lanza Titánica
    piercing: bool = False
    homing_turn_rate: float = 0.0
    target_enemy_id: int | None = None
    anim_time: float = 0.0
    hit_enemy_ids: set[int] = field(default_factory=set)

    def _steer_towards_target(self, dt: float, enemies: list[Enemy]) -> None:
        if self.homing_turn_rate <= 0.0 or not enemies:
            return
        target = None
        if self.target_enemy_id is not None:
            for e in enemies:
                if e.alive and e.entity_id == self.target_enemy_id and e.entity_id not in self.hit_enemy_ids:
                    target = e
                    break
        if target is None:
            best_d = 680.0
            for e in enemies:
                if not e.alive or e.entity_id in self.hit_enemy_ids:
                    continue
                d = math.hypot(e.x - self.x, e.y - self.y)
                if d < best_d:
                    best_d = d
                    target = e
            self.target_enemy_id = target.entity_id if target is not None else None

        if target is None:
            return
        speed = max(math.hypot(self.vx, self.vy), 1e-4)
        cur_ang = math.atan2(self.vy, self.vx)
        des_ang = math.atan2(target.y - self.y, target.x - self.x)
        diff = (des_ang - cur_ang + math.pi) % math.tau - math.pi
        max_step = self.homing_turn_rate * dt
        new_ang = cur_ang + max(-max_step, min(max_step, diff))
        self.vx = math.cos(new_ang) * speed
        self.vy = math.sin(new_ang) * speed

    def update(self, dt: float, particles: ParticleSystem, enemies: list[Enemy] | None = None) -> bool:
        self.anim_time += dt
        if self.homing_turn_rate > 0.0 and enemies:
            self._steer_towards_target(dt, enemies)
        self.x += self.vx * dt
        self.y += self.vy * dt

        if self.special_kind == "heavy" or (self.overcharged and self.special_kind != "scatter"):
            particles.emit_trail(self.x, self.y, config.COLOR_SPECIAL_HEAVY, radius=9.0, life=0.30)
            if random.random() < 0.75:
                particles.emit_trail(self.x, self.y, self.color, radius=6.5, life=0.22)
        elif self.special_kind == "scatter":
            particles.emit_trail(self.x, self.y, config.COLOR_SPECIAL_SCATTER, radius=5.0, life=0.22)
            if random.random() < 0.45:
                particles.emit_trail(self.x, self.y, config.COLOR_OVERCHARGE_CORE, radius=3.0, life=0.16)
        elif random.random() < 0.45:
            particles.emit_trail(self.x, self.y, self.color, radius=max(2.5, self.radius * 0.36), life=0.16)

        margin = self.radius + 70
        return (
            -margin <= self.x <= config.SCREEN_WIDTH + margin
            and -margin <= self.y <= config.SCREEN_HEIGHT + margin
        )

    def draw(self, surface: pygame.Surface) -> None:
        if self.special_kind == "scatter":
            # Nova Dispersa: cometa estelar buscador para enemigos pequeños dispersos
            ang = math.atan2(self.vy, self.vx)
            tail = (self.x - math.cos(ang) * 24, self.y - math.sin(ang) * 24)
            pygame.draw.line(surface, config.COLOR_SPECIAL_SCATTER, tail, (self.x, self.y), 6)
            pygame.draw.line(surface, config.COLOR_OVERCHARGE_CORE, tail, (self.x, self.y), 2)
            draw_glow_circle(surface, config.COLOR_SPECIAL_SCATTER, (self.x, self.y), self.radius * 0.9, config.COLOR_OVERCHARGE_CORE, 2)
            # Destello en cruz de 4 puntas rotando
            r_star = self.radius * 1.45
            for i in range(4):
                a = self.anim_time * 9.0 + i * (math.pi * 0.5)
                pt = (self.x + math.cos(a) * r_star, self.y + math.sin(a) * r_star)
                pygame.draw.line(surface, config.COLOR_OVERCHARGE_CORE, (self.x, self.y), pt, 2)
            return

        if self.overcharged or self.special_kind == "heavy":
            # Lanza Titánica: singularidad perforante masiva para enemigos grandes / jefe
            draw_runic_circle(
                surface,
                (self.x, self.y),
                self.radius * 1.28,
                config.COLOR_SPECIAL_HEAVY,
                self.anim_time * 8.0,
                charge=1.0,
                sides=6,
                alpha=240,
            )
            draw_runic_circle(
                surface,
                (self.x, self.y),
                self.radius * 0.92,
                self.color,
                -self.anim_time * 10.5,
                charge=0.8,
                sides=4,
                alpha=225,
            )
            draw_glow_circle(
                surface,
                config.COLOR_SPECIAL_HEAVY,
                (self.x, self.y),
                self.radius * 0.72,
                config.COLOR_OVERCHARGE_CORE,
                glow_layers=3,
            )
            return

        if self.spell_id == 1:
            # Rayo Arcano: lanza estilizada
            ang = math.atan2(self.vy, self.vx)
            tail = (self.x - math.cos(ang) * 26, self.y - math.sin(ang) * 26)
            pygame.draw.line(surface, self.color, tail, (self.x, self.y), 7)
            pygame.draw.line(surface, self.core_color, tail, (self.x, self.y), 3)
            draw_glow_circle(surface, self.color, (self.x, self.y), self.radius * 0.85, self.core_color, 2)
        elif self.spell_id == 2:
            # Orbe Ígneo: bola de fuego pulsante
            pulse = self.radius * (1.0 + 0.12 * math.sin(self.anim_time * 24.0))
            draw_glow_circle(surface, self.color, (self.x, self.y), pulse, self.core_color, 3)
        elif self.spell_id == 3:
            # Espinas Esmeralda: cristal romboidal orientado
            ang = math.atan2(self.vy, self.vx)
            ca, sa = math.cos(ang), math.sin(ang)
            nx, ny = -sa, ca
            pts = [
                (self.x + ca * 18, self.y + sa * 18),
                (self.x + nx * 7, self.y + ny * 7),
                (self.x - ca * 14, self.y - sa * 14),
                (self.x - nx * 7, self.y - ny * 7),
            ]
            pygame.draw.polygon(surface, self.color, pts)
            pygame.draw.polygon(surface, self.core_color, pts, width=2)
        else:
            # Tormenta Voltaica: orbe violeta con arcos eléctricos
            draw_glow_circle(surface, self.color, (self.x, self.y), self.radius, self.core_color, 2)
            for i in range(3):
                a = self.anim_time * 16.0 + i * (math.tau / 3.0)
                mid = (
                    self.x + math.cos(a) * (self.radius + 7),
                    self.y + math.sin(a) * (self.radius + 7),
                )
                end = (
                    self.x + math.cos(a + 0.45) * (self.radius + 13),
                    self.y + math.sin(a + 0.45) * (self.radius + 13),
                )
                pygame.draw.lines(surface, self.core_color, False, [(self.x, self.y), mid, end], 2)


@dataclass(slots=True)
class EnemyProjectile:
    x: float
    y: float
    vx: float
    vy: float
    radius: float = 11.0
    damage: float = config.ENEMY_ORB_DAMAGE
    reflected: bool = False
    anim_time: float = 0.0

    def reflect(
        self,
        normal: tuple[float, float],
        enemies: list[Enemy],
    ) -> None:
        """Refleja físicamente el orbe usando la normal del escudo angular."""
        nx, ny = normal
        dot = self.vx * nx + self.vy * ny
        # Si el vector de velocidad ya iba en dirección de la normal, invertir la normal
        if dot > 0:
            nx, ny = -nx, -ny
            dot = -dot

        rx = self.vx - 2.0 * dot * nx
        ry = self.vy - 2.0 * dot * ny
        speed = math.hypot(rx, ry) * config.REFLECTED_ORB_SPEED_MULT
        speed = max(560.0, min(920.0, speed))
        r_len = max(math.hypot(rx, ry), 1e-5)
        rx /= r_len
        ry /= r_len

        # Asistencia suave hacia un enemigo dentro del cono reflejado para mayor satisfacción
        best_dir = None
        best_dot = 0.72
        for enemy in enemies:
            if not enemy.alive:
                continue
            ex = enemy.x - self.x
            ey = enemy.y - self.y
            ed = math.hypot(ex, ey)
            if ed < 1e-5:
                continue
            ux, uy = ex / ed, ey / ed
            alignment = rx * ux + ry * uy
            if alignment > best_dot:
                best_dot = alignment
                best_dir = (ux, uy)

        if best_dir is not None:
            rx = rx * 0.55 + best_dir[0] * 0.45
            ry = ry * 0.55 + best_dir[1] * 0.45
            norm = max(math.hypot(rx, ry), 1e-5)
            rx /= norm
            ry /= norm

        self.vx = rx * speed
        self.vy = ry * speed
        self.x += rx * 16.0
        self.y += ry * 16.0
        self.reflected = True
        self.damage = config.REFLECTED_ORB_DAMAGE

    def update(self, dt: float, particles: ParticleSystem) -> bool:
        self.anim_time += dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        trail_col = config.COLOR_REFLECTED_ORB if self.reflected else config.COLOR_ENEMY_ORB
        if random.random() < 0.5:
            particles.emit_trail(self.x, self.y, trail_col, radius=4.5, life=0.18)
        margin = 50.0
        return (
            -margin <= self.x <= config.SCREEN_WIDTH + margin
            and -margin <= self.y <= config.SCREEN_HEIGHT + margin
        )

    def draw(self, surface: pygame.Surface) -> None:
        if self.reflected:
            draw_glow_circle(
                surface,
                config.COLOR_REFLECTED_ORB,
                (self.x, self.y),
                self.radius * 1.15,
                config.COLOR_OVERCHARGE_CORE,
                glow_layers=3,
            )
        else:
            pulse = self.radius * (1.0 + 0.14 * math.sin(self.anim_time * 18.0))
            draw_glow_circle(
                surface,
                config.COLOR_ENEMY_ORB,
                (self.x, self.y),
                pulse,
                config.COLOR_ENEMY_ORB_CORE,
                glow_layers=3,
            )


# ---------------------------------------------------------------------------
# Rayo láser vertical telegrafiado (Señor del Vacío)
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class VoidLaser:
    x: float
    origin_y: float
    warning_timer: float = config.LASER_WARNING_DURATION
    active_timer: float = config.LASER_ACTIVE_DURATION
    half_width: float = config.LASER_HALF_WIDTH
    has_fired_sound: bool = False
    has_dealt_damage: bool = False
    anim_time: float = 0.0

    @property
    def is_active(self) -> bool:
        return self.warning_timer <= 0.0 and self.active_timer > 0.0

    def update(self, dt: float) -> tuple[bool, bool]:
        """Retorna (sigue_vivo, acaba_de_disparar)."""
        self.anim_time += dt
        just_fired = False
        if self.warning_timer > 0.0:
            self.warning_timer -= dt
            if self.warning_timer <= 0.0 and not self.has_fired_sound:
                self.has_fired_sound = True
                just_fired = True
        else:
            self.active_timer -= dt
        return self.active_timer > 0.0, just_fired

    def hits_player(self, player_x: float, player_radius: float) -> bool:
        if not self.is_active or self.has_dealt_damage:
            return False
        return abs(player_x - self.x) <= (self.half_width + player_radius * 0.7)

    def draw(self, surface: pygame.Surface) -> None:
        ix = int(self.x)
        if self.warning_timer > 0.0:
            progress = 1.0 - max(0.0, self.warning_timer / config.LASER_WARNING_DURATION)
            blink = 0.5 + 0.5 * math.sin(self.anim_time * (12.0 + 26.0 * progress))
            width = max(2, int(2 + 4 * progress))

            # Franja translúcida de peligro
            band = pygame.Surface((int(self.half_width * 2), config.SCREEN_HEIGHT), pygame.SRCALPHA)
            band_alpha = int((24 + 52 * progress) * (0.55 + 0.45 * blink))
            band.fill((*config.COLOR_LASER_WARN, band_alpha))
            surface.blit(band, (int(self.x - self.half_width), 0))

            # Línea roja central de advertencia (1.4 s)
            pygame.draw.line(
                surface,
                config.COLOR_LASER_WARN,
                (ix, int(self.origin_y)),
                (ix, config.SCREEN_HEIGHT),
                width,
            )
            # Retícula en el suelo
            reticle_r = int(28 - 10 * progress)
            pygame.draw.circle(surface, config.COLOR_LASER_WARN, (ix, int(config.PLAYER_Y)), max(10, reticle_r), 2)
        else:
            ratio = max(0.0, self.active_timer / config.LASER_ACTIVE_DURATION)
            outer_w = max(8, int(self.half_width * 2.2 * (0.65 + 0.35 * ratio)))
            inner_w = max(4, int(self.half_width * 0.9 * ratio))

            beam_surf = pygame.Surface((outer_w + 20, config.SCREEN_HEIGHT), pygame.SRCALPHA)
            bcx = (outer_w + 20) // 2
            pygame.draw.line(
                beam_surf,
                (*config.COLOR_LASER_BEAM, 145),
                (bcx, int(self.origin_y)),
                (bcx, config.SCREEN_HEIGHT),
                outer_w,
            )
            pygame.draw.line(
                beam_surf,
                (*config.COLOR_LASER_CORE, 245),
                (bcx, int(self.origin_y)),
                (bcx, config.SCREEN_HEIGHT),
                inner_w,
            )
            surface.blit(beam_surf, (ix - bcx, 0))


# ---------------------------------------------------------------------------
# Los 5 arquetipos de enemigos
# ---------------------------------------------------------------------------
class Enemy:
    """Clase base para los 5 arquetipos de enemigos arcanos."""

    archetype_name: str = "Enemigo"
    is_boss: bool = False

    def __init__(
        self,
        x: float,
        y: float,
        hp: float,
        radius: float,
        score_value: int,
        shield_element: int | None = None,
    ) -> None:
        self.entity_id: int = next(_ENTITY_ID_SEQ)
        self.x: float = x
        self.y: float = y
        self.hp: float = hp
        self.max_hp: float = hp
        self.radius: float = radius
        self.score_value: int = score_value
        self.shield_element: int | None = shield_element
        self.alive: bool = True
        self.hit_flash: float = 0.0
        self.shield_flash: float = 0.0
        self.anim_time: float = random.uniform(0.0, math.tau)

    def update(
        self,
        dt: float,
        player_x: float,
        enemy_projectiles: list[EnemyProjectile],
        lasers: list[VoidLaser],
        audio,
    ) -> bool:
        """Actualiza movimiento y ataques. Retorna True si rebasó la defensa inferior."""
        self.anim_time += dt
        self.hit_flash = max(0.0, self.hit_flash - dt)
        self.shield_flash = max(0.0, self.shield_flash - dt)
        return self.y - self.radius > config.SCREEN_HEIGHT + 10

    def receive_hit(
        self,
        damage: float,
        spell_id: int | None = None,
        overcharged: bool = False,
        reflected_orb: bool = False,
    ) -> str:
        """Aplica impacto respetando escudos elementales.

        Retorna: 'shield_broken', 'blocked', 'killed', o 'damaged'.
        """
        if not self.alive:
            return "blocked"

        if self.shield_element is not None:
            can_break = overcharged or reflected_orb or (spell_id == self.shield_element)
            if not can_break:
                self.shield_flash = 0.24
                return "blocked"
            # ¡Escudo elemental roto!
            self.shield_element = None
            self.hit_flash = 0.22
            if overcharged or reflected_orb:
                self.hp -= damage * 0.75
            else:
                self.hp -= damage * 0.25
            if self.hp <= 0.0:
                self.alive = False
                return "killed"
            return "shield_broken"

        self.hp -= damage
        self.hit_flash = 0.16
        if self.hp <= 0.0:
            self.alive = False
            return "killed"
        return "damaged"

    def draw_hp_bar(self, surface: pygame.Surface) -> None:
        if self.is_boss or self.hp >= self.max_hp:
            return
        w = int(self.radius * 2.1)
        h = 6
        x = int(self.x - w / 2)
        y = int(self.y - self.radius - 14)
        ratio = max(0.0, self.hp / max(self.max_hp, 1.0))
        pygame.draw.rect(surface, (18, 20, 34), (x, y, w, h), border_radius=3)
        pygame.draw.rect(surface, (240, 88, 108), (x, y, int(w * ratio), h), border_radius=3)

    def draw_elemental_shield(
        self,
        surface: pygame.Surface,
        number_font: pygame.font.Font,
    ) -> None:
        if self.shield_element is None:
            return
        spec = config.SPELLS[self.shield_element]
        ring_col = config.COLOR_TEXT_MAIN if self.shield_flash > 0 else spec.color
        shield_r = self.radius + 14.0
        draw_runic_circle(
            surface,
            (self.x, self.y),
            shield_r,
            ring_col,
            self.anim_time * 1.9,
            charge=0.25,
            sides=6,
            alpha=235,
        )
        # Insignia con número 1..4 muy nítido en el centro
        badge_r = 16 if not self.is_boss else 20
        pygame.draw.circle(surface, (10, 12, 26), (int(self.x), int(self.y)), badge_r)
        pygame.draw.circle(surface, ring_col, (int(self.x), int(self.y)), badge_r, width=3)
        label = number_font.render(str(self.shield_element), True, spec.core_color)
        surface.blit(label, label.get_rect(center=(int(self.x), int(self.y))))

    def draw(self, surface: pygame.Surface, number_font: pygame.font.Font) -> None:
        raise NotImplementedError


class EspectroErrante(Enemy):
    """1. Espectro Errante: descenso lineal clásico."""

    archetype_name = "Espectro Errante"

    def __init__(self, x: float, wave: int) -> None:
        hp = 42.0 + wave * 9.0
        super().__init__(x=x, y=-34.0, hp=hp, radius=24.0, score_value=100)
        self.speed = min(175.0, 74.0 + wave * 8.5 + random.uniform(-8.0, 12.0))

    def update(self, dt, player_x, enemy_projectiles, lasers, audio) -> bool:
        self.y += self.speed * dt
        return super().update(dt, player_x, enemy_projectiles, lasers, audio)

    def draw(self, surface: pygame.Surface, number_font: pygame.font.Font) -> None:
        col = (255, 240, 240) if self.hit_flash > 0 else config.COLOR_WRAITH
        cx, cy = self.x, self.y
        wobble = math.sin(self.anim_time * 6.0) * 4.0

        # Cuerpo fantasmal con cola ondulante
        pts = [
            (cx, cy - 26),
            (cx + 21, cy - 8),
            (cx + 18, cy + 16),
            (cx + 8 + wobble, cy + 26),
            (cx, cy + 18),
            (cx - 8 + wobble, cy + 26),
            (cx - 18, cy + 16),
            (cx - 21, cy - 8),
        ]
        pygame.draw.polygon(surface, (42, 48, 86), pts)
        pygame.draw.polygon(surface, col, pts, width=2)
        pygame.draw.circle(surface, (235, 245, 255), (int(cx - 7), int(cy - 6)), 3)
        pygame.draw.circle(surface, (235, 245, 255), (int(cx + 7), int(cy - 6)), 3)
        self.draw_hp_bar(surface)


class CentinelaRunico(Enemy):
    """2. Centinela Rúnico: anillo elemental (1..4) con número visible en su centro."""

    archetype_name = "Centinela Rúnico"

    def __init__(self, x: float, wave: int, element: int | None = None) -> None:
        chosen = element if element in config.SPELLS else random.randint(1, 4)
        hp = 68.0 + wave * 13.0
        super().__init__(
            x=x,
            y=-44.0,
            hp=hp,
            radius=28.0,
            score_value=220,
            shield_element=chosen,
        )
        self.speed = min(130.0, 52.0 + wave * 5.5)

    def update(self, dt, player_x, enemy_projectiles, lasers, audio) -> bool:
        self.y += self.speed * dt
        return super().update(dt, player_x, enemy_projectiles, lasers, audio)

    def draw(self, surface: pygame.Surface, number_font: pygame.font.Font) -> None:
        cx, cy = self.x, self.y
        base_col = (255, 240, 240) if self.hit_flash > 0 else (112, 128, 178)

        # Octágono cristalino del centinela
        pts = []
        for i in range(8):
            a = self.anim_time * 0.7 + (math.tau * i / 8.0)
            pts.append((cx + math.cos(a) * self.radius, cy + math.sin(a) * self.radius))
        pygame.draw.polygon(surface, (28, 34, 62), pts)
        pygame.draw.polygon(surface, base_col, pts, width=3)

        self.draw_elemental_shield(surface, number_font)
        self.draw_hp_bar(surface)


class InvocadorIgneo(Enemy):
    """3. Invocador Ígneo: se detiene a media pantalla y dispara orbes rojos reflejables."""

    archetype_name = "Invocador Ígneo"

    def __init__(self, x: float, wave: int) -> None:
        hp = 64.0 + wave * 11.0
        super().__init__(x=x, y=-40.0, hp=hp, radius=26.0, score_value=240)
        self.target_y = random.uniform(155.0, 265.0)
        self.descent_speed = 135.0
        self.anchor_x = x
        self.sway_amp = random.uniform(35.0, 70.0)
        self.fire_interval = max(1.65, 2.75 - wave * 0.12)
        self.fire_timer = random.uniform(0.9, 1.5)

    def update(self, dt, player_x, enemy_projectiles, lasers, audio) -> bool:
        if self.y < self.target_y:
            self.y = min(self.target_y, self.y + self.descent_speed * dt)
        else:
            self.x = max(
                config.ARENA_LEFT + 44.0,
                min(config.ARENA_RIGHT - 44.0, self.anchor_x + math.sin(self.anim_time * 1.4) * self.sway_amp),
            )
            self.fire_timer -= dt
            if self.fire_timer <= 0.0:
                self.fire_timer = self.fire_interval
                dx = player_x - self.x
                dy = config.PLAYER_Y - self.y
                dist = max(math.hypot(dx, dy), 1e-5)
                speed = 290.0
                enemy_projectiles.append(
                    EnemyProjectile(
                        x=self.x,
                        y=self.y + self.radius + 4,
                        vx=(dx / dist) * speed,
                        vy=(dy / dist) * speed,
                    )
                )
        return super().update(dt, player_x, enemy_projectiles, lasers, audio)

    def draw(self, surface: pygame.Surface, number_font: pygame.font.Font) -> None:
        cx, cy = self.x, self.y
        col = (255, 240, 220) if self.hit_flash > 0 else config.COLOR_PYROMANCER

        # Silueta de invocador con cuernos y núcleo ardiente
        body = [
            (cx, cy - 30),
            (cx + 24, cy - 6),
            (cx + 15, cy + 25),
            (cx, cy + 16),
            (cx - 15, cy + 25),
            (cx - 24, cy - 6),
        ]
        pygame.draw.polygon(surface, (68, 22, 24), body)
        pygame.draw.polygon(surface, col, body, width=2)

        # Indicador de carga antes de lanzar el orbe rojo
        charge_ratio = max(0.0, 1.0 - self.fire_timer / self.fire_interval)
        orb_r = 5.0 + 7.5 * charge_ratio
        draw_glow_circle(surface, config.COLOR_ENEMY_ORB, (cx, cy + 2), orb_r, config.COLOR_ENEMY_ORB_CORE, 2)
        self.draw_hp_bar(surface)


class EnjambreEtereo(Enemy):
    """4. Enjambre Etéreo: grupos rápidos en zigzag con poca vida."""

    archetype_name = "Enjambre Etéreo"

    def __init__(self, x: float, wave: int, phase_offset: float = 0.0) -> None:
        hp = 22.0 + wave * 3.5
        super().__init__(x=x, y=-24.0 - phase_offset * 22.0, hp=hp, radius=16.0, score_value=75)
        self.base_x = x
        self.speed_y = min(230.0, 118.0 + wave * 10.0)
        self.zigzag_amp = random.uniform(55.0, 95.0)
        self.zigzag_freq = random.uniform(3.4, 4.6)
        self.phase = phase_offset

    def update(self, dt, player_x, enemy_projectiles, lasers, audio) -> bool:
        self.y += self.speed_y * dt
        self.x = self.base_x + math.sin(self.anim_time * self.zigzag_freq + self.phase) * self.zigzag_amp
        self.x = max(config.ARENA_LEFT + 28.0, min(config.ARENA_RIGHT - 28.0, self.x))
        return super().update(dt, player_x, enemy_projectiles, lasers, audio)

    def draw(self, surface: pygame.Surface, number_font: pygame.font.Font) -> None:
        cx, cy = self.x, self.y
        col = (240, 255, 255) if self.hit_flash > 0 else config.COLOR_SWARM
        wing = 16.0 + 5.0 * math.sin(self.anim_time * 18.0)
        pts = [
            (cx, cy - 16),
            (cx + wing, cy),
            (cx, cy + 16),
            (cx - wing, cy),
        ]
        pygame.draw.polygon(surface, (20, 62, 68), pts)
        pygame.draw.polygon(surface, col, pts, width=2)
        pygame.draw.circle(surface, (220, 255, 245), (int(cx), int(cy)), 4)


class SenorDelVacio(Enemy):
    """5. Señor del Vacío (Jefe, Oleada 5+): escudo elemental, ráfagas triples y láseres."""

    archetype_name = "Señor del Vacío"
    is_boss = True

    def __init__(self, wave: int) -> None:
        hp = 520.0 + (wave - config.BOSS_MIN_WAVE) * 140.0
        super().__init__(
            x=config.SCREEN_WIDTH * 0.5,
            y=-90.0,
            hp=hp,
            radius=54.0,
            score_value=1500,
            shield_element=random.randint(1, 4),
        )
        self.target_y = 138.0
        self.burst_timer = 2.1
        self.laser_timer = 4.2
        self.shield_regen_timer = 0.0

    def update(self, dt, player_x, enemy_projectiles, lasers, audio) -> bool:
        if self.y < self.target_y:
            self.y = min(self.target_y, self.y + 95.0 * dt)
        else:
            # Desplazamiento majestuoso dentro de la zona de juego recortada
            max_sway = max(120.0, config.ARENA_WIDTH * 0.5 - self.radius - 36.0)
            self.x = config.SCREEN_WIDTH * 0.5 + math.sin(self.anim_time * 0.72) * max_sway

            # Regeneración periódica de escudo elemental tras haber sido roto
            if self.shield_element is None:
                self.shield_regen_timer += dt
                if self.shield_regen_timer >= 9.0:
                    self.shield_regen_timer = 0.0
                    self.shield_element = random.randint(1, 4)
            else:
                self.shield_regen_timer = 0.0

            # Ráfaga triple reflejable
            self.burst_timer -= dt
            if self.burst_timer <= 0.0:
                self.burst_timer = 2.65
                dx = player_x - self.x
                dy = config.PLAYER_Y - self.y
                base_angle = math.atan2(dy, dx)
                speed = 305.0
                for spread_deg in (-16.0, 0.0, 16.0):
                    a = base_angle + math.radians(spread_deg)
                    enemy_projectiles.append(
                        EnemyProjectile(
                            x=self.x,
                            y=self.y + self.radius * 0.7,
                            vx=math.cos(a) * speed,
                            vy=math.sin(a) * speed,
                            radius=12.0,
                        )
                    )

            # Rayo láser vertical telegrafiado (1.4 s)
            self.laser_timer -= dt
            if self.laser_timer <= 0.0:
                self.laser_timer = 5.4
                lasers.append(VoidLaser(x=player_x, origin_y=self.y + 20.0))
                if audio is not None:
                    audio.play("laser_warn", 0.85)

        return super().update(dt, player_x, enemy_projectiles, lasers, audio)

    def draw(self, surface: pygame.Surface, number_font: pygame.font.Font) -> None:
        cx, cy = self.x, self.y
        col = (255, 225, 255) if self.hit_flash > 0 else config.COLOR_VOID_LORD

        # Halo oscuro exterior del jefe
        draw_runic_circle(
            surface,
            (cx, cy),
            self.radius + 26.0,
            (130, 42, 200),
            -self.anim_time * 1.1,
            charge=0.35,
            sides=8,
            alpha=155,
        )

        # Alas / corona del Señor del Vacío
        crown = [
            (cx, cy - 58),
            (cx + 22, cy - 36),
            (cx + 56, cy - 22),
            (cx + 42, cy + 16),
            (cx + 18, cy + 48),
            (cx, cy + 36),
            (cx - 18, cy + 48),
            (cx - 42, cy + 16),
            (cx - 56, cy - 22),
            (cx - 22, cy - 36),
        ]
        pygame.draw.polygon(surface, (28, 12, 48), crown)
        pygame.draw.polygon(surface, col, crown, width=3)

        # Ojos del vacío si no hay escudo tapando el centro
        if self.shield_element is None:
            pygame.draw.circle(surface, config.COLOR_LASER_WARN, (int(cx - 16), int(cy - 6)), 7)
            pygame.draw.circle(surface, config.COLOR_LASER_WARN, (int(cx + 16), int(cy - 6)), 7)
            pygame.draw.circle(surface, config.COLOR_LASER_CORE, (int(cx - 16), int(cy - 6)), 3)
            pygame.draw.circle(surface, config.COLOR_LASER_CORE, (int(cx + 16), int(cy - 6)), 3)
        else:
            self.draw_elemental_shield(surface, number_font)
