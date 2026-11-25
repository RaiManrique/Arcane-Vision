# Arcane Vision: Duelo de Magos

Juego arcade de acción mágica controlado en tiempo real por **visión computacional**, construido con **Python 3.14**, **MediaPipe Tasks (`HandLandmarker` + `FaceLandmarker`)**, **OpenCV**, **Pygame-CE** y **NumPy**. Todos los gráficos, círculos rúnicos, enemigos y efectos de sonido se generan proceduralmente sin depender de sprites ni archivos de audio externos.

---

## Historia y Lore

En la bóveda astral del *Observatorio de Aethel*, una fisura del Vacío amenaza con consumir los sellos que protegen el plano mortal. Como último **Arcanista del Espejo**, canalizas magia elemental directamente con tus manos, concentras energía rúnica mediante el aliento arcano y desvías las llamas infernales con una barrera prismática mientras esquivas los haces del **Señor del Vacío**.

---

## Controles Biométricos

| Gesto | Parte del cuerpo | Acción | Efecto en el juego |
| --- | --- | --- | --- |
| Mostrar **1 a 4 dedos** | Mano dominante | Selección de hechizo | Cambia el hechizo activo del Grimorio (conteo relativo a la muñeca, invariante a la inclinación). |
| Abrir la **palma completa (5 dedos)** con boca cerrada | Mano dominante | Disparo rápido | Lanza proyectiles básicos del hechizo activo con asistencia suave de puntería. |
| **Abrir la boca** sostenidamente | Rostro (`jawOpen` + MAR) | Carga arcana | El círculo rúnico de la mano dominante crece y acumula energía sobre el umbral de sobrecarga. |
| **Cerrar la boca** tras superar la carga | Rostro | Disparo sobrecargado | Libera un proyectil gigante perforante que atraviesa enemigos y rompe cualquier escudo elemental. |
| Abrir la **palma** y rotar la muñeca | Mano secundaria | Escudo Deflector Angular | Despliega una barrera cuya inclinación sigue el eje nudillo índice–meñique para rebotar orbes rojos contra los enemigos. |
| **Inclinar la cabeza** a izquierda o derecha | Rostro (*roll* entre ojos) | Esquive lateral | Desplaza el avatar del mago en la franja inferior para evadir rayos láser y proyectiles. |

> **Soporte para zurdos:** Pulsa **`H`** en cualquier momento para intercambiar dinámicamente la mano de ataque y la mano del escudo.

---

## Grimorio de los 4 Hechizos

| Dedos | Hechizo | Color | Especialidad |
| :---: | --- | --- | --- |
| **1** | **Rayo Arcano** | Azul | Alta velocidad y cadencia ágil; ideal contra enemigos rápidos y escudos `1`. |
| **2** | **Orbe Ígneo** | Naranja | Proyectil grande de gran impacto y daño alto; ideal contra objetivos resistentes y escudos `2`. |
| **3** | **Espinas Esmeralda** | Verde | Disparo triple en abanico; excelente para barrer enjambres y romper escudos `3`. |
| **4** | **Tormenta Voltaica** | Violeta | Velocidad superior y altísima probabilidad de golpe crítico; ideal contra jefes y escudos `4`. |

---

## Bestiario: 5 Arquetipos de Enemigos

1. **Espectro Errante:** Desciende en línea recta hacia la base del mago. Elimínalo con cualquier hechizo antes de que cruce la línea inferior.
2. **Centinela Rúnico:** Protegido por un anillo elemental de color con un número visible (**`1`** a **`4`**) en su centro. Solo sufre daño al romper su escudo con el hechizo de ese número de dedos, con un disparo sobrecargado o con un orbe reflejado.
3. **Invocador Ígneo:** Desciende hasta media pantalla, se detiene y dispara orbes rojos. Abre la mano secundaria e inclina tu **Escudo Deflector Angular** para devolverlos con daño multiplicado.
4. **Enjambre Etéreo:** Aparece en grupos rápidos con trayectoria en zigzag y poca salud. **Espinas Esmeralda (3 dedos)** o **Rayo Arcano (1 dedo)** son ideales para interceptarlos.
5. **Señor del Vacío (Jefe, Oleada 5+):** Enorme resistencia, escudo elemental regenerable, ráfagas triples reflejables y **rayos láser verticales** anunciados por una línea roja pulsante durante **1.4 segundos**. Inclina la cabeza a tiempo para salir de la zona roja y combina sobrecargas con reflejos para derrotarlo.

