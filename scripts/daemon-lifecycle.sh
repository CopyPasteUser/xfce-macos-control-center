#!/usr/bin/env bash
# Sourced by install/update/uninstall scripts. Only identifies Python processes
# whose actual script argument basename is exactly macos-control-center.

cc_process_alive() {
    local pid="$1" state
    [[ "$pid" =~ ^[0-9]+$ ]] || return 1
    [[ -r "/proc/$pid/status" ]] || return 1
    state=$(awk '$1 == "State:" { print $2; exit }' "/proc/$pid/status" 2>/dev/null || true)
    [[ -n "$state" && "$state" != "Z" ]]
}

cc_is_control_center_process() {
    local pid="$1" owner exe script
    local -a argv=()
    [[ "$pid" =~ ^[0-9]+$ && -r "/proc/$pid/status" && -r "/proc/$pid/cmdline" ]] || return 1
    owner=$(awk '$1 == "Uid:" { print $2; exit }' "/proc/$pid/status" 2>/dev/null || true)
    [[ "$owner" == "$EUID" ]] || return 1
    mapfile -d '' -t argv < "/proc/$pid/cmdline" 2>/dev/null || true
    ((${#argv[@]} >= 2)) || return 1
    exe="${argv[0]##*/}"
    script="${argv[1]##*/}"
    [[ "$script" == "macos-control-center" ]] || return 1
    case "$exe" in
        python|python[0-9]*|pypy|pypy[0-9]*) return 0 ;;
        *) return 1 ;;
    esac
}

cc_stop_control_center_instances() {
    local proc pid owner i running
    local -a pids=()
    local pidfile="${XDG_RUNTIME_DIR:-/tmp}/macos-control-center.pid"
    local statefile="$pidfile.state.json"

    # Search /proc rather than trusting a potentially stale PID file. This also
    # catches an older daemon launched from a checkout instead of the install path.
    for proc in /proc/[0-9]*; do
        [[ -r "$proc/status" && -r "$proc/cmdline" ]] || continue
        pid="${proc##*/}"
        [[ "$pid" == "$$" || "$pid" == "$PPID" ]] && continue
        cc_is_control_center_process "$pid" || continue
        pids+=("$pid")
    done

    for pid in "${pids[@]}"; do
        if cc_process_alive "$pid"; then
            printf 'Beende laufende Control-Center-Instanz (PID %s) …\n' "$pid"
            kill -TERM "$pid" 2>/dev/null || true
        fi
    done

    for pid in "${pids[@]}"; do
        for i in $(seq 1 40); do
            cc_process_alive "$pid" || break
            sleep 0.1
        done
        if cc_process_alive "$pid"; then
            if cc_is_control_center_process "$pid"; then
                printf 'FEHLER: Control Center (PID %s) beendet sich nicht; Update wird abgebrochen.\n' "$pid" >&2
                return 1
            fi
        fi
    done

    # Remove only our dedicated stale PID file. Never overwrite one that points
    # to a still-running unrelated process.
    if [[ -e "$pidfile" ]]; then
        pid=$(cat "$pidfile" 2>/dev/null || true)
        if [[ "$pid" =~ ^[0-9]+$ ]] && cc_process_alive "$pid"; then
            if cc_is_control_center_process "$pid"; then
                printf 'FEHLER: Alte Control-Center-Instanz (PID %s) ist noch aktiv.\n' "$pid" >&2
                return 1
            fi
            printf 'FEHLER: PID-Datei %s verweist auf einen fremden aktiven Prozess (PID %s); unverändert gelassen.\n' "$pidfile" "$pid" >&2
            return 1
        fi
        rm -f -- "$pidfile"
    fi
    # State metadata is dedicated to this application and may be stale after an
    # old process exited via SIGTERM before its Python finally-block ran.
    rm -f -- "$statefile"
    return 0
}

cc_start_and_show_control_center() {
    local app="$1" app_root="$2"
    local pidfile="${XDG_RUNTIME_DIR:-/tmp}/macos-control-center.pid"
    local statefile="$pidfile.state.json"
    local log="$app_root/logs/daemon.log"
    local expected_version expected_script launched_pid candidate i ready=0 has_daemon arg
    local -a argv=()
    expected_version=$(cat "$app_root/app/VERSION" 2>/dev/null || true)
    expected_script=$(readlink -f -- "$app" 2>/dev/null || printf '%s' "$app")
    [[ -n "$expected_version" ]] || { echo "FEHLER: installierte VERSION-Datei fehlt." >&2; return 1; }

    [[ -x "$app" ]] || { echo "FEHLER: Programm fehlt oder ist nicht ausführbar: $app" >&2; return 1; }
    mkdir -p "$app_root/logs"
    chmod 700 "$app_root/logs"
    touch "$log"
    chmod 600 "$log"
    rm -f -- "$pidfile" "$statefile"

    echo "Starte installierte Version $expected_version als Resident-Daemon …"
    CC_PIDFILE="$pidfile" CC_STATEFILE="$statefile" nohup "$app" --daemon >>"$log" 2>&1 </dev/null &
    launched_pid=$!

    # The app registers SIGUSR1 with GLib before publishing its PID, but publishes
    # the runtime state only from an idle callback after Gtk.main() is running.
    # This wait ensures the signal is handled by a live main loop, not lost during UI construction.
    for i in $(seq 1 100); do
        if [[ -r "$pidfile" ]]; then
            candidate=$(cat "$pidfile" 2>/dev/null || true)
            if [[ "$candidate" =~ ^[0-9]+$ ]] && cc_process_alive "$candidate" && cc_is_control_center_process "$candidate"; then
                mapfile -d '' -t argv < "/proc/$candidate/cmdline" 2>/dev/null || true
                has_daemon=0
                for arg in "${argv[@]}"; do
                    if [[ "$arg" == "--daemon" ]]; then has_daemon=1; break; fi
                done
                if [[ "$has_daemon" -eq 1 && -r "$statefile" ]] \
                  && grep -Fq '"pid": '"$candidate" "$statefile" \
                  && grep -Fq '"version": "'"$expected_version"'"' "$statefile" \
                  && grep -Fq '"script": "'"$expected_script"'"' "$statefile"; then
                    ready=1
                    break
                fi
            fi
        fi
        if ! cc_process_alive "$launched_pid"; then break; fi
        sleep 0.1
    done

    if [[ "$ready" -ne 1 ]]; then
        echo "FEHLER: Der neue Daemon wurde nicht bereit. Letzte Startmeldungen:" >&2
        tail -40 "$log" >&2 2>/dev/null || true
        return 1
    fi

    if [[ "${3:-show}" == "hidden" ]]; then
        echo "Neue Version $expected_version läuft als versteckter Daemon (PID $candidate)."
        echo "Diagnoselog: $log"
        return 0
    fi
    if kill -USR1 "$candidate" 2>/dev/null; then
        echo "Neue Version $expected_version läuft (PID $candidate) und wurde geöffnet."
        echo "Runtime-Status: $statefile"
        echo "Diagnoselog: $log"
        return 0
    fi
    echo "FEHLER: Daemon läuft, aber das Öffnungssignal konnte nicht gesendet werden." >&2
    tail -30 "$log" >&2 2>/dev/null || true
    return 1
}
