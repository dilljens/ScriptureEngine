#!/usr/bin/env bash
# Start one credential-isolated native OpenCode Go worker per workspace.
#
# The parent chat service should receive the resulting socket list through
# OPENCODE_GO_WORKER_SOCKETS. Keys stay inside the ai-secret-injected workers.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOCKET_DIR="${OPENCODE_GO_SOCKET_DIR:-${XDG_RUNTIME_DIR:-/tmp}/scriptureengine-opencode-go}"
PYTHON="${PYTHON:-${ROOT_DIR}/.venv/bin/python3}"

mkdir -p "$SOCKET_DIR"
chmod 700 "$SOCKET_DIR"

# Run this script under the process supervisor (or a systemd service) so the
# entire process group is stopped together.  The script intentionally avoids
# managing child signals itself; raw kill commands are unsafe for shared hosts.

for index in 1 2 3 4; do
  secret="opencode-go-${index}"
  socket_path="${SOCKET_DIR}/worker-${index}.sock"
  ai-secret exec "$secret" --env OPENCODE_API_KEY --reason "ScriptureEngine OpenCode Go worker ${index}" -- \
    "$PYTHON" "$ROOT_DIR/scripts/opencode_go_worker.py" --socket "$socket_path" &
done

printf 'OPENCODE_GO_WORKER_SOCKETS=%s\n' \
  "${SOCKET_DIR}/worker-1.sock,${SOCKET_DIR}/worker-2.sock,${SOCKET_DIR}/worker-3.sock,${SOCKET_DIR}/worker-4.sock"

wait
