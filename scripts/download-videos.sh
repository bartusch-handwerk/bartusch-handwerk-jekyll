#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
MANIFEST="${1:-videos.manifest}"

if [ ! -f "$PROJECT_DIR/$MANIFEST" ]; then
  echo "Error: $MANIFEST not found in $PROJECT_DIR" >&2
  exit 1
fi

downloaded=0
skipped=0
failed=0

while IFS=$'\t' read -r path url_template; do
  # Skip comments and empty lines
  [[ -z "$path" || "$path" == \#* ]] && continue

  dest="$PROJECT_DIR/$path"
  mkdir -p "$(dirname "$dest")"

  if [ -f "$dest" ]; then
    echo "SKIP  $path (already exists)"
    skipped=$((skipped + 1))
    continue
  fi

  # Substitute environment variables in URL template
  url=$(envsubst <<< "$url_template")
  echo "GET   $path"
  if curl -fSL --progress-bar -o "$dest" "$url"; then
    downloaded=$((downloaded + 1))
  else
    echo "FAIL  $path" >&2
    rm -f "$dest"
    failed=$((failed + 1))
  fi
done < "$PROJECT_DIR/$MANIFEST"

echo ""
echo "Done: $downloaded downloaded, $skipped skipped, $failed failed"
[ "$failed" -eq 0 ]
