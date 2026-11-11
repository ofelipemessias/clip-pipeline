# clip-pipeline

Corta automaticamente os melhores momentos de um vídeo em clipes verticais (9:16, 1080x1920) com legenda sincronizada queimada, prontos para Shorts/Reels/TikTok.

Fluxo: **vídeo local ou URL → transcrição local (whisper) → escolha dos melhores momentos (Claude ou heurística local) → cortes 9:16 com legenda (ffmpeg) → clipes + metadata.json.**

## O que ele faz

- Aceita um arquivo de vídeo local ou uma URL (download via yt-dlp).
- Transcreve o áudio localmente com [faster-whisper](https://github.com/SYSTRAN/faster-whisper), sem mandar nada para nuvem.
- Escolhe os N melhores momentos de duas formas:
  - **Claude** (se `ANTHROPIC_API_KEY` estiver definida): o modelo recebe a transcrição com tempos e devolve os momentos com justificativa;
  - **Heurística local** (sem nenhuma chave): pontua janelas por palavras-chave, ênfase e ritmo de fala.
- Corta cada momento em 9:16 (1080x1920) e queima a legenda sincronizada com ffmpeg.
- Gera um `metadata.json` com os tempos e a justificativa de cada clipe.

## Requisitos

- Python 3.10+
- ffmpeg com libass (no Ubuntu: `sudo apt install ffmpeg`)
- Opcional: `ANTHROPIC_API_KEY` para a seleção com Claude (sem ela, a heurística local é usada)

## Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Uso

```bash
clip-pipeline video.mp4
clip-pipeline video.mp4 --count 5 --min-len 15 --max-len 30 --model small --language pt
clip-pipeline "https://url-do-video" --outdir meus_clipes
clip-pipeline video.mp4 --no-llm   # força a heurística, sem chamar a API
```

Os clipes saem em `clips/clip1.mp4`, `clip2.mp4`... com os `.ass` de legenda e o `metadata.json` na mesma pasta.

Opções: `--count` (quantidade de clipes), `--min-len`/`--max-len` (duração em segundos), `--model` (tamanho do whisper: `tiny`, `base`, `small`...), `--language` (ex.: `pt`), `--no-llm`, `--outdir`. O modelo do Claude é configurável pela variável `CLIP_PIPELINE_MODEL`.

## Testes

```bash
pip install -e ".[dev]"
PYTHONPATH=src pytest tests/ -q
```

10 testes cobrem a seleção de momentos (heurística e parsing da resposta do LLM) e o corte real com ffmpeg (duração, resolução 1080x1920 e legenda rebaseada), usando um vídeo sintético gerado na hora. Além da suíte, o fluxo completo foi executado de ponta a ponta em um vídeo real de 44 s: transcrição, seleção dos 3 momentos e geração dos clipes verticais legendados.

## Limitações

- O enquadramento 9:16 é um **corte central**: não há rastreamento de rosto. Em vídeos com o assunto fora do centro, o corte pode perder o foco.
- O modelo whisper `tiny` é rápido, mas erra palavras; para transcrições melhores use `--model base` ou `small`.
- Sem `ANTHROPIC_API_KEY`, a seleção é uma heurística simples — o Claude escolhe visivelmente melhor.
- Dockerfile não está incluído nesta versão; empacotar em Docker é o próximo passo (ver roadmap).

## Próximos passos

- Rastreamento de rosto para o corte vertical
- Dockerfile + docker-compose
- GitHub Actions rodando a suíte de testes
- Estilos de legenda configuráveis (cor, posição, palavra por palavra)

## Aviso legal

Use apenas com **conteúdo próprio ou autorizado**. Baixar vídeos de plataformas pode violar os termos de serviço delas, e republicar conteúdo de terceiros sem permissão pode infringir direitos autorais. Este projeto existe para estudo e para uso em material que você tem direito de usar.

## Licença

MIT
