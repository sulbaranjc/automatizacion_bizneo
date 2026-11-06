## Nuevo script: `bizneo_registrar_horario.py` (06/11/2026)

Sustituye en la práctica a `biz-cargar-dia` / `biz-cargar-semana`: **no usa horarios fijos en el código**. Lee el horario esperado de cada día directamente de Bizneo («Mis fichajes») y registra exactamente esos tramos.

### Qué hace, día por día

1. Abre el mes (`?month=M&year=Y`) y lee la fila del día: columna **Esperado** (p. ej. `13:35-14:30 15:55-21:00`), **Registrado**, **Total**, **Balance** e icono de incidencia «Sobra tiempo».
2. Si no hay horario esperado (fin de semana, descanso, festivo) → no toca nada. Si ese día hay horas registradas, lo marca como `REVISAR` y **no** las borra.
3. Si el día ya está bien (Balance `00:00`, sin «Sobra tiempo», primer inicio y último fin coinciden) → lo salta (idempotente: se puede relanzar sin riesgo).
4. Si hay que arreglarlo: abre el formulario del día, deja **un tramo por turno** (pulsa «Añadir tramo» si falta), elige ese turno en el desplegable del tramo, escribe hora de inicio y de fin en las cajas de hora/minutos.
5. **Comprueba antes de guardar** que los campos tienen lo que se pretendía; si no, aborta ese día sin guardar.
6. Pulsa «Guardar», **recarga el mes** y verifica que el Balance es `00:00` y no hay «Sobra tiempo». Informa ✔ o ⚠/✘.

### Uso

Por defecto **solo simula** (no escribe nada). `--aplicar` guarda de verdad.

```bash
cd /mnt/DocumentosJC/ILERNA/Hermamientas/automatizacion_bizneo
.venv/bin/python bizneo_registrar_horario.py --desde 2026-10-01 --hasta 2026-10-31            # simulación
.venv/bin/python bizneo_registrar_horario.py --desde 2026-10-01 --hasta 2026-10-31 --aplicar  # escribe
.venv/bin/python bizneo_registrar_horario.py --fecha 2026-11-06 --aplicar                     # un día
```

| Argumento | Significado |
|---|---|
| `--fecha` | Un solo día (`YYYY-MM-DD`) |
| `--desde` / `--hasta` | Rango; `--hasta` por defecto = ayer; `--desde` por defecto = ayer |
| `--aplicar` | Guardar de verdad (sin él, simulación) |

Salida: `= ya correcto`, `→ <tramos>` + `✔ guardado`, `⚠ guardado pero revisar`, `✘ error`, `REVISAR` (horas sin horario esperado). Código de salida 1 si hubo errores.

Alias (creado el 06/11/2026 en `~/.bash_aliases`): `biz-registrar` → `.venv/bin/python bizneo_registrar_horario.py`. Ej.: `biz-registrar --desde 2026-11-01 --hasta 2026-11-30` (simula) y añadir `--aplicar` para escribir.

### Alcance y límites

- **Hace:** crear y modificar registros de tiempo de días con horario esperado; corregir tramos mal enlazados a su turno; verificar el resultado leyendo Bizneo.
- **NO hace (a propósito):** borrar registros. Los días con horas pero sin horario esperado solo se avisan. El borrado masivo («Eliminar horario registrado») es irreversible y lo decide el usuario.
- **No** registra el día en curso por defecto (`--hasta` = ayer).
- Si un día tiene **más tramos que turnos**, aborta ese día («revisar a mano»); no sabe eliminar tramos.
- Requiere sesión de Bizneo: usa `session.json`; si caducó, abre Chromium y espera hasta 3 min a que el usuario inicie sesión con Google (el asistente nunca introduce credenciales). **No cerrar la ventana** mientras corre.
- **Sesión persistente (heredada de los scripts antiguos):** reutiliza `session.json` sin pedir login. Novedad: la **renueva en cada ejecución** (`storage_state` se guarda siempre que la tabla carga, no solo tras un login manual), por lo que la sesión caduca mucho menos. El login de Google solo se pide cuando la sesión ya expiró (el `session.json` de junio estaba caducado; se renovó el 06/11/2026).
- Va con `headless=False` (ventana visible).

