# YT Music CLI

Um cliente de música CLI para YouTube, controlado por um daemon em segundo plano. Ouça suas músicas favoritas diretamente do terminal, com suporte a fila de reprodução, busca e reprodução contínua.

 <!-- Substitua pelo link de uma imagem/gif de exemplo -->

## ✨ Funcionalidades

*   **Reprodução Simples**: Toque músicas do YouTube com um único comando.
*   **Daemon em Background**: O player roda em segundo plano, liberando seu terminal.
*   **Fila de Reprodução**: Adicione músicas a uma fila para ouvir sem interrupções.
*   **Busca Integrada**: Procure por músicas no YouTube e escolha qual tocar.
*   **Multiplataforma**: Compatível com Windows e Linux.
*   **Leve**: Utiliza `mpv` para reprodução de áudio, garantindo baixo consumo de recursos.

## 📋 Pré-requisitos

Antes de começar, você precisa ter os seguintes programas instalados:

1.  **Python 3.8+**
2.  **mpv**: Um reprodutor de mídia de linha de comando.
    *   **Windows**: Baixe, extraia e **adicione o diretório do `mpv.exe` ao PATH do sistema**.
    *   **Linux (Debian/Ubuntu)**: `sudo apt update && sudo apt install mpv`

## 🚀 Instalação

Você pode instalar o `yt-music-cli` diretamente do repositório usando `pip`.

1.  **Clone o repositório:**
    ```sh
    git clone https://github.com/bttex/ytcli.git
    cd ytcli
    ```

2.  **Instale o pacote:**
    Abra um terminal (PowerShell/CMD/Bash) e execute o comando `pip` na raiz do projeto. Isso instalará o comando `music_cli` no seu sistema.

    ```sh
    pip install .
    ```

    > **Nota**: No Windows, o `pip` geralmente instala os executáveis em um diretório que já está no seu PATH. Pode ser necessário reiniciar o terminal para que o comando `music_cli` seja reconhecido.

## 🎧 Como Usar

Após a instalação, você pode usar o comando `music_cli` de qualquer lugar no seu terminal.

O daemon será iniciado automaticamente no primeiro comando.

---

### Comandos Principais

**Tocar uma música imediatamente:**
```sh
music_cli play "daft punk get lucky"
```

**Buscar por uma música e escolher em uma lista:**
```sh
music_cli search "red hot chili peppers"
```

**Adicionar uma música à fila:**
```sh
music_cli queue-add "gorillaz feel good inc"
```

**Ver o status atual e a fila:**
```sh
music_cli status
```

**Listar todas as músicas na fila:**
```sh
music_cli queue-list
```

**Pular para a próxima música:**
```sh
music_cli next
```

**Pausar ou retomar a reprodução:**
```sh
music_cli pause
music_cli resume
```

## 🔧 Desenvolvimento

Se você deseja contribuir ou modificar o código, instale o projeto em modo "editável". Isso permite que suas alterações no código-fonte sejam refletidas imediatamente.

1.  Crie e ative um ambiente virtual:
    ```sh
    # Windows
    python -m venv .venv
    .\.venv\Scripts\activate

    # Linux/macOS
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2.  Instale em modo editável:
    ```sh
    pip install -e .
    ```