### Progresión Anti-Fatiga (*Meditación Arcana*)
Cada oleada dura **35 segundos** y se intercala automáticamente con una pausa de **6 segundos de Meditación Arcana**. Durante ese descanso se limpian las amenazas, tu salud se regenera progresivamente y puedes bajar ambos brazos para evitar fatiga física.

---

## Instalación y Ejecución

El proyecto fue diseñado y probado con **Python 3.14** y las versiones más recientes de MediaPipe Tasks, OpenCV, Pygame-CE y NumPy. Al iniciar por primera vez, `vision_engine.py` descarga automáticamente los modelos oficiales `hand_landmarker.task` y `face_landmarker.task` dentro de `models/`.

### Linux / macOS (con `uv` — recomendado)

```bash
cd Pc4
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python main.py
```

### Linux / macOS (con `venv` y `pip`)

```bash
cd Pc4
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

### Windows 11 (PowerShell)

```powershell
cd Pc4
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

### Opciones de línea de comandos

```bash
.venv/bin/python main.py --camara 0        # Seleccionar índice de cámara (por defecto 0)
.venv/bin/python main.py --fullscreen      # Iniciar directamente en pantalla completa
.venv/bin/python main.py --zurdo           # Iniciar con manos intercambiadas
.venv/bin/python main.py --sin-audio       # Desactivar el sintetizador de audio
```

---

## Pantalla Grande, Pantalla Completa y Atajos de Teclado

La aplicación abre por defecto una **ventana grande redimensionable** escalada limpiamente desde el lienzo lógico `1280×720` (60 FPS) y permite alternar a pantalla completa en cualquier instante:

| Atajo | Acción |
| --- | --- |
| **`F11`** o **`Alt + Enter`** (o botón en el HUD) | Entrar o salir de **Pantalla Completa** |
| **`H`** | Intercambiar mano dominante / secundaria (**Diestro ↔ Zurdo**) |
| **`R`** | Reiniciar el duelo inmediatamente |
| **`M`** | Silenciar o reactivar el audio procedural |
| **`ESC`** | Salir de pantalla completa (si está activa) o cerrar el juego (si ya está en modo ventana) |
| **`Enter`** | Comenzar o reintentar desde las pantallas de título / Game Over |

*(Si juegas temporalmente sin cámara, también dispones de respaldo por teclado: `←`/`→` o `A`/`D` para moverte, `1–4` para elegir hechizo, `Espacio` para disparar, `C` mantener/soltar para sobrecarga y `Shift Izq` para escudo.)*

---

## Recomendaciones Prácticas de Cámara e Iluminación

- **Distancia recomendada:** Colócate entre **60 cm y 100 cm** de la cámara de modo que tu rostro y ambas manos levantadas a la altura del pecho queden dentro del encuadre.
- **Iluminación frontal:** Prefiere luz suave frente a tu rostro y manos; evita ventanas o lámparas intensas justo detrás de ti (contraluz) que dificulten la detección de dedos y labios.
- **Postura cómoda:** Mantén los codos relajados cerca del torso y aprovecha cada pausa de **6 segundos de Meditación Arcana** para bajar los brazos.
- **Múltiples cámaras:** Si la cámara principal está ocupada o ves «Cámara no disponible», cierra otras apps de videollamada o prueba `--camara 1`.
