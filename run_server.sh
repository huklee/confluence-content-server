#!/usr/bin/env bash
set -euo pipefail

host="${HOST:-127.0.0.1}"
port="${PORT:-8000}"
reload=0
dry_run=0
plantuml_jar="${PLANTUML_JAR:-}"

usage() {
  cat <<'USAGE'
Usage: ./run_server.sh [OPTIONS]

Run the local Confluence preview server.

Options:
  -H, --host HOST          Bind host (default: 127.0.0.1 or $HOST)
  -p, --port PORT          TCP port (default: 8000 or $PORT)
  -r, --reload             Restart when source files change
      --plantuml-jar PATH  Local PlantUML jar (or set $PLANTUML_JAR)
      --dry-run            Print the resolved command without starting it
  -h, --help               Show this help

Examples:
  ./run_server.sh
  ./run_server.sh --port 8001 --reload
  HOST=0.0.0.0 PORT=9000 ./run_server.sh
USAGE
}

while (($#)); do
  case "$1" in
    -H|--host)
      [[ $# -ge 2 ]] || { echo "error: $1 requires a value" >&2; exit 2; }
      host="$2"
      shift 2
      ;;
    -p|--port)
      [[ $# -ge 2 ]] || { echo "error: $1 requires a value" >&2; exit 2; }
      port="$2"
      shift 2
      ;;
    -r|--reload)
      reload=1
      shift
      ;;
    --plantuml-jar)
      [[ $# -ge 2 ]] || { echo "error: $1 requires a value" >&2; exit 2; }
      plantuml_jar="$2"
      shift 2
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "error: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ ! "$port" =~ ^[0-9]+$ ]] || ((port < 1 || port > 65535)); then
  echo "error: port must be an integer from 1 to 65535" >&2
  exit 2
fi

if [[ -n "$plantuml_jar" ]]; then
  if [[ ! -f "$plantuml_jar" ]]; then
    echo "error: PlantUML jar not found: $plantuml_jar" >&2
    exit 2
  fi
  export PLANTUML_JAR="$plantuml_jar"
fi

command=(uv run uvicorn confluence_content_server.app:app --host "$host" --port "$port")
if ((reload)); then
  command+=(--reload)
fi

if ((dry_run)); then
  printf '%q ' "${command[@]}"
  printf '\n'
  exit 0
fi

exec "${command[@]}"
