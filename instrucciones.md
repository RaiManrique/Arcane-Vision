Actúa como un ingeniero de software senior especializado en videojuegos arcade y visión computacional en tiempo real. Vamos a desarrollar desde cero el proyecto **"Arcane Vision: Duelo de Magos"** en Python usando **MediaPipe Tasks (`HandLandmarker` + `FaceLandmarker`)**, **OpenCV**, **Pygame** y **NumPy**.

Antes de escribir cualquier archivo de código, genera primero un **Implementation Plan** detallado con la lista de tareas y arquitectura modular para mi revisión. Una vez aprobado, ejecuta todo el desarrollo paso a paso.

### 1. Arquitectura y Requisitos Técnicos
- Estructura el proyecto en módulos limpios y desacoplados:
  1. `config.py`: Constantes de pantalla (1280x720 a 60 FPS), paleta cromática, definición de los 4 hechizos, umbrales biométricos, factores de suavizado y tiempos de oleada.
  2. `vision_engine.py`: Captura de webcam en modo espejo, descarga automática de los modelos oficiales `.task` de `hand_landmarker` y `face_landmarker` en una carpeta `models/` si no existen, ejecución en modo `VIDEO`, filtrado de suavizado exponencial (EMA) y confirmación por estabilidad de cuadros (*debounce*).
  3. `audio_fx.py`: Generación procedural de efectos de sonido en memoria con NumPy y Pygame Mixer (sin depender de archivos `.wav` o `.mp3` externos).
  4. `game_entities.py`: Clases para proyectiles normales y sobrecargados, proyectiles enemigos reflejables, rayos láser verticales telegrafiados, sistema de partículas, textos flotantes y los 5 arquetipos de enemigos.
  5. `main.py`: Bucle principal, gestión de oleadas, renderizado del fondo de cámara con baja opacidad, círculos rúnicos sobre las manos y HUD.
  6. `requirements.txt` y `README.md`.
- Todos los gráficos, círculos mágicos, escudos, enemigos y efectos deben ser procedurales/vectoriales en Pygame para garantizar que el juego funcione inmediatamente sin depender de sprites externos.

### 2. Mecánicas de Visión Computacional
- **Selección de Hechizos (Mano Dominante):** Contar dedos extendidos (`1` a `4`) usando distancias relativas respecto a la muñeca (invariante a la inclinación de la mano):
  - `1 dedo`: Rayo Arcano (Azul, rápido).
  - `2 dedos`: Orbe Ígneo (Naranja, daño alto).
  - `3 dedos`: Espinas Esmeralda (Verde, disparo triple en abanico).
  - `4 dedos`: Tormenta Voltaica (Violeta, velocidad y daño críticos).
- **Conjuración y Disparo (Boca + Mano Dominante):**
  - Al abrir la boca (combinando el blendshape `jawOpen` y la relación geométrica de labios MAR), el círculo mágico de la mano crece y acumula carga.
  - Al cerrar la boca tras superar el umbral de carga, se libera un proyectil gigante sobrecargado que perfora enemigos y rompe cualquier escudo elemental.
  - Si la boca está cerrada y se abre la palma completa (`5 dedos`), se lanzan disparos básicos rápidos del hechizo seleccionado con asistencia suave de puntería hacia enemigos cercanos.
- **Escudo Deflector Angular (Mano Secundaria):** Al abrir la palma de la segunda mano se activa una barrera de energía cuya inclinación rota según el ángulo entre los nudillos índice y meñique, permitiendo rebotar proyectiles enemigos de vuelta hacia ellos.
- **Esquive Lateral (Inclinación de Cabeza):** Calcular el ángulo de balanceo (*roll*) entre ambos ojos para mover horizontalmente el avatar del mago en la parte inferior y esquivar ataques verticales.
- **Soporte para Zurdos:** Incluir la tecla `H` para intercambiar dinámicamente cuál mano ataca y cuál sostiene el escudo.

### 3. Diseño de Enemigos y Progresión Anti-Fatiga
- Implementa 5 arquetipos con identidad visual clara:
  1. *Espectro Errante*: Enemigo básico de descenso lineal.
  2. *Centinela Rúnico*: Rodeado por un anillo elemental de color con un número (`1` a `4`) visible en su centro; solo recibe daño si se rompe su escudo con el hechizo de esa cantidad de dedos o con un disparo sobrecargado.
  3. *Invocador Ígneo*: Se detiene a media pantalla y dispara orbes rojos que deben devolverse con el escudo angular.
  4. *Enjambre Etéreo*: Grupos rápidos en zigzag con poca vida.
  5. *Señor del Vacío (Jefe, Oleada 5+)*: Gran resistencia, escudo elemental, ráfagas triples y rayos láser verticales con línea roja de advertencia previa de 1.4 segundos.
- Las oleadas duran 35 segundos y se intercalan con pausas automáticas de **6 segundos ("Meditación Arcana")** donde el jugador recupera salud y puede bajar los brazos para evitar fatiga física.

### 4. Entregable de Documentación (`README.md`)
Redacta un `README.md` completo y bien estructurado en español que incluya:
- Descripción general y lore breve del juego.
- Tabla de controles biométricos (gesto, acción y efecto) y guía del Grimorio de 4 hechizos.
- Descripción de los 5 arquetipos de enemigos y cómo derrotarlos.
- Instrucciones claras de instalación en entorno virtual (Windows y Linux/macOS) y ejecución.
- Recomendaciones prácticas de distancia a la cámara, iluminación frontal y atajos de teclado (`H`, `R`, `ESC`).

### 5. Verificación Final
Crea el entorno virtual, instala las dependencias, verifica que no existan errores de sintaxis ni importación en ningún módulo y comprueba la inicialización de los detectores de MediaPipe.