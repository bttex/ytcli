#!/usr/bin/env bash
set -euo pipefail

APP_NAME="ytcli"
APP_DIR="${HOME}/.local/share/${APP_NAME}"
VENV_DIR="${APP_DIR}/.venv"
BIN_DIR="${HOME}/.local/bin"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() {
  printf "\n==> %s\n" "$1"
}

fail() {
  printf "\n[ERRO] %s\n" "$1" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Comando obrigatorio nao encontrado: $1"
}

install_system_deps() {
  if command -v apt >/dev/null 2>&1; then
    log "Instalando dependencias de sistema (apt)"
    sudo apt update
    sudo apt install -y \
      python3 python3-venv python3-pip \
      mpv libmpv2 ffmpeg \
      curl ca-certificates
    return
  fi

  if command -v dnf >/dev/null 2>&1; then
    log "Instalando dependencias de sistema (dnf)"
    sudo dnf install -y \
      python3 python3-pip \
      mpv mpv-libs ffmpeg \
      curl ca-certificates
    return
  fi

  if command -v pacman >/dev/null 2>&1; then
    log "Instalando dependencias de sistema (pacman)"
    sudo pacman -Sy --noconfirm \
      python python-pip \
      mpv ffmpeg \
      curl ca-certificates
    return
  fi

  fail "Gerenciador de pacotes nao suportado automaticamente. Instale python3, mpv e libmpv manualmente."
}

ensure_path_line() {
  local target_file="$1"
  local line='export PATH="$HOME/.local/bin:$PATH"'

  if [[ -f "$target_file" ]]; then
    grep -F "$line" "$target_file" >/dev/null 2>&1 || echo "$line" >> "$target_file"
  else
    echo "$line" > "$target_file"
  fi
}

main() {
  need_cmd python3

  install_system_deps

  log "Criando ambiente virtual em ${VENV_DIR}"
  mkdir -p "$APP_DIR"
  python3 -m venv "$VENV_DIR"

  log "Atualizando pip/setuptools/wheel"
  "$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel

  log "Instalando pacote Python"
  "$VENV_DIR/bin/pip" install "$REPO_DIR"

  log "Criando launcher music_tui em ${BIN_DIR}"
  mkdir -p "$BIN_DIR"
  cat > "${BIN_DIR}/music_tui" <<EOF
#!/usr/bin/env bash
exec "${VENV_DIR}/bin/music_tui" "\$@"
EOF
  chmod +x "${BIN_DIR}/music_tui"

  ensure_path_line "${HOME}/.bashrc"
  ensure_path_line "${HOME}/.zshrc"

  log "Instalacao concluida"
  echo "Abra um novo terminal ou execute:"
  echo "  export PATH=\"$HOME/.local/bin:$PATH\""
  echo "Depois rode:"
  echo "  music_tui"
  echo
  echo "Observacao: o comando music_tui ja inicia o daemon automaticamente quando necessario."
}

main "$@"
