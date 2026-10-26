#!/bin/bash
# NETZ_AGENT Q4: Heimnetz-Sperre fuer den Container luna-netz (Netz luna-netz-isoliert, 172.30.99.0/24).
# Der Container darf ins Internet, aber an keine private Adresse (Fritz!Box, NAS, MACO470, andere Container).
#   an      Regeln setzen (mehrfach aufrufbar, setzt nichts doppelt)
#   aus     Regeln entfernen (Rueckweg)
#   status  Regeln anzeigen
# Laeuft als root auf der NAS (sudo bzw. DSM-Aufgabenplaner beim Hochfahren UND alle paar Minuten -- DSM wirft die
# Regel bei Container-Starts raus, BF-80). Setzt nur neu, wenn sie fehlt. Wartet bis zu 5 min auf Docker.
#
# Die Sperre sitzt in der Tabelle `mangle`, Kette PREROUTING (BF-79): sie sieht jedes Paket aus dem Container, bevor
# entschieden wird, ob es an die NAS selbst geht oder weitergeleitet wird. Die Filter-Ketten INPUT/FORWARD sind auf
# der Synology umgebogen (DSM-iptables schreibt `FORWARD` nach `DEFAULT_FORWARD`) und greifen nicht verlaesslich.
set -u
NETZ=172.30.99.0/24
KETTE=LUNA-NETZ
PRIVAT="10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 169.254.0.0/16 100.64.0.0/10 127.0.0.0/8 224.0.0.0/4"
IPT=/sbin/iptables
M="$IPT -t mangle"

weg() {   # Sprung entfernen -- hoechstens 10 Versuche, nur solange `-C` ihn findet (BF-78: keine offene Schleife)
  local tab=$1 kette=$2
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    $IPT -t "$tab" -C "$kette" -s $NETZ -j $KETTE 2>/dev/null || return 0
    $IPT -t "$tab" -D "$kette" -s $NETZ -j $KETTE 2>/dev/null
  done
}

alt_weg() {   # Stand vor BF-79 (Filter-Tabelle) aufraeumen
  weg filter DOCKER-USER; weg filter INPUT; weg filter FORWARD
  $IPT -F $KETTE 2>/dev/null; $IPT -X $KETTE 2>/dev/null
}

aktiv() {   # Sprung da und alle Sperrregeln vorhanden?
  $M -C PREROUTING -s $NETZ -j $KETTE 2>/dev/null && [ "$($M -S $KETTE 2>/dev/null | grep -c -- "-j DROP")" -eq "$(echo $PRIVAT | wc -w)" ]
}

an() {
  if aktiv; then echo "Heimnetz-Sperre fuer luna-netz bereits aktiv."; return 0; fi   # BF-80: alle paar Minuten aufgerufen
  for _ in $(seq 60); do $IPT -L DOCKER-USER -n >/dev/null 2>&1 && break; sleep 5; done   # erst wenn Docker laeuft
  alt_weg
  $M -N $KETTE 2>/dev/null
  $M -F $KETTE || exit 1
  for z in $PRIVAT; do $M -A $KETTE -d "$z" -j DROP || exit 1; done   # DROP: Synology-Kernel hat kein REJECT (BF-75)
  $M -C PREROUTING -s $NETZ -j $KETTE 2>/dev/null || $M -I PREROUTING 1 -s $NETZ -j $KETTE || exit 1
  n=$($M -S $KETTE | grep -c -- "-j DROP")
  if [ "$n" -ne "$(echo $PRIVAT | wc -w)" ]; then echo "FEHLER: nur $n Sperrregeln gesetzt"; exit 1; fi
  echo "Heimnetz-Sperre fuer luna-netz aktiv ($n Sperrregeln, mangle/PREROUTING)."
}

aus() {
  alt_weg
  weg mangle PREROUTING
  $M -F $KETTE 2>/dev/null; $M -X $KETTE 2>/dev/null
  echo "Heimnetz-Sperre fuer luna-netz entfernt."
}

status() {
  $M -L $KETTE -n -v 2>/dev/null || echo "Kette $KETTE fehlt"
  echo "PREROUTING (mangle, erste Regeln):"; $M -S PREROUTING 2>/dev/null | sed -n 1,6p
}

case "${1:-}" in
  an) an ;; aus) aus ;; status) status ;;
  *) echo "Aufruf: $0 an|aus|status"; exit 2 ;;
esac
