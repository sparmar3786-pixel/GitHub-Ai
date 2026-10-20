#!/usr/bin/env bash
set -euo pipefail

# Run inside the Ollama container before pulling model weights.
# Defaults are intentionally configurable to match the approved Render plan.
MIN_MEMORY_MB="${OLLAMA_MIN_MEMORY_MB:-4096}"
MIN_DISK_MB="${OLLAMA_MIN_DISK_MB:-6000}"
MODEL_DIR="${OLLAMA_MODELS:-/data/models}"

read_memory_limit_mb() {
  local value
  if [[ -r /sys/fs/cgroup/memory.max ]]; then
    value="$(cat /sys/fs/cgroup/memory.max)"
    if [[ "$value" != "max" && "$value" =~ ^[0-9]+$ ]]; then
      echo $((value / 1024 / 1024))
      return
    fi
  fi
  if [[ -r /sys/fs/cgroup/memory/memory.limit_in_bytes ]]; then
    value="$(cat /sys/fs/cgroup/memory/memory.limit_in_bytes)"
    if [[ "$value" =~ ^[0-9]+$ ]] && (( value < 9223372036854771712 )); then
      echo $((value / 1024 / 1024))
      return
    fi
  fi
  awk '/MemTotal:/ {print int($2 / 1024); exit}' /proc/meminfo
}

if ! [[ "$MIN_MEMORY_MB" =~ ^[0-9]+$ && "$MIN_DISK_MB" =~ ^[0-9]+$ ]]; then
  echo "OLLAMA_MIN_MEMORY_MB and OLLAMA_MIN_DISK_MB must be positive integers." >&2
  exit 2
fi

MEMORY_MB="$(read_memory_limit_mb)"
if [[ -z "$MEMORY_MB" || "$MEMORY_MB" -lt "$MIN_MEMORY_MB" ]]; then
  echo "RESOURCE_CHECK_FAILED: memory limit ${MEMORY_MB:-unknown} MB; minimum is $MIN_MEMORY_MB MB." >&2
  exit 1
fi

mkdir -p "$MODEL_DIR"
AVAILABLE_DISK_MB="$(df -Pm "$MODEL_DIR" | awk 'NR==2 {print $4}')"
if [[ -z "$AVAILABLE_DISK_MB" || "$AVAILABLE_DISK_MB" -lt "$MIN_DISK_MB" ]]; then
  echo "RESOURCE_CHECK_FAILED: free disk ${AVAILABLE_DISK_MB:-unknown} MB at $MODEL_DIR; minimum is $MIN_DISK_MB MB." >&2
  exit 1
fi

echo "RESOURCE_CHECK_OK: memory_limit_mb=$MEMORY_MB free_disk_mb=$AVAILABLE_DISK_MB model_dir=$MODEL_DIR"
