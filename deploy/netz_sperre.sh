#!/bin/bash
# NETZ_AGENT Q4: Heimnetz-Sperre fuer den Container luna-netz (Netz luna-netz-isoliert, 172.30.99.0/24).
# Der Container darf ins Internet, aber an keine private Adresse (Fritz!Box, NAS, MACO470, andere Container).
#   an      Regeln setzen (mehrfach aufrufbar, setzt nichts doppelt)
#   aus     Regeln entfernen (Rueckweg)
#   status  Regeln anzeigen
# Laeuft als root auf der NAS (sudo bzw. DSM-Aufgabenplaner beim Hochfahren). Wartet bis zu 5 min auf Docker.
set -u
NETZ=172.30.99.0/24
KETTE=LUNA-NETZ
PRIVAT="10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 169.254.0.0/16 100.64.0.0/10 127.0.0.0/8 224.0.0.0/4"
IPT=/sbin/iptables

weg() {   # Sprung aus einer Kette entfernen -- hoechstens 10 Versuche, nur solange er per -C da ist (BF-78: keine offene Schleife)
  for _ in 1 2 3 4 5 6 7 8 9 10; do $IPT -C "$1" -s $NETZ -j $KETTE 2>/dev/null || return 0; $IPT -D "$1" -s $NETZ -j $KETTE 2>/dev/null; done
}

an() {
  for _ in $(seq 60); do $IPT -L DOCKER-USER -n >/dev/null 2>&1 && break; sleep 5; done
  if ! $IPT -L DOCKER-USER -n >/dev/null 2>&1; then echo "FEHLER: Kette DOCKER-USER fehlt (Docker nicht gestartet?)"; exit 1; fi
  $IPT -N $KETTE 2>/dev/null
  $IPT -F $KETTE
  for z in $PRIVAT; do $IPT -A $KETTE -d "$z" -j DROP || exit 1; done   # DROP: Synology-Kernel hat kein REJECT (BF-75)
  $IPT -C DOCKER-USER -s $NETZ -j $KETTE 2>/dev/null || $IPT -I DOCKER-USER 1 -s $NETZ -j $KETTE   # Weiterleitung (LAN, andere Container)
  weg FORWARD                                                                                         # BF-76: in FORWARD ganz nach oben,
  $IPT -I FORWARD 1 -s $NETZ -j $KETTE                                                                # vor die ACCEPT-Regeln von Docker/DSM
  $IPT -C INPUT -s $NETZ -j $KETTE 2>/dev/null || $IPT -I INPUT 1 -s $NETZ -j $KETTE               # NAS selbst
  n=$($IPT -S $KETTE | grep -c -- "-j DROP")
  if [ "$n" -ne "$(echo $PRIVAT | wc -w)" ]; then echo "FEHLER: nur $n Sperrregeln gesetzt"; exit 1; fi
  echo "Heimnetz-Sperre fuer luna-netz aktiv ($n Sperrregeln)."
}

aus() {
  weg DOCKER-USER; weg INPUT; weg FORWARD
  $IPT -F $KETTE 2>/dev/null; $IPT -X $KETTE 2>/dev/null
  echo "Heimnetz-Sperre fuer luna-netz entfernt."
}

status() {
  $IPT -L $KETTE -n 2>/dev/null || echo "Kette $KETTE fehlt"
  echo "DOCKER-USER: $($IPT -S DOCKER-USER 2>/dev/null | grep -c " $KETTE")  INPUT: $($IPT -S INPUT 2>/dev/null | grep -c " $KETTE")  FORWARD: $($IPT -S FORWARD 2>/dev/null | grep -c " $KETTE")"
  echo "FORWARD (erste Regeln):"; $IPT -S FORWARD 2>/dev/null | sed -n 2,8p
}

case "${1:-}" in
  an) an ;; aus) aus ;; status) status ;;
  *) echo "Aufruf: $0 an|aus|status"; exit 2 ;;
esac
