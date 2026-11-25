"""Arcane Vision: Duelo de Magos — Bucle principal, HUD, oleadas y pantalla completa.

Ejecuta el juego arcade controlado por visión computacional (MediaPipe Tasks)
con renderizado procedural en Pygame-CE, ventana grande redimensionable y
alternancia instantánea de pantalla completa (F11 / Alt+Enter / botón HUD).
"""

from __future__ import annotations

import argparse
import math
import random

import numpy as np
import pygame

import config
from audio_fx import AudioFX
from game_entities import (
    AngularShield,
    CentinelaRunico,
    Enemy,
    EnemyProjectile,
    EnjambreEtereo,
    EspectroErrante,
    FloatingText,
    InvocadorIgneo,
    ParticleSystem,
    PlayerProjectile,
    SenorDelVacio,
    VoidLaser,
    WizardAvatar,
    draw_glow_circle,
    draw_runic_circle,
    segment_circle_collision,
)
from vision_engine import VisionEngine, VisionState


class DisplayManager:
    """Administra lienzo lógico 1280x720, ventana grande redimensionable y pantalla completa."""

    def __init__(self, start_fullscreen: bool = False) -> None:
        self.canvas = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        self.fullscreen = False
        self.desktop_size = self._detect_desktop_size()
        self.windowed_size = self._compute_initial_window_size(*self.desktop_size)
        self.window: pygame.Surface = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        pygame.display.set_caption(config.WINDOW_TITLE)
        self.viewport_rect = self._compute_viewport_rect(self.window.get_size())

        if start_fullscreen:
            self.set_fullscreen(True)

    @staticmethod
    def _detect_desktop_size() -> tuple[int, int]:
        try:
            sizes = pygame.display.get_desktop_sizes()
            if sizes:
                return int(sizes[0][0]), int(sizes[0][1])
        except pygame.error:
            pass
        info = pygame.display.Info()
        w = info.current_w if info.current_w > 0 else config.SCREEN_WIDTH
        h = info.current_h if info.current_h > 0 else config.SCREEN_HEIGHT
        return int(w), int(h)

    @staticmethod
    def _compute_initial_window_size(desktop_w: int, desktop_h: int) -> tuple[int, int]:
        avail_w = max(config.MIN_WINDOW_WIDTH, int(desktop_w * config.WINDOW_SCALE_RATIO))
        avail_h = max(config.MIN_WINDOW_HEIGHT, int(desktop_h * config.WINDOW_SCALE_RATIO))
        aspect = config.SCREEN_WIDTH / config.SCREEN_HEIGHT

        win_w = min(avail_w, int(avail_h * aspect))
        win_h = int(win_w / aspect)
        win_w = min(win_w, max(640, desktop_w - 40))
        win_h = min(win_h, max(360, desktop_h - 80))
        return max(640, win_w), max(360, win_h)

    @staticmethod
    def _compute_viewport_rect(window_size: tuple[int, int]) -> pygame.Rect:
        win_w, win_h = max(1, window_size[0]), max(1, window_size[1])
        scale = min(win_w / config.SCREEN_WIDTH, win_h / config.SCREEN_HEIGHT)
        dst_w = max(1, int(round(config.SCREEN_WIDTH * scale)))
        dst_h = max(1, int(round(config.SCREEN_HEIGHT * scale)))
        dst_x = (win_w - dst_w) // 2
        dst_y = (win_h - dst_h) // 2
        return pygame.Rect(dst_x, dst_y, dst_w, dst_h)

    def set_fullscreen(self, enabled: bool) -> bool:
        if enabled == self.fullscreen:
            return self.fullscreen
        if enabled:
            self.windowed_size = self.window.get_size()
            try:
                self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                self.fullscreen = True
            except pygame.error:
                self.window = pygame.display.set_mode(self.desktop_size, pygame.FULLSCREEN)
                self.fullscreen = True
        else:
            w = max(config.MIN_WINDOW_WIDTH // 2, self.windowed_size[0])
            h = max(config.MIN_WINDOW_HEIGHT // 2, self.windowed_size[1])
            self.window = pygame.display.set_mode((w, h), pygame.RESIZABLE)
            self.fullscreen = False
        self.viewport_rect = self._compute_viewport_rect(self.window.get_size())
        return self.fullscreen

    def toggle_fullscreen(self) -> bool:
        return self.set_fullscreen(not self.fullscreen)

    def handle_resize(self, width: int, height: int) -> None:
        if self.fullscreen:
            return
        w = max(640, width)
        h = max(360, height)
        self.windowed_size = (w, h)
        surf = pygame.display.get_surface()
        if surf is not None:
            self.window = surf
        self.viewport_rect = self._compute_viewport_rect(self.window.get_size())

    def window_to_canvas(self, pos: tuple[int, int]) -> tuple[float, float]:
        vr = self.viewport_rect
        x = (pos[0] - vr.x) * (config.SCREEN_WIDTH / max(vr.width, 1))
        y = (pos[1] - vr.y) * (config.SCREEN_HEIGHT / max(vr.height, 1))
        return (x, y)

    def present(self, shake_offset: tuple[int, int] = (0, 0)) -> None:
        self.window.fill(config.COLOR_LETTERBOX)
        vr = self.viewport_rect
        if vr.size == (config.SCREEN_WIDTH, config.SCREEN_HEIGHT):
            scaled = self.canvas
        else:
            scaled = pygame.transform.smoothscale(self.canvas, vr.size)
        self.window.blit(scaled, (vr.x + shake_offset[0], vr.y + shake_offset[1]))
        pygame.display.flip()


class ArcaneVisionGame:
    """Controlador principal de Arcane Vision: Duelo de Magos."""

    def __init__(
        self,
        camera_index: int = 0,
        start_fullscreen: bool = False,
        left_handed: bool = False,
        enable_audio: bool = True,
    ) -> None:
        pygame.init()
        self.display = DisplayManager(start_fullscreen=start_fullscreen)
        self.clock = pygame.time.Clock()
        self.audio = AudioFX(enabled=enable_audio)
        self.vision = VisionEngine(camera_index=camera_index, left_handed=left_handed)

        # Fuentes limpias del sistema
        self.font_title = pygame.font.SysFont("dejavusans,arial,sans", 56, bold=True)
        self.font_large = pygame.font.SysFont("dejavusans,arial,sans", 34, bold=True)
        self.font_medium = pygame.font.SysFont("dejavusans,arial,sans", 22, bold=True)
        self.font_small = pygame.font.SysFont("dejavusans,arial,sans", 16, bold=False)
        self.font_badge = pygame.font.SysFont("dejavusans,arial,sans", 24, bold=True)

        # Estrellas decorativas de fondo arcano
        rng = random.Random(7)
        self.stars = [
            (
                rng.uniform(0, config.SCREEN_WIDTH),
                rng.uniform(0, config.SCREEN_HEIGHT),
                rng.uniform(1.0, 2.6),
                rng.uniform(12.0, 36.0),
            )
            for _ in range(70)
        ]

        # Botones interactivos del HUD en coordenadas del lienzo 1280x720
        self.fullscreen_btn_rect = pygame.Rect(config.SCREEN_WIDTH - 224, 14, 208, 36)
        self.start_btn_rect = pygame.Rect(config.SCREEN_WIDTH // 2 - 170, 560, 340, 56)

        # Estado del juego
        self.running = True
        self.mode = "title"  # "title" | "playing" | "meditation" | "gameover"
        self.anim_time = 0.0
        self.wizard = WizardAvatar()
        self.shield = AngularShield()
        self.particles = ParticleSystem()
        self.floating_texts: list[FloatingText] = []

        self.player_projectiles: list[PlayerProjectile] = []
        self.enemy_projectiles: list[EnemyProjectile] = []
        self.lasers: list[VoidLaser] = []
        self.enemies: list[Enemy] = []

        self.selected_spell = 1
        self.fire_cooldown = 0.0
        self.charge_level = 0.0
        self.charge_tick_timer = 0.0
        self.prev_mouth_open = False
        self.prev_vision_spell = 1

        # Progresión de oleadas
        self.wave = 1
        self.wave_timer = config.WAVE_DURATION
        self.meditation_timer = config.MEDITATION_DURATION
        self.spawn_timer = 1.0
        self.boss_spawned_this_wave = False

        # Estadísticas y feedback visual
        self.score = 0
        self.kills = 0
        self.reflected_count = 0
        self.overcharge_count = 0
        self.shake_timer = 0.0
        self.shake_strength = 0.0
        self.toast_text = ""
        self.toast_timer = 0.0

        # Cache de cámara convertida a Surface
        self._last_frame_ref = None
        self._camera_bg_surf: pygame.Surface | None = None

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------
    def _render_loading_screen(self, message: str) -> None:
        pygame.event.pump()
        c = self.display.canvas
        c.fill(config.COLOR_BG_DARK)
        draw_runic_circle(
            c,
            (config.SCREEN_WIDTH * 0.5, config.SCREEN_HEIGHT * 0.44),
            92.0,
            config.SPELLS[1].color,
            pygame.time.get_ticks() * 0.002,
            charge=0.5,
            sides=6,
            alpha=210,
        )
        title = self.font_large.render(config.WINDOW_TITLE, True, config.COLOR_TEXT_GOLD)
        sub = self.font_medium.render(message, True, config.COLOR_TEXT_MAIN)
        c.blit(title, title.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2 + 78)))
        c.blit(sub, sub.get_rect(center=(config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2 + 122)))
        self.display.present()

    def run(self) -> None:
        """Inicializa visión computacional y ejecuta el bucle principal a 60 FPS."""
        try:
            self._render_loading_screen("Verificando modelos de MediaPipe (Hand + Face)...")
            self.vision.start(progress_callback=self._render_loading_screen)
            while self.running:
                dt = min(self.clock.tick(config.FPS) / 1000.0, 0.05)
                self.anim_time += dt
                vision_state = self.vision.update()
                self._handle_events(vision_state)
                self._update(dt, vision_state)
                self._render(vision_state)
        finally:
            self.vision.stop()
            pygame.quit()

    def _start_new_game(self) -> None:
        self.wizard.reset()
        self.particles.clear()
        self.floating_texts.clear()
        self.player_projectiles.clear()
        self.enemy_projectiles.clear()
        self.lasers.clear()
        self.enemies.clear()

        self.wave = 1
        self.wave_timer = config.WAVE_DURATION
        self.meditation_timer = config.MEDITATION_DURATION
        self.spawn_timer = 0.8
        self.boss_spawned_this_wave = False

        self.score = 0
        self.kills = 0
        self.reflected_count = 0
        self.overcharge_count = 0
        self.charge_level = 0.0
        self.fire_cooldown = 0.0
        self.mode = "playing"
        self.audio.play("wave_start", 0.85)
        self._show_toast("¡Oleada 1 iniciada! Muestra 1-4 dedos y abre la palma para atacar")

    def _show_toast(self, text: str, duration: float = 2.6) -> None:
        self.toast_text = text
        self.toast_timer = duration

    def _add_shake(self, strength: float, duration: float = 0.16) -> None:
        self.shake_strength = max(self.shake_strength, strength)
        self.shake_timer = max(self.shake_timer, duration)

    # ------------------------------------------------------------------
    # Eventos de teclado y ratón
    # ------------------------------------------------------------------
    def _handle_events(self, vision_state: VisionState) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                self.display.handle_resize(event.w, event.h)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                cx, cy = self.display.window_to_canvas(event.pos)
                if self.fullscreen_btn_rect.collidepoint(cx, cy):
                    is_fs = self.display.toggle_fullscreen()
                    self._show_toast("Pantalla completa activada" if is_fs else "Modo ventana restaurado", 1.8)
                elif self.mode in ("title", "gameover") and self.start_btn_rect.collidepoint(cx, cy):
                    self._start_new_game()
            elif event.type == pygame.KEYDOWN:
                self._handle_keydown(event, vision_state)

    def _handle_keydown(self, event: pygame.event.Event, vision_state: VisionState) -> None:
        alt_held = bool(event.mod & pygame.KMOD_ALT)
        if event.key == pygame.K_F11 or (event.key == pygame.K_RETURN and alt_held):
            is_fs = self.display.toggle_fullscreen()
            self._show_toast("Pantalla completa activada" if is_fs else "Modo ventana restaurado", 1.8)
            return

        if event.key == pygame.K_ESCAPE:
            if self.display.fullscreen:
                self.display.set_fullscreen(False)
                self._show_toast("Saliste de pantalla completa (pulsa ESC otra vez para cerrar)", 2.2)
            else:
                self.running = False
            return

        if event.key == pygame.K_h:
            is_left = self.vision.toggle_handedness()
            self.audio.play("spell_switch", 0.9)
            label = "ZURDO (Izq: Ataque / Der: Escudo)" if is_left else "DIESTRO (Der: Ataque / Izq: Escudo)"
            self._show_toast(f"Modo {label}", 2.6)
            return

        if event.key == pygame.K_m:
            muted = self.audio.toggle_mute()
            self._show_toast("Audio silenciado" if muted else "Audio activado", 1.6)
            return

        if event.key == pygame.K_r and self.mode in ("playing", "meditation", "gameover"):
            self._start_new_game()
            return

        if event.key in (pygame.K_RETURN, pygame.K_SPACE) and self.mode in ("title", "gameover"):
            self._start_new_game()
            return

        # Selección de hechizo por teclado (respaldo si no hay mano dominante en cámara)
        if not vision_state.dominant_present:
            key_to_spell = {
                pygame.K_1: 1,
                pygame.K_2: 2,
                pygame.K_3: 3,
                pygame.K_4: 4,
            }
            if event.key in key_to_spell:
                self.selected_spell = key_to_spell[event.key]
                self.audio.play("spell_switch", 0.65)

    # ------------------------------------------------------------------
    # Actualización de simulación
    # ------------------------------------------------------------------
    def _update(self, dt: float, vs: VisionState) -> None:
        # Actualizar fondo estelar
        for idx, (sx, sy, sr, spd) in enumerate(self.stars):
            ny = sy + spd * dt
            if ny > config.SCREEN_HEIGHT:
                ny -= config.SCREEN_HEIGHT
            self.stars[idx] = (sx, ny, sr, spd)

        self.toast_timer = max(0.0, self.toast_timer - dt)
        if self.shake_timer > 0.0:
            self.shake_timer = max(0.0, self.shake_timer - dt)
            if self.shake_timer <= 0.0:
                self.shake_strength = 0.0

        # Sincronizar selección de hechizo con MediaPipe (cuando hay mano dominante)
        if vs.dominant_present and vs.selected_spell != self.prev_vision_spell:
            self.prev_vision_spell = vs.selected_spell
            self.selected_spell = vs.selected_spell
            self.audio.play("spell_switch", 0.6)
        elif vs.dominant_present:
            self.selected_spell = vs.selected_spell

        # Actualizar escudo deflector angular (visible incluso en pantalla de título para calibrar)
        keys = pygame.key.get_pressed()
        kb_shield = not vs.shield_present and keys[pygame.K_LSHIFT]
        shield_active = vs.shield_active or kb_shield
        shield_pos = vs.shield_pos if vs.shield_present else (self.wizard.x, self.wizard.y - 86.0)
        shield_angle = vs.shield_angle if vs.shield_present else 0.0
        self.shield.update(shield_active, shield_pos, shield_angle, dt)

        # Movimiento lateral del mago (inclinación de cabeza + respaldo de flechas)
        kb_move = (int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(keys[pygame.K_LEFT] or keys[pygame.K_a]))
        move_input = kb_move if kb_move != 0 else vs.head_move
        self.wizard.update(move_input, dt)

        self.particles.update(dt)
        self.floating_texts = [ft for ft in self.floating_texts if ft.update(dt)]

        if self.mode == "title":
            # En pantalla de título permitimos probar la carga bucal visualmente
            if vs.mouth_open:
                self.charge_level = min(1.0, self.charge_level + config.CHARGE_FILL_RATE * dt)
            else:
                self.charge_level = max(0.0, self.charge_level - config.CHARGE_DECAY_RATE * dt)
            return

        if self.mode == "gameover":
            self.charge_level = 0.0
            return

        if self.mode == "meditation":
            self._update_meditation(dt)
            return

        # --- Modo "playing" ---
        self._update_combat(dt, vs, keys)

    def _update_meditation(self, dt: float) -> None:
        self.charge_level = max(0.0, self.charge_level - config.CHARGE_DECAY_RATE * dt)
        self.meditation_timer -= dt

        prev_hp = int(self.wizard.hp)
        self.wizard.heal(config.MEDITATION_HEAL_PER_SEC * dt)
        if int(self.wizard.hp) > prev_hp and int(self.wizard.hp) % 5 == 0:
            self.floating_texts.append(
                FloatingText("+5 HP", self.wizard.x + random.uniform(-24, 24), self.wizard.y - 36, config.COLOR_MEDITATION)
            )

        if random.random() < 0.35:
            self.particles.emit_trail(
                self.wizard.x + random.uniform(-44, 44),
                self.wizard.y + random.uniform(-16, 18),
                config.COLOR_MEDITATION,
                radius=4.5,
                life=0.45,
            )

        if self.meditation_timer <= 0.0:
            self.wave += 1
            self.wave_timer = config.WAVE_DURATION
            self.spawn_timer = 0.9
            self.boss_spawned_this_wave = False
            self.mode = "playing"
            self.audio.play("wave_start", 0.9)
            if self.wave >= config.BOSS_MIN_WAVE:
                self._show_toast(f"¡Oleada {self.wave}! ¡El Señor del Vacío se aproxima!", 3.2)
            else:
                self._show_toast(f"¡Oleada {self.wave} iniciada!", 2.4)

    def _update_combat(self, dt: float, vs: VisionState, keys) -> None:
        # 1. Reloj de oleada (35 s -> 6 s de Meditación Arcana)
        self.wave_timer -= dt
        if self.wave_timer <= 0.0:
            self._enter_meditation()
            return

        # 2. Spawner de enemigos según la oleada
        self._update_spawner(dt)

        # 3. Conjuración bucal (carga + disparo gigante sobrecargado al cerrar) y disparo rápido (5 dedos)
        self.fire_cooldown = max(0.0, self.fire_cooldown - dt)
        mouth_is_open = vs.mouth_open or (not vs.face_present and keys[pygame.K_c])
        cast_origin = vs.dominant_pos if vs.dominant_present else (self.wizard.x, self.wizard.y - 44.0)

        if mouth_is_open:
            self.charge_level = min(1.0, self.charge_level + config.CHARGE_FILL_RATE * dt)
            self.charge_tick_timer -= dt
            if self.charge_tick_timer <= 0.0:
                self.charge_tick_timer = 0.28
                self.audio.play("charge_tick", 0.35 + 0.35 * self.charge_level)
            # Partículas atraídas hacia el círculo rúnico de la mano
            if random.random() < 0.65:
                ang = random.uniform(0.0, math.tau)
                dist = 55.0 + 45.0 * self.charge_level
                px = cast_origin[0] + math.cos(ang) * dist
                py = cast_origin[1] + math.sin(ang) * dist
                col = (
                    config.COLOR_OVERCHARGE_AURA
                    if self.charge_level >= config.OVERCHARGE_MIN_CHARGE
                    else config.SPELLS[self.selected_spell].color
                )
                self.particles.emit_trail(px, py, col, radius=4.0, life=0.22)
        else:
            if self.prev_mouth_open and self.charge_level >= config.OVERCHARGE_MIN_CHARGE:
                self._fire_overcharged_spell(cast_origin, self.charge_level)
                self.charge_level = 0.0
            else:
                self.charge_level = max(0.0, self.charge_level - config.CHARGE_DECAY_RATE * dt)

            # Disparo rápido con palma completa (5 dedos) o Espacio si no hay mano
            rapid_fire = vs.rapid_fire_active or (not vs.dominant_present and keys[pygame.K_SPACE])
            if rapid_fire and self.fire_cooldown <= 0.0:
                self._fire_basic_spell(cast_origin)

        self.prev_mouth_open = mouth_is_open

        # 4. Actualizar proyectiles del jugador
        self.player_projectiles = [p for p in self.player_projectiles if p.update(dt, self.particles)]

        # 5. Actualizar enemigos y detectar brechas en la línea inferior
        survivors: list[Enemy] = []
        for enemy in self.enemies:
            breached = enemy.update(dt, self.wizard.x, self.enemy_projectiles, self.lasers, self.audio)
            if breached:
                if self.wizard.take_damage(config.ENEMY_BREACH_DAMAGE):
                    self.audio.play("player_hit", 0.85)
                    self._add_shake(7.0, 0.22)
                    self.floating_texts.append(
                        FloatingText(f"-{int(config.ENEMY_BREACH_DAMAGE)} HP", self.wizard.x, self.wizard.y - 44, config.COLOR_HP_LOW)
                    )
            elif enemy.alive:
                survivors.append(enemy)
        self.enemies = survivors

        # 6. Actualizar proyectiles enemigos (reflejo con escudo angular + colisión con enemigos/jugador)
        self._update_enemy_projectiles(dt)

        # 7. Actualizar rayos láser verticales telegrafiados
        self._update_lasers(dt)

        # 8. Colisiones de proyectiles del jugador contra enemigos
        self._resolve_player_projectile_hits()

        # 9. Comprobar derrota
        if self.wizard.hp <= 0.0:
            self.mode = "gameover"
            self.audio.play("game_over", 0.9)
            self.particles.emit_burst(self.wizard.x, self.wizard.y, config.COLOR_HP_LOW, count=42)
            self._add_shake(12.0, 0.35)

    def _enter_meditation(self) -> None:
        self.mode = "meditation"
        self.meditation_timer = config.MEDITATION_DURATION
        self.charge_level = 0.0
        self.prev_mouth_open = False

        # Limpiar proyectiles y enemigos residuales convirtiéndolos en chispas arcanas
        for enemy in self.enemies:
            self.particles.emit_burst(enemy.x, enemy.y, config.COLOR_MEDITATION, count=14)
        self.enemies.clear()
        self.enemy_projectiles.clear()
        self.lasers.clear()
        self.player_projectiles.clear()

        self.audio.play("meditation_start", 0.9)
        self._show_toast("Meditación Arcana: baja los brazos 6 s mientras recuperas salud", 3.5)

    def _update_spawner(self, dt: float) -> None:
        # Jefe en oleada 5+
        if self.wave >= config.BOSS_MIN_WAVE and not self.boss_spawned_this_wave:
            self.boss_spawned_this_wave = True
            self.enemies.append(SenorDelVacio(self.wave))
            self.floating_texts.append(
                FloatingText("¡SEÑOR DEL VACÍO!", config.SCREEN_WIDTH * 0.5, 180.0, config.COLOR_VOID_LORD, life=1.8, max_life=1.8)
            )

        self.spawn_timer -= dt
        if self.spawn_timer > 0.0:
            return

        has_boss = any(e.is_boss for e in self.enemies)
        base_interval = max(0.85, 2.15 - self.wave * 0.14)
        self.spawn_timer = base_interval * (1.45 if has_boss else 1.0)

        # Límite razonable de enemigos simultáneos para legibilidad
        if len(self.enemies) >= (7 if has_boss else 11):
            return

        margin = 95.0
        x = random.uniform(margin, config.SCREEN_WIDTH - margin)
        roll = random.random()

        if self.wave == 1:
            if roll < 0.52:
                self.enemies.append(EspectroErrante(x, self.wave))
            elif roll < 0.78:
                self._spawn_swarm_pack(x)
            else:
                self.enemies.append(CentinelaRunico(x, self.wave))
        elif self.wave == 2:
            if roll < 0.30:
                self.enemies.append(EspectroErrante(x, self.wave))
            elif roll < 0.55:
                self.enemies.append(CentinelaRunico(x, self.wave))
            elif roll < 0.80:
                self.enemies.append(InvocadorIgneo(x, self.wave))
            else:
                self._spawn_swarm_pack(x)
        else:
            if roll < 0.24:
                self.enemies.append(EspectroErrante(x, self.wave))
            elif roll < 0.52:
                self.enemies.append(CentinelaRunico(x, self.wave))
            elif roll < 0.78:
                self.enemies.append(InvocadorIgneo(x, self.wave))
            else:
                self._spawn_swarm_pack(x)

    def _spawn_swarm_pack(self, center_x: float) -> None:
        count = random.randint(3, 4)
        for i in range(count):
            offset_x = (i - (count - 1) * 0.5) * 42.0
            sx = max(70.0, min(config.SCREEN_WIDTH - 70.0, center_x + offset_x))
            self.enemies.append(EnjambreEtereo(sx, self.wave, phase_offset=i * 0.7))

    # ------------------------------------------------------------------
    # Disparo con asistencia suave de puntería y sobrecarga
    # ------------------------------------------------------------------
    def _aim_direction_with_assist(self, origin: tuple[float, float]) -> float:
        """Calcula ángulo de disparo hacia arriba con asistencia suave hacia enemigos cercanos."""
        base_angle = -math.pi * 0.5  # Arriba puro
        ox, oy = origin
        max_rad = math.radians(config.AIM_ASSIST_MAX_ANGLE_DEG)

        best_angle_diff = max_rad
        best_target_angle = None
        best_score = float("inf")

        for enemy in self.enemies:
            if not enemy.alive or enemy.y >= oy - 16.0:
                continue
            dx = enemy.x - ox
            dy = enemy.y - oy
            dist = math.hypot(dx, dy)
            if dist > config.AIM_ASSIST_RANGE or dist < 1e-3:
                continue
            ang = math.atan2(dy, dx)
            diff = (ang - base_angle + math.pi) % math.tau - math.pi
            if abs(diff) <= max_rad:
                # Prioriza enemigos más alineados y cercanos
                metric = dist * (0.55 + abs(diff) / max_rad)
                if metric < best_score:
                    best_score = metric
                    best_angle_diff = diff
                    best_target_angle = base_angle + diff

        if best_target_angle is not None:
            return base_angle + best_angle_diff * config.AIM_ASSIST_STRENGTH
        return base_angle

    def _fire_basic_spell(self, origin: tuple[float, float]) -> None:
        spec = config.SPELLS[self.selected_spell]
        self.fire_cooldown = spec.cooldown
        aim_angle = self._aim_direction_with_assist(origin)

        count = spec.projectile_count
        for i in range(count):
            if count == 1:
                spread = 0.0
            else:
                spread = math.radians((i - (count - 1) * 0.5) * spec.spread_deg)
            ang = aim_angle + spread
            is_crit = random.random() < spec.crit_chance
            dmg = spec.damage * (spec.crit_multiplier if is_crit else 1.0)
            self.player_projectiles.append(
                PlayerProjectile(
                    x=origin[0],
                    y=origin[1] - 12.0,
                    vx=math.cos(ang) * spec.speed,
                    vy=math.sin(ang) * spec.speed,
                    spell_id=spec.spell_id,
                    damage=dmg,
                    radius=spec.radius + (2 if is_crit else 0),
                    color=spec.color,
                    core_color=spec.core_color,
                    overcharged=False,
                    is_crit=is_crit,
                )
            )

        self.particles.emit_burst(origin[0], origin[1] - 10.0, spec.color, count=6, speed_range=(40, 140), life_range=(0.12, 0.25))
        self.audio.play(f"spell_{spec.spell_id}", 0.72)

    def _fire_overcharged_spell(self, origin: tuple[float, float], charge: float) -> None:
        spec = config.SPELLS[self.selected_spell]
        aim_angle = self._aim_direction_with_assist(origin)
        scale = 0.75 + 0.55 * charge
        self.player_projectiles.append(
            PlayerProjectile(
                x=origin[0],
                y=origin[1] - 14.0,
                vx=math.cos(aim_angle) * spec.overcharge_speed,
                vy=math.sin(aim_angle) * spec.overcharge_speed,
                spell_id=spec.spell_id,
                damage=spec.overcharge_damage * scale,
                radius=spec.overcharge_radius * (0.85 + 0.25 * charge),
                color=spec.color,
                core_color=config.COLOR_OVERCHARGE_CORE,
                overcharged=True,
                is_crit=True,
            )
        )
        self.overcharge_count += 1
        self.audio.play("overcharge_fire", 0.95)
        self._add_shake(8.5, 0.22)
        self.particles.emit_ring(origin[0], origin[1], config.COLOR_OVERCHARGE_AURA, max_radius=110.0, duration=0.35, width=5)
        self.particles.emit_burst(origin[0], origin[1], config.COLOR_OVERCHARGE_AURA, count=28, speed_range=(90, 320))
        self.floating_texts.append(
            FloatingText("¡SOBRECARGA!", origin[0], origin[1] - 46.0, config.COLOR_OVERCHARGE_AURA, life=1.0, max_life=1.0)
        )

    # ------------------------------------------------------------------
    # Colisiones
    # ------------------------------------------------------------------
    def _resolve_player_projectile_hits(self) -> None:
        remaining_projectiles: list[PlayerProjectile] = []
        for proj in self.player_projectiles:
            consumed = False
            for enemy in self.enemies:
                if not enemy.alive or enemy.entity_id in proj.hit_enemy_ids:
                    continue
                hit_r = enemy.radius + (14.0 if enemy.shield_element is not None else 0.0) + proj.radius
                if math.hypot(proj.x - enemy.x, proj.y - enemy.y) <= hit_r:
                    proj.hit_enemy_ids.add(enemy.entity_id)
                    required_el = enemy.shield_element
                    outcome = enemy.receive_hit(
                        damage=proj.damage,
                        spell_id=proj.spell_id,
                        overcharged=proj.overcharged,
                    )
                    self._handle_enemy_hit_feedback(enemy, proj.x, proj.y, proj.damage, proj.color, proj.is_crit, outcome, required_el)

                    if not proj.overcharged:
                        consumed = True
                        break
            if not consumed:
                remaining_projectiles.append(proj)

        self.player_projectiles = remaining_projectiles
        self.enemies = [e for e in self.enemies if e.alive]

    def _update_enemy_projectiles(self, dt: float) -> None:
        shield_p1, shield_p2 = self.shield.endpoints()
        kept: list[EnemyProjectile] = []

        for orb in self.enemy_projectiles:
            if not orb.update(dt, self.particles):
                continue

            # 1. Rebote contra el escudo deflector angular
            if not orb.reflected and self.shield.active:
                hit, normal = segment_circle_collision(
                    shield_p1,
                    shield_p2,
                    (orb.x, orb.y),
                    orb.radius + self.shield.thickness * 0.65,
                )
                if hit:
                    orb.reflect(normal, self.enemies)
                    self.shield.trigger_flash()
                    self.reflected_count += 1
                    self.score += 60
                    self.audio.play("shield_deflect", 0.9)
                    self._add_shake(4.5, 0.12)
                    self.particles.emit_ring(orb.x, orb.y, config.COLOR_SHIELD_PRIMARY, max_radius=62.0, duration=0.25)
                    self.particles.emit_burst(orb.x, orb.y, config.COLOR_REFLECTED_ORB, count=18)
                    self.floating_texts.append(
                        FloatingText("¡REFLEJADO!", orb.x, orb.y - 26.0, config.COLOR_REFLECTED_ORB)
                    )
                    kept.append(orb)
                    continue

            # 2. Orbe reflejado impacta contra enemigos
            if orb.reflected:
                hit_enemy = False
                for enemy in self.enemies:
                    if not enemy.alive:
                        continue
                    if math.hypot(orb.x - enemy.x, orb.y - enemy.y) <= enemy.radius + orb.radius + 8.0:
                        required_el = enemy.shield_element
                        outcome = enemy.receive_hit(
                            damage=orb.damage,
                            spell_id=None,
                            overcharged=False,
                            reflected_orb=True,
                        )
                        self._handle_enemy_hit_feedback(
                            enemy, orb.x, orb.y, orb.damage, config.COLOR_REFLECTED_ORB, True, outcome, required_el
                        )
                        hit_enemy = True
                        break
                if not hit_enemy:
                    kept.append(orb)
                continue

            # 3. Orbe enemigo impacta al mago
            if math.hypot(orb.x - self.wizard.x, orb.y - self.wizard.y) <= self.wizard.radius + orb.radius:
                if self.wizard.take_damage(orb.damage):
                    self.audio.play("player_hit", 0.9)
                    self._add_shake(8.0, 0.22)
                    self.particles.emit_burst(orb.x, orb.y, config.COLOR_ENEMY_ORB, count=20)
                    self.floating_texts.append(
                        FloatingText(f"-{int(orb.damage)} HP", self.wizard.x, self.wizard.y - 44, config.COLOR_HP_LOW)
                    )
                continue

            kept.append(orb)

        self.enemy_projectiles = kept
        self.enemies = [e for e in self.enemies if e.alive]

    def _update_lasers(self, dt: float) -> None:
        active_lasers: list[VoidLaser] = []
        for laser in self.lasers:
            still_alive, just_fired = laser.update(dt)
            if just_fired:
                self.audio.play("laser_fire", 0.92)
                self._add_shake(9.0, 0.28)
                self.particles.emit_burst(laser.x, config.PLAYER_Y, config.COLOR_LASER_BEAM, count=24)

            if laser.hits_player(self.wizard.x, self.wizard.radius):
                laser.has_dealt_damage = True
                if self.wizard.take_damage(config.LASER_DAMAGE):
                    self.audio.play("player_hit", 0.95)
                    self._add_shake(11.0, 0.28)
                    self.particles.emit_burst(self.wizard.x, self.wizard.y, config.COLOR_LASER_WARN, count=28)
                    self.floating_texts.append(
                        FloatingText(f"-{int(config.LASER_DAMAGE)} HP", self.wizard.x, self.wizard.y - 48, config.COLOR_HP_LOW)
                    )

            if still_alive:
                active_lasers.append(laser)
        self.lasers = active_lasers

    def _handle_enemy_hit_feedback(
        self,
        enemy: Enemy,
        hx: float,
        hy: float,
        damage: float,
        color: tuple[int, int, int],
        is_crit: bool,
        outcome: str,
        required_element: int | None,
    ) -> None:
        if outcome == "blocked":
            self.particles.emit_burst(hx, hy, (200, 210, 240), count=6, speed_range=(40, 120), life_range=(0.12, 0.25))
            if required_element is not None:
                self.floating_texts.append(
                    FloatingText(
                        f"Requiere {required_element}!",
                        enemy.x,
                        enemy.y - enemy.radius - 18,
                        config.SPELLS[required_element].color,
                        life=0.65,
                        max_life=0.65,
                    )
                )
        elif outcome == "shield_broken":
            self.audio.play("shield_break", 0.9)
            self._add_shake(5.5, 0.14)
            ring_col = config.SPELLS[required_element].color if required_element in config.SPELLS else color
            self.particles.emit_ring(enemy.x, enemy.y, ring_col, max_radius=enemy.radius + 54, duration=0.32, width=5)
            self.particles.emit_burst(enemy.x, enemy.y, ring_col, count=26, speed_range=(90, 290))
            self.floating_texts.append(
                FloatingText("¡ESCUDO ROTO!", enemy.x, enemy.y - enemy.radius - 22, config.COLOR_TEXT_GOLD, life=0.95, max_life=0.95)
            )
        elif outcome == "killed":
            self.kills += 1
            self.score += enemy.score_value
            self.audio.play("enemy_die", 0.85 if not enemy.is_boss else 1.0)
            self._add_shake(10.0 if enemy.is_boss else 4.0, 0.25 if enemy.is_boss else 0.10)
            self.particles.emit_ring(enemy.x, enemy.y, color, max_radius=enemy.radius + (85 if enemy.is_boss else 40))
            self.particles.emit_burst(enemy.x, enemy.y, color, count=52 if enemy.is_boss else 22)
            label = f"+{enemy.score_value} ¡JEFE DERROTADO!" if enemy.is_boss else f"+{enemy.score_value}"
            self.floating_texts.append(
                FloatingText(label, enemy.x, enemy.y - 12, config.COLOR_TEXT_GOLD, life=1.1 if enemy.is_boss else 0.75, max_life=1.1 if enemy.is_boss else 0.75)
            )
        else:
            self.audio.play("enemy_hit", 0.65)
            self.particles.emit_burst(hx, hy, color, count=10, speed_range=(50, 170), life_range=(0.15, 0.35))
            txt = f"-{int(round(damage))}!" if is_crit else f"-{int(round(damage))}"
            txt_col = config.COLOR_TEXT_GOLD if is_crit else color
            self.floating_texts.append(FloatingText(txt, hx, hy - 14, txt_col, life=0.55, max_life=0.55))

    # ------------------------------------------------------------------
    # Renderizado procedural
    # ------------------------------------------------------------------
    def _render(self, vs: VisionState) -> None:
        c = self.display.canvas
        c.fill(config.COLOR_BG_DARK)

        # 1. Fondo de webcam con baja opacidad
        self._draw_camera_background(c, vs)

        # 2. Campo estelar y línea del santuario inferior
        for sx, sy, sr, _ in self.stars:
            pygame.draw.circle(c, (110, 130, 190), (int(sx), int(sy)), max(1, int(sr * 0.65)))
        pygame.draw.line(c, (42, 58, 112), (0, int(config.PLAYER_Y + 34)), (config.SCREEN_WIDTH, int(config.PLAYER_Y + 34)), 2)

        # 3. Rayos láser, enemigos, proyectiles, partículas
        for laser in self.lasers:
            laser.draw(c)
        for enemy in self.enemies:
            enemy.draw(c, self.font_badge)
        for orb in self.enemy_projectiles:
            orb.draw(c)
        for proj in self.player_projectiles:
            proj.draw(c)
        self.particles.draw(c)

        # 4. Avatar del mago
        active_spec = config.SPELLS[self.selected_spell]
        self.wizard.draw(c, active_spec.color, meditating=(self.mode == "meditation"))

        # 5. Círculos rúnicos sobre las manos y escudo deflector angular
        self._draw_hand_overlays(c, vs)

        # 6. Textos flotantes
        for ft in self.floating_texts:
            ft.draw(c, self.font_medium)

        # 7. HUD y pantallas superpuestas según estado
        self._draw_hud(c, vs)
        if self.mode == "title":
            self._draw_title_overlay(c, vs)
        elif self.mode == "meditation":
            self._draw_meditation_overlay(c)
        elif self.mode == "gameover":
            self._draw_gameover_overlay(c)

        # 8. Toast informativo temporal
        if self.toast_timer > 0.0 and self.toast_text:
            self._draw_toast(c)

        # 9. Presentar con shake sutil
        shake = (0, 0)
        if self.shake_timer > 0.0:
            mag = int(self.shake_strength * (self.shake_timer / 0.25))
            if mag > 0:
                shake = (random.randint(-mag, mag), random.randint(-mag, mag))
        self.display.present(shake_offset=shake)

    def _draw_camera_background(self, surface: pygame.Surface, vs: VisionState) -> None:
        if vs.frame_rgb is None:
            return
        if vs.frame_rgb is not self._last_frame_ref:
            self._last_frame_ref = vs.frame_rgb
            h, w = vs.frame_rgb.shape[:2]
            raw = pygame.image.frombuffer(vs.frame_rgb, (w, h), "RGB")
            scaled = pygame.transform.smoothscale(raw, (config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
            scaled.set_alpha(config.CAMERA_BG_ALPHA)
            self._camera_bg_surf = scaled
        if self._camera_bg_surf is not None:
            surface.blit(self._camera_bg_surf, (0, 0))

    def _draw_hand_overlays(self, surface: pygame.Surface, vs: VisionState) -> None:
        spec = config.SPELLS[self.selected_spell]

        # Mano dominante: círculo rúnico que crece con la carga bucal
        if vs.dominant_present:
            radius = 38.0 + 48.0 * self.charge_level + (8.0 if vs.rapid_fire_active else 0.0)
            ring_color = (
                config.COLOR_OVERCHARGE_AURA
                if self.charge_level >= config.OVERCHARGE_MIN_CHARGE
                else spec.color
            )
            draw_runic_circle(
                surface,
                vs.dominant_pos,
                radius,
                ring_color,
                self.anim_time * (2.4 + 4.5 * self.charge_level),
                charge=self.charge_level,
                sides=5 + (self.selected_spell % 3),
                alpha=230,
            )
            if self.charge_level >= config.OVERCHARGE_MIN_CHARGE:
                tag_txt = "¡CIERRA LA BOCA!"
                tag_col = config.COLOR_OVERCHARGE_AURA
            elif vs.rapid_fire_active:
                tag_txt = f"DISPARANDO • {spec.short_name}"
                tag_col = spec.core_color
            else:
                tag_txt = f"ATAQUE ({self.selected_spell}) • {spec.short_name}"
                tag_col = spec.color
            lbl = self.font_small.render(tag_txt, True, tag_col)
            surface.blit(lbl, lbl.get_rect(center=(int(vs.dominant_pos[0]), int(vs.dominant_pos[1] + radius + 16))))

        # Mano secundaria: escudo deflector angular (o anillo tenue si palma cerrada)
        if self.shield.active:
            self.shield.draw(surface)
            lbl = self.font_small.render("ESCUDO ACTIVO", True, config.COLOR_SHIELD_GLOW)
            surface.blit(lbl, lbl.get_rect(center=(int(self.shield.x), int(self.shield.y + 32))))
        elif vs.shield_present:
            draw_runic_circle(
                surface,
                vs.shield_pos,
                28.0,
                config.COLOR_SHIELD_PRIMARY,
                -self.anim_time * 1.4,
                charge=0.0,
                sides=4,
                alpha=115,
            )
            lbl = self.font_small.render("ESCUDO (abre palma)", True, config.COLOR_TEXT_MUTED)
            surface.blit(lbl, lbl.get_rect(center=(int(vs.shield_pos[0]), int(vs.shield_pos[1] + 40))))

    def _draw_panel(self, surface: pygame.Surface, rect: pygame.Rect, border_color=config.COLOR_PANEL_BORDER) -> None:
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(panel, config.COLOR_PANEL_BG, panel.get_rect(), border_radius=10)
        pygame.draw.rect(panel, (*border_color, 215), panel.get_rect(), width=2, border_radius=10)
        surface.blit(panel, rect.topleft)

    def _draw_hud(self, surface: pygame.Surface, vs: VisionState) -> None:
        # 1. Panel superior izquierdo: Vida, Puntuación y Modo Diestro/Zurdo
        left_panel = pygame.Rect(16, 14, 300, 96)
        self._draw_panel(surface, left_panel)

        hp_ratio = max(0.0, self.wizard.hp / max(self.wizard.max_hp, 1.0))
        hp_col = (
            config.COLOR_HP_HIGH
            if hp_ratio > 0.55
            else (config.COLOR_HP_MID if hp_ratio > 0.25 else config.COLOR_HP_LOW)
        )
        bar_rect = pygame.Rect(30, 26, 200, 18)
        pygame.draw.rect(surface, (20, 24, 42), bar_rect, border_radius=6)
        pygame.draw.rect(surface, hp_col, (bar_rect.x, bar_rect.y, int(bar_rect.w * hp_ratio), bar_rect.h), border_radius=6)
        pygame.draw.rect(surface, (180, 195, 230), bar_rect, width=1, border_radius=6)

        hp_txt = self.font_small.render(f"{int(round(self.wizard.hp))}/{int(self.wizard.max_hp)}", True, config.COLOR_TEXT_MAIN)
        surface.blit(hp_txt, (238, 25))

        score_txt = self.font_medium.render(f"Puntos: {self.score:,}", True, config.COLOR_TEXT_GOLD)
        surface.blit(score_txt, (30, 50))

        hand_mode = "ZURDO [H]" if vs.left_handed else "DIESTRO [H]"
        mode_txt = self.font_small.render(f"Mano: {hand_mode}", True, config.COLOR_TEXT_MUTED)
        surface.blit(mode_txt, (30, 82))

        # 2. Panel superior central: Oleada, tiempo restante y barra del Jefe
        center_panel = pygame.Rect(config.SCREEN_WIDTH // 2 - 190, 14, 380, 68)
        self._draw_panel(
            surface,
            center_panel,
            border_color=config.COLOR_MEDITATION if self.mode == "meditation" else config.COLOR_PANEL_BORDER,
        )
        if self.mode == "meditation":
            w_title = f"MEDITACIÓN ARCANA • {self.meditation_timer:0.1f}s"
            ratio = max(0.0, self.meditation_timer / config.MEDITATION_DURATION)
            bar_col = config.COLOR_MEDITATION
        else:
            w_title = f"OLEADA {self.wave} • {max(0.0, self.wave_timer):0.1f}s"
            ratio = max(0.0, self.wave_timer / config.WAVE_DURATION)
            bar_col = config.COLOR_VOID_LORD if self.wave >= config.BOSS_MIN_WAVE else config.SPELLS[1].color

        lbl = self.font_medium.render(w_title, True, config.COLOR_TEXT_MAIN)
        surface.blit(lbl, lbl.get_rect(center=(config.SCREEN_WIDTH // 2, 34)))
        t_bar = pygame.Rect(config.SCREEN_WIDTH // 2 - 165, 54, 330, 12)
        pygame.draw.rect(surface, (20, 24, 42), t_bar, border_radius=5)
        pygame.draw.rect(surface, bar_col, (t_bar.x, t_bar.y, int(t_bar.w * ratio), t_bar.h), border_radius=5)

        # Barra de vida del Jefe (Señor del Vacío) si está presente
        boss = next((e for e in self.enemies if e.is_boss and e.alive), None)
        if boss is not None:
            boss_bar = pygame.Rect(config.SCREEN_WIDTH // 2 - 220, 90, 440, 22)
            pygame.draw.rect(surface, (24, 12, 38), boss_bar, border_radius=7)
            b_ratio = max(0.0, boss.hp / max(boss.max_hp, 1.0))
            pygame.draw.rect(surface, config.COLOR_VOID_LORD, (boss_bar.x, boss_bar.y, int(boss_bar.w * b_ratio), boss_bar.h), border_radius=7)
            pygame.draw.rect(surface, (235, 195, 255), boss_bar, width=2, border_radius=7)
            b_lbl = self.font_small.render(f"SEÑOR DEL VACÍO  {int(boss.hp)}/{int(boss.max_hp)}", True, config.COLOR_TEXT_MAIN)
            surface.blit(b_lbl, b_lbl.get_rect(center=boss_bar.center))

        # 3. Botón superior derecho: Pantalla Completa + estado cámara y audio
        self._draw_panel(surface, self.fullscreen_btn_rect, border_color=config.COLOR_TEXT_GOLD if self.display.fullscreen else config.COLOR_PANEL_BORDER)
        fs_label = "[F11] Salir Completa" if self.display.fullscreen else "[F11] Pantalla Completa"
        fs_surf = self.font_small.render(fs_label, True, config.COLOR_TEXT_MAIN)
        surface.blit(fs_surf, fs_surf.get_rect(center=self.fullscreen_btn_rect.center))

        # Estado de cámara y audio debajo del botón
        cam_col = config.COLOR_HP_HIGH if vs.camera_available else config.COLOR_HP_MID
        cam_text = "Cámara OK" if vs.camera_available else (vs.camera_status or "Sin cámara")
        audio_text = "Audio OFF [M]" if self.audio.muted or not self.audio.enabled else "Audio ON [M]"
        status_surf = self.font_small.render(f"● {cam_text}  |  {audio_text}", True, cam_col)
        surface.blit(status_surf, (config.SCREEN_WIDTH - status_surf.get_width() - 18, 56))

        # 4. Panel inferior izquierdo: Grimorio de los 4 hechizos
        dock_x, dock_y = 16, config.SCREEN_HEIGHT - 74
        for idx in range(1, 5):
            spec = config.SPELLS[idx]
            rect = pygame.Rect(dock_x + (idx - 1) * 124, dock_y, 116, 58)
            active = idx == self.selected_spell
            self._draw_panel(surface, rect, border_color=spec.color if active else (54, 66, 102))
            if active:
                pygame.draw.rect(surface, spec.color, rect.inflate(4, 4), width=2, border_radius=12)
            draw_glow_circle(surface, spec.color, (rect.x + 22, rect.y + 29), 11, spec.core_color, 1)
            n_surf = self.font_small.render(str(idx), True, (8, 10, 22))
            surface.blit(n_surf, n_surf.get_rect(center=(rect.x + 22, rect.y + 29)))
            name_surf = self.font_small.render(spec.short_name, True, config.COLOR_TEXT_MAIN if active else config.COLOR_TEXT_MUTED)
            surface.blit(name_surf, (rect.x + 40, rect.y + 12))
            sub_txt = f"{idx} dedo" if idx == 1 else f"{idx} dedos"
            sub_surf = self.font_small.render(sub_txt, True, spec.color if active else config.COLOR_TEXT_MUTED)
            surface.blit(sub_surf, (rect.x + 40, rect.y + 32))

        # 5. Panel inferior derecho: Medidor de Carga Bucal (Sobrecarga)
        gauge_panel = pygame.Rect(config.SCREEN_WIDTH - 270, config.SCREEN_HEIGHT - 74, 254, 58)
        ready = self.charge_level >= config.OVERCHARGE_MIN_CHARGE
        self._draw_panel(surface, gauge_panel, border_color=config.COLOR_OVERCHARGE_AURA if ready else config.COLOR_PANEL_BORDER)
        g_lbl = self.font_small.render(
            "¡SOBRECARGA LISTA!" if ready else "Carga Bucal (abre boca)",
            True,
            config.COLOR_OVERCHARGE_AURA if ready else config.COLOR_TEXT_MUTED,
        )
        surface.blit(g_lbl, (gauge_panel.x + 14, gauge_panel.y + 8))

        meter = pygame.Rect(gauge_panel.x + 14, gauge_panel.y + 32, gauge_panel.w - 28, 14)
        pygame.draw.rect(surface, (20, 24, 42), meter, border_radius=5)
        fill_col = config.COLOR_OVERCHARGE_AURA if ready else config.SPELLS[self.selected_spell].color
        pygame.draw.rect(surface, fill_col, (meter.x, meter.y, int(meter.w * self.charge_level), meter.h), border_radius=5)
        # Marca del umbral mínimo de sobrecarga
        thresh_x = meter.x + int(meter.w * config.OVERCHARGE_MIN_CHARGE)
        pygame.draw.line(surface, config.COLOR_TEXT_MAIN, (thresh_x, meter.y - 3), (thresh_x, meter.bottom + 3), 2)

    def _draw_title_overlay(self, surface: pygame.Surface, vs: VisionState) -> None:
        dim = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((6, 8, 20, 150))
        surface.blit(dim, (0, 0))

        title = self.font_title.render("ARCANE VISION", True, config.COLOR_TEXT_GOLD)
        subtitle = self.font_large.render("Duelo de Magos", True, config.SPELLS[1].core_color)
        surface.blit(title, title.get_rect(center=(config.SCREEN_WIDTH // 2, 165)))
        surface.blit(subtitle, subtitle.get_rect(center=(config.SCREEN_WIDTH // 2, 218)))

        card = pygame.Rect(config.SCREEN_WIDTH // 2 - 390, 255, 780, 275)
        self._draw_panel(surface, card, border_color=config.SPELLS[1].color)

        lines = [
            ("Mano Dominante (1-4 dedos):", "Elige hechizo — 1 Arcano | 2 Ígneo | 3 Esmeralda | 4 Voltaica"),
            ("Palma Abierta (5 dedos):", "Disparo rápido del hechizo activo con asistencia suave"),
            ("Abrir y Cerrar la Boca:", "Carga el círculo mágico y libera un proyectil gigante perforante"),
            ("Mano Secundaria (palma abierta):", "Escudo Deflector Angular — inclina la mano para rebotar orbes rojos"),
            ("Inclinar la Cabeza:", "Esquiva lateralmente los ataques y rayos láser del Señor del Vacío"),
            ("Atajos:", "[F11 / Alt+Enter] Pantalla Completa  •  [H] Zurdo/Diestro  •  [R] Reiniciar  •  [ESC] Salir"),
        ]
        y = card.y + 24
        for heading, desc in lines:
            h_surf = self.font_small.render(heading, True, config.COLOR_TEXT_GOLD)
            d_surf = self.font_small.render(desc, True, config.COLOR_TEXT_MAIN)
            surface.blit(h_surf, (card.x + 24, y))
            surface.blit(d_surf, (card.x + 266, y))
            y += 38

        # Indicador biométrico en vivo antes de empezar
        bio_status = (
            f"Rostro: {'OK' if vs.face_present else '...'}   |   "
            f"Ataque: {vs.dominant_fingers} dedos   |   "
            f"Escudo: {'ACTIVO' if vs.shield_active else ('OK' if vs.shield_present else '...')}"
        )
        bio_surf = self.font_small.render(bio_status, True, config.COLOR_MEDITATION)
        surface.blit(bio_surf, bio_surf.get_rect(center=(config.SCREEN_WIDTH // 2, card.bottom - 18)))

        # Botón comenzar
        self._draw_panel(surface, self.start_btn_rect, border_color=config.COLOR_TEXT_GOLD)
        btn_txt = self.font_medium.render("PULSA ENTER O HAZ CLIC PARA COMENZAR", True, config.COLOR_TEXT_GOLD)
        surface.blit(btn_txt, btn_txt.get_rect(center=self.start_btn_rect.center))

    def _draw_meditation_overlay(self, surface: pygame.Surface) -> None:
        # Borde verde calmado
        overlay = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (*config.COLOR_MEDITATION, 55), overlay.get_rect(), width=18)
        surface.blit(overlay, (0, 0))

        box = pygame.Rect(config.SCREEN_WIDTH // 2 - 330, 210, 660, 188)
        self._draw_panel(surface, box, border_color=config.COLOR_MEDITATION)

        t1 = self.font_large.render("MEDITACIÓN ARCANA", True, config.COLOR_MEDITATION)
        t2 = self.font_medium.render("Baja los brazos y descansa — Recuperando salud...", True, config.COLOR_TEXT_MAIN)
        t3 = self.font_large.render(f"Siguiente: Oleada {self.wave + 1} en {self.meditation_timer:0.1f}s", True, config.COLOR_TEXT_GOLD)
        surface.blit(t1, t1.get_rect(center=(config.SCREEN_WIDTH // 2, box.y + 44)))
        surface.blit(t2, t2.get_rect(center=(config.SCREEN_WIDTH // 2, box.y + 94)))
        surface.blit(t3, t3.get_rect(center=(config.SCREEN_WIDTH // 2, box.y + 144)))

    def _draw_gameover_overlay(self, surface: pygame.Surface) -> None:
        dim = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((12, 4, 14, 185))
        surface.blit(dim, (0, 0))

        box = pygame.Rect(config.SCREEN_WIDTH // 2 - 280, 185, 560, 325)
        self._draw_panel(surface, box, border_color=config.COLOR_HP_LOW)

        t1 = self.font_title.render("DUELO FINALIZADO", True, config.COLOR_HP_LOW)
        surface.blit(t1, t1.get_rect(center=(config.SCREEN_WIDTH // 2, box.y + 52)))

        stats = [
            f"Puntuación final:  {self.score:,}",
            f"Oleada alcanzada:  {self.wave}",
            f"Enemigos derrotados:  {self.kills}",
            f"Orbes reflejados:  {self.reflected_count}",
            f"Hechizos sobrecargados:  {self.overcharge_count}",
        ]
        y = box.y + 114
        for line in stats:
            s = self.font_medium.render(line, True, config.COLOR_TEXT_MAIN)
            surface.blit(s, s.get_rect(center=(config.SCREEN_WIDTH // 2, y)))
            y += 38

        self._draw_panel(surface, self.start_btn_rect, border_color=config.COLOR_TEXT_GOLD)
        btn_txt = self.font_medium.render("[R] / [ENTER] REINTENTAR DUELO", True, config.COLOR_TEXT_GOLD)
        surface.blit(btn_txt, btn_txt.get_rect(center=self.start_btn_rect.center))

    def _draw_toast(self, surface: pygame.Surface) -> None:
        txt = self.font_small.render(self.toast_text, True, config.COLOR_TEXT_MAIN)
        rect = pygame.Rect(0, 0, txt.get_width() + 36, 36)
        rect.center = (config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT - 102)
        self._draw_panel(surface, rect, border_color=config.COLOR_TEXT_GOLD)
        surface.blit(txt, txt.get_rect(center=rect.center))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Arcane Vision: Duelo de Magos")
    parser.add_argument("--camara", type=int, default=0, help="Índice de la cámara (0 por defecto)")
    parser.add_argument("--fullscreen", action="store_true", help="Iniciar directamente en pantalla completa")
    parser.add_argument("--zurdo", action="store_true", help="Iniciar en modo zurdo (también intercambiable con H)")
    parser.add_argument("--sin-audio", action="store_true", help="Desactivar efectos de sonido procedurales")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    game = ArcaneVisionGame(
        camera_index=args.camara,
        start_fullscreen=args.fullscreen,
        left_handed=args.zurdo,
        enable_audio=not args.sin_audio,
    )
    game.run()


if __name__ == "__main__":
    main()
