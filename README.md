# Bot Telegram - Gerenciamento de Motoristas

Um bot robusto para Telegram que gerencia dados de motoristas com sistema de planilha de fechamento automática.

## Funcionalidades

✅ **Adicionar Motoristas** - Registre novos motoristas no sistema  
✅ **Buscar por Placa** - Pesquise motoristas pela placa do veículo  
✅ **Buscar por LH** - Pesquise motoristas pela LH (Licença de Habilitação)  
✅ **Marcar como Concluído** - Registre motoristas que completaram suas tarefas  
✅ **Marcar como Cancelado** - Registre cancelamentos  
✅ **Remover Motorista** - Remova motorista do sistema  
✅ **Gerar Planilha** - Crie planilha Excel com cores automáticas  
✅ **Sistema de Logging** - Registre todas as operações em arquivo de log  
✅ **Retry Automático** - Reconecte automaticamente em caso de falha  

## Instalação

### Pré-requisitos

- Python 3.8+
- pip (gerenciador de pacotes Python)
- Token do Telegram Bot (obtenha em @BotFather no Telegram)

### Passos

1. **Clone ou baixe o repositório**:
   ```bash
   cd c:\programacao\projeto_trabalho
   ```

2. **Instale as dependências**:
   ```bash
   python -m pip install -r requirements.txt
   ```

3. **Configure o token** no arquivo `.env`:
   ```
   token_telegram=SEU_TOKEN_AQUI
   ```

4. **Execute o bot**:
   ```bash
   python main.py
   ```

## Comandos Disponíveis

### `/help`
Mostra a lista de todos os comandos com exemplos.

```
/help
```

---

### `/add <LH> <NOME> <PLACA>`
Adiciona um novo motorista ao sistema.

**Parâmetros:**
- `<LH>` - Licença de Habilitação (13 caracteres)
- `<NOME>` - Nome completo do motorista
- `<PLACA>` - Placa do veículo (7 caracteres)

**Exemplo:**
```
/add LH1234567890123 Joao Silva ABC1234
```

**Resposta:**
- ✅ `[OK] Motorista adicionado com sucesso.` (novo)
- ⚠️ `[AVISO] Motorista com essa LH já existe.` (duplicado)
- ❌ `[ERRO] Formato inválido.` (erro)

---

### `/placa <PLACA>`
Busca motorista pela placa do veículo (7 caracteres).

**Exemplo:**
```
/placa ABC1234
```

**Resposta:**
- ✅ `[OK] Motorista encontrado: {...}`
- ❌ `[FALHA] Nenhum motorista encontrado para placa ABC1234`

---

### `/lh <LH>`
Busca motorista pela Licença de Habilitação (13 caracteres).

**Exemplo:**
```
/lh LH1234567890123
```

**Resposta:**
- ✅ `[OK] Motorista encontrado: {...}`
- ❌ `[FALHA] Nenhum motorista encontrado para LH`

---

### `/add <LH> <NOME> <PLACA>`
Adiciona um novo motorista ao sistema com verificação de duplicatas.

---

### `/concluidos <LH>`
Marca um motorista como **Concluído** (ficará verde na planilha).

**Exemplo:**
```
/concluidos LH1234567890123
```

**Resposta:**
- ✅ `[OK] Motorista marcado como concluído.`
- ❌ `[ERRO] Motorista não encontrado.`

---

### `/cancelados <LH>`
Marca um motorista como **Cancelado** (ficará vermelho na planilha).

**Exemplo:**
```
/cancelados LH1234567890123
```

**Resposta:**
- ✅ `[OK] Motorista marcado como cancelado.`
- ❌ `[ERRO] Motorista não encontrado.`

---

### `/remove <LH>`
Remove motorista do sistema (marca como cancelado no histórico).

**Exemplo:**
```
/remove LH1234567890123
```

**Resposta:**
- ✅ `[OK] Motorista removido com sucesso.`
- ❌ `[ERRO] Motorista não encontrado.`

---

### `/planilha`
Gera e envia uma planilha Excel com todos os motoristas e seus status.

**Características:**
- 📊 Arquivo Excel com cores automáticas
- 🟡 **Amarelo** = Motorista Ativo
- 🟢 **Verde** = Motorista Concluído
- 🔴 **Vermelho** = Motorista Cancelado
- 💾 Nunca remove dados (sempre acumula histórico)
- 📅 Nomeado com data atual

