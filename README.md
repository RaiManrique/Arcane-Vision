# Arcane Vision: Duelo de Magos

Juego arcade de acción mágica controlado en tiempo real por **visión computacional**, construido con **Python 3.14**, **MediaPipe Tasks (`HandLandmarker` + `FaceLandmarker`)**, **OpenCV**, **Pygame-CE** y **NumPy**. Todos los gráficos, círculos rúnicos, enemigos y efectos de sonido se generan proceduralmente sin depender de sprites ni archivos de audio externos.

---

## Historia y Lore

En la bóveda astral del *Observatorio de Aethel*, una fisura del Vacío amenaza con consumir los sellos que protegen el plano mortal. Como último **Arcanista del Espejo**, canalizas magia elemental directamente con tus manos, concentras energía rúnica mediante el aliento arcano y desvías las llamas infernales con una barrera prismática mientras esquivas los haces del **Señor del Vacío**.

---

## Controles Biométricos

| Gesto | Parte del cuerpo | Acción | Efecto en el juego |
| --- | --- | --- | --- |
| Mostrar **1 a 4 dedos** | Mano dominante | Selección de hechizo | Cambia el hechizo activo del Grimorio (conteo relativo a la muñeca, invariante a la inclinación) mientras el ataque esté desbloqueado. |
| **Cerrar el puño (`0 dedos`)** | Mano dominante | Bloquear / Desbloquear ataque | Alterna el candado del hechizo actual para evitar cambios accidentales al abrir la mano para disparar. |
| Abrir la **palma (`5 dedos`, o `4–5` si está bloqueado)** | Mano dominante | Disparo rápido | Lanza proyectiles básicos del hechizo activo con asistencia suave de puntería. |
| **Abrir y cerrar la boca** (con Barra Especial al **100%**) | Rostro (`jawOpen` + MAR) + mano | Tiro Especial | Consume la Barra Especial y desata uno de los 2 ataques especiales según tu gesto (`3–5 dedos`: **Nova Dispersa** / `1–2 dedos`: **Lanza Titánica**). |
| Abrir la **palma** y rotar la muñeca | Mano secundaria | Escudo Deflector Angular | Despliega la barrera inclinable para rebotar orbes rojos. Consume su barra por tiempo, recupera lento al descansar y entra en **enfriamiento (*cooldown*)** si se agota por completo. |
| **Juntar ambas manos (gesto de oración)** | Ambas manos | Intercambiar manos | Intercambia dinámicamente qué mano lanza hechizos y cuál sostiene el escudo (repetible al separar y volver a juntar las manos, o con la tecla **`H`**). |
| **Inclinar la cabeza** a izquierda o derecha | Rostro (*roll* entre ojos) | Esquive lateral | Desplaza el avatar del mago en la franja inferior para evadir rayos láser y proyectiles. |

> **Zona de juego recortada con detección completa:** La arena jugable está enmarcada al centro (`x = 190..1090`), mientras que MediaPipe sigue rastreando el **100 % de tu cámara** con mapeo ampliado desde tu rango cómodo (`17 %..83 %`), permitiéndote alcanzar ambos bordes sin estirar los brazos fuera de cuadro.

---

## Grimorio de los 4 Hechizos

| Dedos | Hechizo | Color | Especialidad |
| :---: | --- | --- | --- |
| **1** | **Rayo Arcano** | Azul | Alta velocidad y cadencia ágil; ideal contra enemigos rápidos y escudos `1`. |
| **2** | **Orbe Ígneo** | Naranja | Proyectil grande de gran impacto y daño alto; ideal contra objetivos resistentes y escudos `2`. |
| **3** | **Espinas Esmeralda** | Verde | Disparo triple en abanico; excelente para barrer enjambres y romper escudos `3`. |
| **4** | **Tormenta Voltaica** | Violeta | Velocidad superior y altísima probabilidad de golpe crítico; ideal contra jefes y escudos `4`. |

---

## Sistema de Tiros Especiales (Barra 0–100%)

El ataque especial bucal ya no puede lanzarse de forma ilimitada: primero debes llenar la **Barra Especial al 100%** combatiendo (aciertos, eliminaciones, rupturas de escudo, reflejos con el escudo y recarga pasiva lenta). Al llegar al 100%, abre la boca para cargar y ciérrala para lanzar uno de los **2 tipos**:

| Tipo de Especial | Gesto (Modo Auto) / Atajo | Ideal contra | Efecto |
| --- | --- | --- | --- |
| **Nova Dispersa** | **3–5 dedos** al abrir la boca (o fijar con **`E`**) | Enemigos pequeños y dispersos (*Enjambre Etéreo*, múltiples *Espectros*) | Dispara **9 cometas buscadores** en abanico amplio que se reparten entre los objetivos en pantalla y rompen escudos. |
| **Lanza Titánica** | **1–2 dedos** al abrir la boca (o fijar con **`E`**) | Enemigos grandes y resistentes (*Centinela Rúnico*, *Invocador*, *Señor del Vacío*) | Proyectil gigante hiperconcentrado y **perforante** de altísimo daño que atraviesa la línea de combate y destruye cualquier escudo elemental. |

