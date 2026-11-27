"""Motor de audio procedural en memoria con NumPy y Pygame Mixer.

Genera todos los efectos sonoros del juego en tiempo de inicialización sin
depender de archivos .wav o .mp3 externos. Si el sistema carece de dispositivo
de audio, entra en modo silencioso seguro sin interrumpir el juego.
"""

from __future__ import annotations

import numpy as np
import pygame


class AudioFX:
    """Sintetizador procedural de efectos arcanos en memoria."""

    SAMPLE_RATE = 44100

    def __init__(self, enabled: bool = True, master_volume: float = 0.45) -> None:
        self.enabled = False
        self.muted = not enabled
        self.master_volume = max(0.0, min(1.0, master_volume))
        self.sounds: dict[str, pygame.mixer.Sound] = {}

        if not enabled:
            return

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(
                    frequency=self.SAMPLE_RATE,
                    size=-16,
                    channels=2,
                    buffer=512,
                )
            pygame.mixer.set_num_channels(24)
            self.enabled = True
            self._build_bank()
        except pygame.error:
            self.enabled = False

    def toggle_mute(self) -> bool:
        """Alterna silencio y devuelve True si quedó silenciado."""
        self.muted = not self.muted
        return self.muted

    def play(self, name: str, volume: float = 1.0) -> None:
        """Reproduce un efecto sintetizado por nombre."""
        if not self.enabled or self.muted:
            return
        snd = self.sounds.get(name)
        if snd is None:
            return
        snd.set_volume(max(0.0, min(1.0, self.master_volume * volume)))
        snd.play()

    # ------------------------------------------------------------------
    # Primitivas de síntesis
    # ------------------------------------------------------------------
    def _time_axis(self, duration: float) -> np.ndarray:
        count = max(1, int(self.SAMPLE_RATE * duration))
        return np.linspace(0.0, duration, count, endpoint=False, dtype=np.float32)

    def _to_sound(self, mono: np.ndarray) -> pygame.mixer.Sound:
        peak = float(np.max(np.abs(mono))) if mono.size else 1.0
        if peak > 1.0:
            mono = mono / peak
        clipped = np.clip(mono, -1.0, 1.0)
        pcm = (clipped * 32767.0).astype(np.int16)
        stereo = np.column_stack((pcm, pcm))
        return pygame.mixer.Sound(buffer=stereo.tobytes())

    @staticmethod
    def _adsr(t: np.ndarray, attack: float, decay: float, sustain: float = 0.0) -> np.ndarray:
        env = np.ones_like(t, dtype=np.float32)
        if attack > 0.0:
            atk_mask = t < attack
            env[atk_mask] = t[atk_mask] / attack
        rel_mask = t >= attack
        if np.any(rel_mask):
            dt = t[rel_mask] - attack
            env[rel_mask] = sustain + (1.0 - sustain) * np.exp(-dt / max(decay, 1e-4))
        fade_samples = min(128, t.size)
        if fade_samples > 1:
            env[-fade_samples:] *= np.linspace(1.0, 0.0, fade_samples, dtype=np.float32)
        return env

    @staticmethod
    def _chirp(t: np.ndarray, f0: float, f1: float) -> np.ndarray:
        dur = float(t[-1]) if t.size > 1 else 1.0
        rate = (f1 - f0) / max(dur, 1e-4)
        phase = 2.0 * np.pi * (f0 * t + 0.5 * rate * t * t)
        return np.sin(phase, dtype=np.float32)

    # ------------------------------------------------------------------
    # Construcción del banco procedural
    # ------------------------------------------------------------------
    def _build_bank(self) -> None:
        rng = np.random.default_rng(42)

        # 1. Rayo Arcano (Azul): chispa cristalina veloz
        t = self._time_axis(0.14)
        wave = 0.65 * self._chirp(t, 1280.0, 620.0) + 0.35 * self._chirp(t, 1920.0, 1100.0)
        self.sounds["spell_1"] = self._to_sound(wave * self._adsr(t, 0.005, 0.045) * 0.72)

        # 2. Orbe Ígneo (Naranja): impulso grave con estela de fuego
        t = self._time_axis(0.24)
        noise = rng.standard_normal(t.size).astype(np.float32)
        # Suavizado simple de ruido (filtro paso bajo)
        kernel = np.ones(9, dtype=np.float32) / 9.0
        warm_noise = np.convolve(noise, kernel, mode="same")
        wave = 0.72 * self._chirp(t, 260.0, 82.0) + 0.42 * warm_noise
        self.sounds["spell_2"] = self._to_sound(wave * self._adsr(t, 0.012, 0.085) * 0.85)

        # 3. Espinas Esmeralda (Verde): ráfaga triple brillante
        t = self._time_axis(0.19)
        wave = np.zeros_like(t)
        for idx, freq in enumerate((620.0, 780.0, 980.0)):
            offset = idx * 0.032
            mask = t >= offset
            dt = t[mask] - offset
            wave[mask] += np.sin(2.0 * np.pi * freq * dt) * np.exp(-dt / 0.038)
        self.sounds["spell_3"] = self._to_sound(wave * 0.48)

        # 4. Tormenta Voltaica (Violeta): descarga eléctrica FM
        t = self._time_axis(0.18)
        mod = 28.0 * np.sin(2.0 * np.pi * 65.0 * t)
        carrier = np.sin(2.0 * np.pi * (920.0 - 2400.0 * t) * t + mod)
        crackle = rng.standard_normal(t.size).astype(np.float32) * 0.25
        wave = np.tanh((0.8 * carrier + crackle) * 1.4)
        self.sounds["spell_4"] = self._to_sound(wave * self._adsr(t, 0.003, 0.055) * 0.72)

        # Pulso sutil mientras se carga con la boca abierta
        t = self._time_axis(0.16)
        wave = (
            0.55 * np.sin(2.0 * np.pi * 330.0 * t)
            + 0.35 * np.sin(2.0 * np.pi * 495.0 * t)
            + 0.20 * np.sin(2.0 * np.pi * 660.0 * t)
        )
        self.sounds["charge_tick"] = self._to_sound(wave * self._adsr(t, 0.025, 0.06) * 0.38)

        # Disparo sobrecargado gigante (liberación bucal)
        t = self._time_axis(0.55)
        sub = self._chirp(t, 190.0, 46.0)
        shimmer = (
            np.sin(2.0 * np.pi * 440.0 * t)
            + 0.7 * np.sin(2.0 * np.pi * 659.25 * t)
            + 0.5 * np.sin(2.0 * np.pi * 880.0 * t)
        ) * np.exp(-t / 0.19)
        burst = np.convolve(rng.standard_normal(t.size).astype(np.float32), np.ones(6) / 6.0, mode="same")
        wave = 0.78 * sub * self._adsr(t, 0.008, 0.22) + 0.36 * shimmer + 0.28 * burst * self._adsr(t, 0.005, 0.10)
        self.sounds["overcharge_fire"] = self._to_sound(np.tanh(wave * 1.25) * 0.92)

        # Rebote en escudo deflector angular
        t = self._time_axis(0.28)
        bell = (
            0.55 * np.sin(2.0 * np.pi * 980.0 * t)
            + 0.45 * np.sin(2.0 * np.pi * 1475.0 * t)
            + 0.30 * self._chirp(t, 640.0, 1680.0)
        )
        self.sounds["shield_deflect"] = self._to_sound(bell * self._adsr(t, 0.003, 0.095) * 0.82)

        # Ruptura de escudo elemental
        t = self._time_axis(0.34)
        shatter = (
            0.40 * self._chirp(t, 1850.0, 520.0)
            + 0.35 * np.sin(2.0 * np.pi * 1240.0 * t)
            + 0.45 * rng.standard_normal(t.size).astype(np.float32) * np.exp(-t / 0.07)
        )
        self.sounds["shield_break"] = self._to_sound(shatter * self._adsr(t, 0.004, 0.11) * 0.85)

        # Impacto en enemigo
        t = self._time_axis(0.09)
        wave = 0.7 * self._chirp(t, 440.0, 160.0) + 0.3 * rng.standard_normal(t.size).astype(np.float32)
        self.sounds["enemy_hit"] = self._to_sound(wave * self._adsr(t, 0.002, 0.03) * 0.55)

        # Muerte de enemigo
        t = self._time_axis(0.24)
        wave = 0.65 * self._chirp(t, 520.0, 95.0) + 0.35 * self._chirp(t, 880.0, 220.0)
        self.sounds["enemy_die"] = self._to_sound(wave * self._adsr(t, 0.004, 0.085) * 0.72)

        # Advertencia del rayo láser del Señor del Vacío
        t = self._time_axis(0.32)
        pulse = 0.5 + 0.5 * np.sin(2.0 * np.pi * 14.0 * t)
        wave = self._chirp(t, 520.0, 940.0) * pulse
        self.sounds["laser_warn"] = self._to_sound(wave * self._adsr(t, 0.01, 0.16) * 0.65)

        # Descarga del rayo láser vertical
        t = self._time_axis(0.62)
        roar = np.convolve(rng.standard_normal(t.size).astype(np.float32), np.ones(7) / 7.0, mode="same")
        beam = 0.65 * self._chirp(t, 210.0, 72.0) + 0.45 * np.sin(2.0 * np.pi * 120.0 * t) + 0.45 * roar
        self.sounds["laser_fire"] = self._to_sound(np.tanh(beam * 1.3) * self._adsr(t, 0.015, 0.25) * 0.88)

        # Daño al mago
        t = self._time_axis(0.28)
        crunch = 0.75 * self._chirp(t, 180.0, 58.0) + 0.45 * rng.standard_normal(t.size).astype(np.float32)
        self.sounds["player_hit"] = self._to_sound(np.tanh(crunch * 1.5) * self._adsr(t, 0.004, 0.11) * 0.85)

        # Meditación Arcana (acorde relajante)
        t = self._time_axis(0.95)
        chord = np.zeros_like(t)
        for idx, freq in enumerate((261.63, 329.63, 392.00, 493.88, 587.33)):
            offset = idx * 0.055
            mask = t >= offset
            dt = t[mask] - offset
            chord[mask] += np.sin(2.0 * np.pi * freq * dt) * np.exp(-dt / 0.36)
        self.sounds["meditation_start"] = self._to_sound(chord * 0.28)

        # Inicio de oleada
        t = self._time_axis(0.48)
        fanfare = np.zeros_like(t)
        for idx, freq in enumerate((392.00, 493.88, 587.33)):
            offset = idx * 0.08
            mask = t >= offset
            dt = t[mask] - offset
            fanfare[mask] += np.sin(2.0 * np.pi * freq * dt) * np.exp(-dt / 0.18)
        self.sounds["wave_start"] = self._to_sound(fanfare * 0.40)

        # Cambio de hechizo / lateralidad
        t = self._time_axis(0.07)
        wave = self._chirp(t, 760.0, 1140.0)
        self.sounds["spell_switch"] = self._to_sound(wave * self._adsr(t, 0.002, 0.024) * 0.40)

        # Candado de hechizo (puño): bloquear / desbloquear
        t = self._time_axis(0.14)
        lock_wave = (
            0.6 * np.sin(2.0 * np.pi * 520.0 * t)
            + 0.4 * self._chirp(t, 780.0, 1040.0)
        )
        self.sounds["spell_lock"] = self._to_sound(lock_wave * self._adsr(t, 0.004, 0.045) * 0.58)

        t = self._time_axis(0.14)
        unlock_wave = (
            0.6 * np.sin(2.0 * np.pi * 680.0 * t)
            + 0.4 * self._chirp(t, 920.0, 560.0)
        )
        self.sounds["spell_unlock"] = self._to_sound(unlock_wave * self._adsr(t, 0.004, 0.045) * 0.55)

        # Barra de especial lista al 100%
        t = self._time_axis(0.42)
        ready = np.zeros_like(t)
        for idx, freq in enumerate((523.25, 659.25, 783.99, 1046.5)):
            offset = idx * 0.055
            mask = t >= offset
            dt = t[mask] - offset
            ready[mask] += np.sin(2.0 * np.pi * freq * dt) * np.exp(-dt / 0.14)
        self.sounds["special_ready"] = self._to_sound(ready * 0.36)

        # Especial Tipo A: Nova Dispersa (cascada estelar brillante)
        t = self._time_axis(0.52)
        nova = np.zeros_like(t)
        for idx, freq in enumerate((620.0, 840.0, 1080.0, 1340.0, 1620.0)):
            offset = idx * 0.038
            mask = t >= offset
            dt = t[mask] - offset
            nova[mask] += np.sin(2.0 * np.pi * freq * dt) * np.exp(-dt / 0.16)
        whoosh = np.convolve(rng.standard_normal(t.size).astype(np.float32), np.ones(5) / 5.0, mode="same")
        self.sounds["special_scatter"] = self._to_sound(
            np.tanh((0.55 * nova + 0.35 * whoosh * self._adsr(t, 0.008, 0.14)) * 1.15) * 0.85
        )

        # Escudo sobrecalentado (barra agotada -> inicia cooldown)
        t = self._time_axis(0.42)
        overheat = (
            0.65 * self._chirp(t, 760.0, 145.0)
            + 0.45 * rng.standard_normal(t.size).astype(np.float32) * np.exp(-t / 0.14)
        )
        self.sounds["shield_overheat"] = self._to_sound(np.tanh(overheat * 1.35) * self._adsr(t, 0.005, 0.17) * 0.85)

        # Escudo enfriado y disponible nuevamente
        t = self._time_axis(0.26)
        shield_ok = 0.55 * self._chirp(t, 480.0, 960.0) + 0.45 * np.sin(2.0 * np.pi * 1180.0 * t)
        self.sounds["shield_ready"] = self._to_sound(shield_ok * self._adsr(t, 0.006, 0.085) * 0.55)

        # Intercambio de manos por gesto de oración (acorde místico ascendente)
        t = self._time_axis(0.38)
        swap = np.zeros_like(t)
        for idx, freq in enumerate((440.0, 554.37, 659.25, 880.0)):
            offset = idx * 0.045
            mask = t >= offset
            dt = t[mask] - offset
            swap[mask] += np.sin(2.0 * np.pi * freq * dt) * np.exp(-dt / 0.14)
        self.sounds["hand_swap"] = self._to_sound(swap * 0.42)

        # Game Over
        t = self._time_axis(0.85)
        doom = np.zeros_like(t)
        for idx, freq in enumerate((329.63, 293.66, 246.94, 196.00)):
            offset = idx * 0.14
            mask = t >= offset
            dt = t[mask] - offset
            doom[mask] += (
                0.7 * np.sin(2.0 * np.pi * freq * dt)
                + 0.3 * np.sin(2.0 * np.pi * (freq * 0.5) * dt)
            ) * np.exp(-dt / 0.24)
        self.sounds["game_over"] = self._to_sound(doom * 0.55)
