![Branches](https://www.shieldcn.dev/github/branches/bttex/ytcli.svg?variant=ghost&size=sm)
![Contributors](https://www.shieldcn.dev/github/contributors/bttex/ytcli.svg?theme=emerald&size=sm)
![Last commit](https://www.shieldcn.dev/github/last-commit/bttex/ytcli.svg?variant=secondary&size=sm)
![Commits](https://www.shieldcn.dev/github/commits/bttex/ytcli.svg?variant=secondary&size=sm)
[![License: MIT](![badge](https://shieldcn.dev/badge/License%20MIT.svg?variant=secondary))](LICENSE)


# YTCLI

Interface TUI para controlar reprodução de músicas do YouTube Music com um daemon local em segundo plano. O projeto foi simplificado para usar apenas a TUI como interface de usuário.

## Funcionalidades

* Busca músicas ou URLs diretamente no terminal.
* Mostra a faixa atual, a fila e os resultados da busca.
* Permite tocar, enfileirar, pausar, retomar, avançar e parar.
* Inicia o daemon automaticamente quando necessário.
* Funciona no Linux e também em outros sistemas suportados pelo Python, `mpv` e dependências do projeto.

## Pré-requisitos

* Python 3.10+
* `mpv`

No Ubuntu/Debian:

```sh
sudo apt update && sudo apt install -y mpv python3-venv
```

## Instalação

```sh
chmod +x install.sh
./install.sh
```

Ou, para desenvolvimento local:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

## Uso

Abra a interface com:

```sh
music_tui
```

Na TUI, use a caixa de busca para pesquisar músicas ou colar uma URL. Depois selecione um resultado para tocar ou enfileirar.

Atalhos úteis:

* `q`: sair
* `r`: atualizar status
* `p`: pausar ou retomar

## Instalação manual

Se preferir instalar sem o script:

```sh
pip install .
```

## Desenvolvimento

O fluxo recomendado para contribuir é usar o ambiente virtual local e instalar em modo editável com `pip install -e .`. Isso mantém a TUI apontando para o código em desenvolvimento.
