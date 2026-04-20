#!/usr/bin/env bash
# Install API Response Comparator as a clickable desktop app (Linux XDG).
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPS="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons/hicolor/scalable/apps"

mkdir -p "$APPS" "$ICONS"

cat > "$ICONS/api-response-comparator.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <rect x="4" y="8" width="56" height="48" rx="6" fill="#1c2030"/>
  <rect x="8" y="12" width="24" height="40" rx="3" fill="#171a22"/>
  <rect x="32" y="12" width="24" height="40" rx="3" fill="#171a22"/>
  <rect x="12" y="18" width="16" height="3" rx="1" fill="#34d399"/>
  <rect x="12" y="24" width="12" height="3" rx="1" fill="#8a93a6"/>
  <rect x="12" y="30" width="14" height="3" rx="1" fill="#fbbf24"/>
  <rect x="12" y="36" width="10" height="3" rx="1" fill="#8a93a6"/>
  <rect x="36" y="18" width="16" height="3" rx="1" fill="#34d399"/>
  <rect x="36" y="24" width="12" height="3" rx="1" fill="#8a93a6"/>
  <rect x="36" y="30" width="14" height="3" rx="1" fill="#f87171"/>
  <rect x="36" y="36" width="10" height="3" rx="1" fill="#8a93a6"/>
  <circle cx="32" cy="32" r="6" fill="#6366f1"/>
  <path d="M29 32 L31 34 L35 30" stroke="#fff" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
SVG

cat > "$APPS/api-response-comparator.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=API Response Comparator
GenericName=API Diff Tool
Comment=Side-by-side diff for JSON, XML, and plain-text API responses
Exec="$DIR/launch.sh"
Icon=api-response-comparator
Terminal=false
Categories=Development;Utility;
StartupNotify=true
EOF

chmod +x "$DIR/launch.sh" "$APPS/api-response-comparator.desktop"
update-desktop-database "$APPS" 2>/dev/null || true

echo "Installed. Look for 'API Response Comparator' in your app menu."
echo "Desktop entry: $APPS/api-response-comparator.desktop"
echo "Icon:          $ICONS/api-response-comparator.svg"
