#!/bin/bash
# NETZ_AGENT Q4: Heimnetz-Sperre fuer den Container luna-netz.
# Der Container darf ins Internet, aber an keine private Adresse (Fritz!Box, NAS, MACO470, andere Container).
#   an      Regeln setzen (setzt nur neu, wenn sie fehlen -- fuer den DSM-Aufgabenplaner beim Hochfahren und alle paar Minuten)
#   aus     Regeln entfernen (Rueckweg)
#   status  Regeln anzeigen
# Laeuft als root auf der NAS. Wartet bis zu 5 min, bis der Container laeuft.
#
# Die Regeln sitzen IM Netz-Namensraum des Containers (Kette OUTPUT), nicht in den Ketten der NAS (BF-81): DSM baut seine
# eigenen Ketten bei Container-Starts und auch zwischendurch neu auf und wirft fremde Regeln hinaus (BF-79/BF-80). Im
# Container-Namensraum fasst DSM nichts an; der Container selbst kann sie nicht aendern (keine Rechte, cap_drop ALL).
# Startet der Container neu, ist der Namensraum neu und leer -> die naechste Ausfuehrung setzt die Regeln wieder; bis
# dahin nimmt der Netz-Agent keine Auftraege an (fail closed, `netz_agent/agent.py`).
set -u
NETZ=172.30.99.0/24
KETTE=LUNA-NETZ
PRIVAT="10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 169.254.0.0/16 100.64.0.0/10 127.0.0.0/8 224.0.0.0/4"
IPT=/sbin/iptables
DOCKER=/usr/local/bin/docker
NS=luna-netz

namensraum() {   # Netz-Namensraum des laufenden Containers unter /var/run/netns/luna-netz bereitstellen
  local pid=""
  for _ in $(seq 60); do
    pid=$($DOCKER inspect -f '{{.State.Pid}}' luna-netz 2>/dev/null)
    [ -n "$pid" ] && [ "$pid" != "0" ] && break
    sleep 5
  done
  if [ -z "$pid" ] || [ "$pid" = "0" ]; then echo "FEHLER: Container luna-netz laeuft nicht"; exit 1; fi
  mkdir -p /var/run/netns
  ln -sfn "/proc/$pid/ns/net" /var/run/netns/$NS
}

C() { ip netns exec $NS $IPT "$@"; }   # iptables im Container-Namensraum

alt_weg() {   # Stand vor BF-81 auf der NAS selbst aufraeumen (Filter- und mangle-Tabelle) -- ohne offene Schleifen (BF-78)
  local tab kette
  for tab in filter mangle; do
    for kette in DOCKER-USER INPUT FORWARD PREROUTING; do
      for _ in 1 2 3; do
        $IPT -t $tab -C $kette -s $NETZ -j $KETTE 2>/dev/null || break
        $IPT -t $tab -D $kette -s $NETZ -j $KETTE 2>/dev/null
      done
    done
    $IPT -t $tab -F $KETTE 2>/dev/null; $IPT -t $tab -X $KETTE 2>/dev/null
  done
}

aktiv() {   # Sprung da und alle Sperrregeln vorhanden?
  C -C OUTPUT -j $KETTE 2>/dev/null && [ "$(C -S $KETTE 2>/dev/null | grep -c -- "-j DROP")" -eq "$(echo $PRIVAT | wc -w)" ]
}

an() {
  namensraum
  alt_weg
  if aktiv; then echo "Heimnetz-Sperre fuer luna-netz bereits aktiv."; return 0; fi
  C -N $KETTE 2>/dev/null
  C -F $KETTE || exit 1
  C -A $KETTE -o lo -j RETURN || exit 1                                    # Docker-Namensdienst (127.0.0.11) bleibt
  for z in $PRIVAT; do C -A $KETTE -d "$z" -j DROP || exit 1; done        # DROP: Synology-Kernel hat kein REJECT (BF-75)
  C -C OUTPUT -j $KETTE 2>/dev/null || C -I OUTPUT 1 -j $KETTE || exit 1
  aktiv || { echo "FEHLER: Sperrregeln nicht vollstaendig gesetzt"; exit 1; }
  echo "Heimnetz-Sperre fuer luna-netz aktiv ($(echo $PRIVAT | wc -w) Sperrregeln im Container-Netz)."
}

aus() {
  alt_weg
  namensraum
  for _ in 1 2 3; do C -C OUTPUT -j $KETTE 2>/dev/null || break; C -D OUTPUT -j $KETTE; done
  C -F $KETTE 2>/dev/null; C -X $KETTE 2>/dev/null
  echo "Heimnetz-Sperre fuer luna-netz entfernt."
}

status() {
  namensraum
  C -L $KETTE -n -v 2>/dev/null || echo "Kette $KETTE fehlt"
  echo "OUTPUT (Container-Netz):"; C -S OUTPUT 2>/dev/null | sed -n 1,6p
}

case "${1:-}" in
  an) an ;; aus) aus ;; status) status ;;
  *) echo "Aufruf: $0 an|aus|status"; exit 2 ;;
esac
