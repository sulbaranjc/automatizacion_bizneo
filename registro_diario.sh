#!/usr/bin/env bash
# Lanzador desatendido de bizneo_registrar_horario.py (lo llama el temporizador systemd).
# Registra los últimos 4 días hasta ayer (el script salta lo ya correcto, así que repetir no hace daño).
# Deja log en ~/.local/state/bizneo/ y avisa por notificación de escritorio si algo falla.
DIR="$(cd "$(dirname "$0")" && pwd)"
ESTADO="$HOME/.local/state/bizneo"
LOG="$ESTADO/registro.log"
mkdir -p "$ESTADO"

exec 9>"$ESTADO/registro.lock"
flock -n 9 || { echo "$(date '+%F %T') ya hay una ejecución en curso" >> "$LOG"; exit 0; }

notificar() { notify-send -a "Bizneo" -u "${3:-normal}" "$1" "$2" 2>/dev/null || true; }

# Tras el arranque la red puede tardar: esperar hasta 2 min a que responda Bizneo.
for _ in $(seq 12); do
    curl -s -o /dev/null --max-time 5 https://ilerna.bizneohr.com && break
    sleep 10
done

# Hasta 3 intentos (tras el arranque la red puede cambiar a mitad, p. ej. ERR_NETWORK_CHANGED).
# La sesión caducada (rc 2) no se reintenta: no se arregla sola.
for INTENTO in 1 2 3; do
    SALIDA="$(timeout 900 "$DIR/.venv/bin/python" "$DIR/bizneo_registrar_horario.py" --ultimos 4 --headless --aplicar 2>&1)"
    RC=$?
    [ $RC -eq 0 ] || [ $RC -eq 2 ] && break
    { echo "=== $(date '+%F %T') intento $INTENTO fallido (rc=$RC)"; echo "$SALIDA" | tail -3; } >> "$LOG"
    [ $INTENTO -lt 3 ] && sleep 60
done

{ echo "=== $(date '+%F %T') rc=$RC"; echo "$SALIDA"; echo; } >> "$LOG"
echo "$(date '+%F %T') rc=$RC" > "$ESTADO/ultima_ejecucion"

case $RC in
    0) N=$(grep -c '✔ guardado' <<<"$SALIDA")
       [ "$N" -gt 0 ] && notificar "Bizneo: horas registradas" "$N día(s) registrados correctamente." ;;
    2) notificar "Bizneo: sesión caducada" "Ejecuta biz-registrar (sin --headless) para volver a iniciar sesión." critical ;;
    *) notificar "Bizneo: error al registrar" "Revisa $LOG" critical ;;
esac
exit $RC
