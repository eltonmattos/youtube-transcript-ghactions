# YouTube Transcript to Notion usando Github Actions

Este projeto baixa **transcrições de vídeos do YouTube**, processa o texto usando **IA (OpenAI ou Gemini)** e salva o conteúdo tratado como **páginas no Notion**, com os parágrafos divididos em blocos de até 2000 caracteres.

O pipeline é projetado para rodar **100% na nuvem via GitHub Actions**.  
Você pode rodar manualmente (workflow_dispatch) ou agendado (cron).

## 🔑 Configuração

### 1. **Secrets do GitHub**

Vá em `Settings > Secrets and variables > Actions > New repository secret` e crie os seguintes:

| Nome               | Descrição                                              | Obrigatório |
|--------------------|--------------------------------------------------------|-------------|
| `SUPADATA_API_KEY` | Chave da Supadata API (para transcrições)              | ✅ |
| `OPENAI_API_KEY`   | Chave da OpenAI (se usar modelos `gpt-*`)              | ❌ |
| `GEMINI_API_KEY`   | Chave da Google Gemini (se usar modelos `gemini-*`)    | ❌ |
| `NOTION_TOKEN`     | Token da integração com o Notion                       | ✅ |

### 2. **Variáveis de ambiente (vars do GitHub)**

Em `Settings > Secrets and variables > Actions > New repository variable` crie:

| Nome               | Exemplo                   | Descrição |
|--------------------|---------------------------|-----------|
| `NOTION_PARENT_ID` | `xxxxxxxxxxxxxxxxxx`      | ID da página/pasta onde as páginas serão criadas |
| `AI_MODEL`         | `gpt-4o-mini` ou `gemini-2.5-flash` | Modelo usado para processamento |
| `AI_PROMPT`        | `"Format the transcript into paragraphs with punctuation."` | Prompt que define como tratar a transcrição |

## 📦 Dependências

Instale localmente (se quiser testar fora do Actions):

```bash
pip install -r requirements.txt
```

## ▶️ Execução

O script principal está em scripts/main.py.

Exemplo de chamada dentro do workflow:

python scripts/main.py


Por padrão, o main.py vem com uma lista de URLs de exemplo.
Você pode adaptar para receber:

Uma playlist do YouTube (iterar sobre vídeos)

Uma lista de URLs específica

## 📝 Funcionamento

Extrai metadados do vídeo (título e canal) usando yt-dlp

Baixa transcrição do vídeo usando Supadata API

Processa o texto com OpenAI ou Gemini (baseado em AI_MODEL)

Divide em blocos de até 2000 caracteres

Cria página no Notion com título "[Título do vídeo] - [Canal]"

## ⚠️ Observações

Apenas a transcrição usa a Supadata API → economiza chamadas.

Título e canal são obtidos via yt-dlp (sem custo).

O NOTION_PARENT_ID não precisa ser secreto, pode ser só uma variável.