### Mecánica de Bizneo descubierta (importante para mantenerlo)

| Hallazgo | Consecuencia en el código |
|---|---|
| «Mi horario» es una plantilla semanal de RRHH, solo lectura. El botón «Registrar horario» **no** carga horas: deja las horas vacías y solo deja el horario como referencia | Hay que teclear inicio y fin siempre |
| La fila `tr.log-info-row[data-bulk-element="YYYY-MM-DD"]` se expande con htmx en `tr#form-YYYY-MM-DD` | Se abre con un clic en la fila |
| Columnas de la fila: `[2]` Horario, `[3]` Esperado, `[4]` Registrado, `[5]` Total, `[6]` Balance, icono `.huge-stop-watch-stroke-rounded` = «Sobra tiempo» | `leer_fila()` |
| Las horas visibles son **dos `input[type=number]`** (hora y minutos) dentro de `div.start`/`div.end` → `.timepicker`. El `input[name$="[start_at]"]` es un **respaldo oculto** que rellena el widget | Escribir en las cajas numéricas + `Tab`; **nunca** en el input de texto (en tramos nuevos no surte efecto) |
| Un tramo nuevo («Añadir tramo») **hereda como inicio el fin del anterior** | Hay que sobrescribirlo y verificarlo |
| Elegir turno en el desplegable `shift_id` reescribe las horas del tramo | Esperar ~1 s tras `select_option` y teclear después |
| Los registros antiguos sin turno asociado **no muestran** el desplegable (solo un `hidden` vacío) | Si no hay `select`, se escriben solo las horas |
| Etiquetas del desplegable con formatos distintos: `13:35 a 14:30`, `8:30 a 21h`, `08:30 - 14:30`, `20:05-21:00` | Regex `ETIQUETA_RE` normaliza a `HH:MM` |
| Tras «Guardar» el formulario no siempre desaparece | Verificar recargando el mes, no esperando a que cierre |
| `page.locator("body").click()` cae sobre otra fila y abre su formulario, tapando el actual | **No usarlo**; desenfocar con `Tab` |
| El Balance solo compara **totales**, no horas: un día puede estar a `00:00` con horas equivocadas o con «Sobra tiempo» | Comprobar también el icono y el primer inicio/último fin |
| Columna «Registrado» muestra solo primer inicio–último fin (`13:35-21:00`), aunque haya hueco entre tramos | No sirve para validar huecos; `Total` sí |

### Qué se modificó en Bizneo (06/11/2026)

**Octubre 2026** (todo el mes tenía placeholders `08:30-14:30` de scripts anteriores y los días 27-30 vacíos):

| Día | Antes | Después |
|---|---|---|
| Vie 2, 9, 16, 23, 30 | `08:30-14:30` / vacío (bal. −6:30 / −12:30) | `08:30-21:00` (12:30), bal. 00:00 |
| Lun 5, 19, 26 | `08:30-14:30` | `08:30-14:30` + `20:05-21:00` (6:55), bal. 00:00 |
| Mar 6, 13, 20, 27 | `08:30-14:30` / vacío | `11:45-21:00` (9:15), bal. 00:00 |
| Mié 7, 14, 21, 28 | `08:30-14:30` / vacío | `13:35-14:30` + `15:55-21:00` (6:00), bal. 00:00 |

Resultado: 18 días laborables a `00:00`, sin «Sobra tiempo»; 144 h 15 min registradas.
**Pendiente:** jueves 8, 15, 22 y 29 tenían 6:00 registradas sin horario esperado (+6:00). El usuario borró a mano uno (el 8); a 06/11 siguen 15, 22 y 29 (el script solo los avisa como `REVISAR`; el borrado lo hace el usuario).