**Exemplo:**
```
/planilha
```

**Resposta:**
- Arquivo Excel é enviado via Telegram
- Mensagem explicando as cores

---

## Estrutura de Arquivos

```
projeto_trabalho/
├── main.py                 # Bot principal
├── estrutura.py            # Classe RoboBolsao (dados)
├── planilha_fechamento.py  # Gerador de planilhas Excel
├── requirements.txt        # Dependências
├── .env                    # Token (NÃO commitar)
├── bot.log                 # Arquivo de logs
├── README.md               # Este arquivo
└── planilha_fechamento_*.xlsx  # Planilhas geradas
```

## Logs

Todos os eventos são registrados em `bot.log`:

- **INFO** - Operações bem-sucedidas
- **WARNING** - Avisos (duplicatas, etc)
- **ERROR** - Erros (falhas de conexão, etc)

**Exemplo:**
```
2025-12-12 10:30:45,123 - INFO - [BOT] Iniciando Bot Telegram para Busca de Motoristas
2025-12-12 10:30:50,456 - INFO - Nova mensagem de Joao (123456789): /add LH1234567890123 Pedro ABC1234
2025-12-12 10:30:51,789 - INFO - Motorista novo adicionado: {'LH': 'LH1234567890123', ...}
```

## Configuração Avançada

### Ajustar Retry

No `main.py`, você pode modificar quantas vezes o bot tenta reconectar:

```python
bot = BotTelegram(
    bot_bolsao=bot_b,
    max_retries=5,      # Número de tentativas
    retry_delay=5       # Segundos entre tentativas
)
```

### Timeout de Requisições

```python
bot.timeout = 30  # Segundos
```

## Tratamento de Erros

O bot foi projetado para **nunca travar** durante longos períodos:

✅ **Reconexão automática** - Se perder conexão, reconecta automaticamente  
✅ **Processamento isolado** - Erro em uma mensagem não afeta outras  
✅ **Retry inteligente** - Tenta novamente com delay progressivo  
✅ **Logging completo** - Todos os erros são registrados  

## Exemplos de Uso

### Adicionar 3 motoristas

```
/add LH1234567890123 Joao Silva ABC1234
/add LH9876543210987 Maria Santos XYZ7890
/add LH5555555555555 Pedro Costa JKL9876
```

### Buscar e marcar como concluído

```
/placa ABC1234           # Busca por placa
/concluidos LH1234567890123  # Marca como concluído
/planilha                # Gera relatório
```

### Gerenciar cancelamentos

```
/cancelados LH9876543210987  # Marca como cancelado
/remove LH5555555555555       # Remove (cancela)
/planilha                     # Relatório atualizado
```

## Troubleshooting

### ❌ "ModuleNotFoundError: No module named 'openpyxl'"

**Solução:**
```bash
python -m pip install openpyxl
```

### ❌ "token não configurado"

**Solução:**
1. Crie arquivo `.env` na pasta do projeto
2. Adicione: `token_telegram=SEU_TOKEN_AQUI`
3. Obtenha token em @BotFather no Telegram

### ❌ "Falha ao enviar arquivo"

**Verificar:**
- Arquivo Excel foi criado? Verifique `bot.log`
- Permissões de leitura no arquivo
- Permissões de acesso do bot ao Telegram

## Performance

- **Requisições Não-Bloqueantes** - Múltiplas buscas em paralelo
- **Threads Daemon** - Operações longas não travam o bot
- **Timeout de 30s** - Evita requisições penduradas
- **Planilhas Incrementais** - Apenas atualiza dados, não reescreve

## Segurança

⚠️ **NUNCA** commit do arquivo `.env` com o token real!

Adicione ao `.gitignore`:
```
.env
bot.log
*.xlsx
```

## Manutenção

### Limpar logs

```bash
# Windows
del bot.log

# Linux/Mac
rm bot.log
```

### Backup de planilhas

As planilhas são automaticamente nomeadas com data:
```
planilha_fechamento_12_12_2025.xlsx
```

## Suporte

Para reportar bugs ou solicitar features, entre em contato com o desenvolvedor.

---

**Versão:** 1.0  
**Última Atualização:** 12/12/2025  
**Status:** ✅ Em Produção