---

## Escudo Deflector con Barra Temporal y Enfriamiento

- **Uso por tiempo:** Mantener el escudo desplegado consume su barra de energía (~`4.0 s` de uso continuo).
- **Regeneración lenta:** Al cerrar la mano secundaria o bajar el brazo, la barra se restablece lentamente (~`11.5 %/s`) tras una breve pausa.
- **Enfriamiento (*Cooldown*):** Si gastas la barra hasta `0 %`, el escudo se sobrecalienta y queda bloqueado durante **`4.5 segundos`** antes de volver a estar disponible. Gestionarlo en ráfagas cortas te permite reflejar orbes sin quedar indefenso.

---

## Bestiario: 5 Arquetipos de Enemigos

1. **Espectro Errante:** Desciende en línea recta hacia la base del mago.
2. **Centinela Rúnico:** Protegido por un anillo elemental de color con un número visible (**`1`** a **`4`**) en su centro. Solo sufre daño al romper su escudo con el hechizo de ese número de dedos, con un ataque especial o con un orbe reflejado.
3. **Invocador Ígneo:** Desciende hasta media pantalla, se detiene y dispara orbes rojos reflejables con tu escudo angular (reflejarlos también carga rápido tu Barra Especial).
4. **Enjambre Etéreo:** Grupos rápidos con movimiento en zigzag y poca salud; excelentes blancos para **Espinas Esmeralda** o **Nova Dispersa**.
5. **Señor del Vacío (Jefe, Oleada 5+):** Gran resistencia, escudo elemental regenerable, ráfagas triples reflejables y **rayos láser verticales** anunciados por una línea roja pulsante durante **1.4 segundos**. Ideal para castigarlo con **Lanza Titánica**.

### Progresión Anti-Fatiga (*Meditación Arcana*)
Cada oleada dura **35 segundos** y se intercala automáticamente con una pausa de **6 segundos de Meditación Arcana**. Durante ese descanso se limpian las amenazas, tu salud se regenera, tu escudo se enfría y recarga, y puedes bajar ambos brazos para evitar fatiga física.

---

## Instalación y Ejecución

El proyecto está preparado para **Python 3.14** y las versiones más recientes de MediaPipe Tasks, OpenCV, Pygame-CE y NumPy. Los modelos oficiales `hand_landmarker.task` y `face_landmarker.task` se guardan en `models/` y se descargan automáticamente si faltan.

### Linux / macOS (con `uv` — recomendado)

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python main.py
```

### Linux / macOS (con `venv` y `pip`)

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

### Windows 11 (PowerShell)

```powershell
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

| Atajo | Acción |
| --- | --- |
| **`F11`** o **`Alt + Enter`** (o botón en el HUD) | Entrar o salir de **Pantalla Completa** |
| **`L`** (o **Puño** / clic en el candado) | Bloquear o desbloquear el tipo de ataque actual |
| **`E`** (o clic en el selector del HUD) | Alternar modo de Especial: **Auto (gesto)** / **Nova Dispersa** / **Lanza Titánica** |
| **`H`** | Intercambiar mano dominante / secundaria (**Diestro ↔ Zurdo**) |
| **`R`** | Reiniciar el duelo inmediatamente |
| **`M`** | Silenciar o reactivar el audio procedural |
| **`ESC`** | Salir de pantalla completa (si está activa) o cerrar el juego (si ya está en modo ventana) |
| **`Enter`** | Comenzar o reintentar desde las pantallas de título / Game Over |

*(Respaldo sin cámara: `←`/`→` o `A`/`D` para moverte, `1–4` para elegir hechizo si está desbloqueado, `Espacio` para disparar, `C` mantener/soltar para el tiro especial cuando la barra esté al 100%, y `Shift Izq` para escudo.)*

---

## Recomendaciones Prácticas de Cámara e Iluminación

- **Distancia recomendada:** Colócate entre **60 cm y 100 cm** de la cámara de modo que tu rostro y ambas manos levantadas a la altura del pecho entren completos en el encuadre.
- **Iluminación frontal:** Prefiere luz suave frente a tu rostro y manos; evita contraluz fuerte detrás de ti.
- **Tip para el puño de bloqueo:** Cierra bien los 5 dedos (incluyendo el pulgar) frente a la cámara durante una fracción de segundo hasta ver el candado dorado; luego podrás abrir y mover la mano libremente para disparar sin que cambie el hechizo.