**Noviembre 2026** (hasta el 5/11): mié 4 → corregido el 2.º tramo, que estaba enlazado al turno «13:35 a 14:30» (causaba «Sobra tiempo» con balance 00:00); ahora `13:35-14:30` + `15:55-21:00`. Mar 3 ya estaba bien. Lun 2 (festivo Todos los Santos) y jue 5 sin registros. **Vie 6 sin registrar** (el día en curso no se carga por defecto).

### Incidencias durante el desarrollo (lecciones)

1. **Tramos duplicados/erróneos en 19, 21 y 26 oct** (balances +5:35 / +6:30): la 1.ª versión escribía en el input oculto y el 2.º tramo heredó inicio 14:30. Corregido tras descubrir las cajas numéricas.
2. **Clic en `body`** abría otra fila y el botón «Guardar» no aparecía (timeouts de 30 s). Eliminado.
3. **Selección de turno antes de teclear** pisaba la hora (`08:35` en vez de `13:35`): se añadió espera de 1 s.
4. **Comprobación previa al guardado** añadida precisamente para que ningún día se guarde con horas distintas de las esperadas.
5. Sesión caducada y ventana cerrada por el usuario durante el login → el script fallaba con «Target closed»; no se escribió nada.

### Estado git

Commit `d8bd48c` (06/11/2026) subido a https://github.com/sulbaranjc/automatizacion_bizneo (repo **público**; `session.json` y `.venv` están en `.gitignore` y nunca estuvieron en el historial).

### Ejecución automática diaria (desde 06/11/2026)

Un temporizador de **systemd de usuario** lanza el script solo, sin Claude ni ventana:

| Pieza | Detalle |
|---|---|
| `bizneo-registro.timer` | `~/.config/systemd/user/`; `OnCalendar=*-*-* 10:00:00`, **`Persistent=true`** |
| `bizneo-registro.service` | `oneshot` → ejecuta `registro_diario.sh` |
| `registro_diario.sh` | (en el repo) espera hasta 2 min a que haya red, bloquea ejecuciones simultáneas (`flock`), lanza `bizneo_registrar_horario.py --ultimos 4 --headless --aplicar` (timeout 15 min), escribe el log y notifica |
| Log | `~/.local/state/bizneo/registro.log` (cada ejecución con fecha y `rc`) |
| Estado | `~/.local/state/bizneo/ultima_ejecucion` (`fecha rc=N`) |

**Comportamiento:**
- A las 10:00 registra los **últimos 4 días hasta ayer**. Es idempotente: lo ya correcto se salta; fines de semana/festivos no registran nada.
- **Si la laptop estaba apagada a las 10:00**, `Persistent=true` lanza la ejecución **automáticamente al encenderla** (y los 4 días de margen cubren un fin de semana entero apagada). No hace falta abrir Claude.
- Notificación de escritorio: «horas registradas» (si guardó algo), «sesión caducada» (rc 2) o «error» (rc ≠ 0).
- **Sesión caducada** en modo `--headless`: no espera login; sale con código 2 y `SESION_CADUCADA`. Solución: ejecutar `biz-registrar` (sin `--headless`) y hacer login con Google una vez.
- Argumentos nuevos del script: `--headless` y `--ultimos N`.

**Comandos útiles:**

```bash
systemctl --user list-timers bizneo-registro.timer     # próxima ejecución
systemctl --user start bizneo-registro.service         # lanzarlo ya (prueba)
tail -30 ~/.local/state/bizneo/registro.log            # ver qué hizo
cat ~/.local/state/bizneo/ultima_ejecucion             # última ejecución y resultado
systemctl --user disable --now bizneo-registro.timer   # desactivar
```

**Límites:** requiere la laptop encendida y la sesión de usuario iniciada (el temporizador es de usuario, sin `linger`). Pruebas del 06/11/2026: ejecución real vía systemd → rc 0 y log correcto; sesión falsa → rc 2 con mensaje. Primera ejecución programada: sábado 07/11/2026 10:00 (registra el viernes 06/11).
