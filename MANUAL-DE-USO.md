# 🌊 Brisa — Manual Completo de Uso

> Seu robô de monitoramento de imóveis no Rio de Janeiro

---

## 📱 Como a Brisa funciona no seu celular

A Brisa **não é um aplicativo** — ela roda em um servidor na nuvem (Railway) e te manda mensagens direto no **WhatsApp** que você já usa. Ou seja:

- ✅ Não precisa instalar nada no celular
- ✅ Não precisa abrir nenhum app
- ✅ As mensagens chegam como se fosse um contato normal
- ✅ Funciona 24h por dia, mesmo com o celular desligado

**Salve o número do CallMeBot na agenda** como "Brisa 🌊" para as mensagens aparecerem organizadas.

---

## 📁 Arquivos do projeto

| Arquivo | O que é |
|---|---|
| `monitor.py` | O cérebro da Brisa — todo o código |
| `requirements.txt` | Lista de bibliotecas Python necessárias |
| `Dockerfile` | Instrução para o Railway montar o ambiente |
| `railway.toml` | Configurações de deploy no Railway |

---

## 🚀 Passo a Passo — Subindo a Brisa no Railway

### ETAPA 1 · Criar conta no GitHub

1. Acesse **github.com**
2. Clique em **Sign up**
3. Crie sua conta (pode usar seu e-mail Google)

---

### ETAPA 2 · Criar o repositório

1. Após entrar no GitHub, clique no **"+"** no canto superior direito
2. Clique em **"New repository"**
3. Preencha:
   - **Repository name:** `brisa-imoveis`
   - Marque **Private** (seus dados ficam seguros)
4. Clique em **"Create repository"**

---

### ETAPA 3 · Enviar os arquivos

1. Na página do repositório criado, clique em **"uploading an existing file"**
2. Arraste ou selecione os 4 arquivos:
   - `monitor.py`
   - `requirements.txt`
   - `Dockerfile`
   - `railway.toml`
3. Clique em **"Commit changes"** (botão verde)

---

### ETAPA 4 · Criar conta no Railway

1. Acesse **railway.app**
2. Clique em **"Start a New Project"**
3. Escolha **"Login with GitHub"** — use a mesma conta que acabou de criar
4. Autorize o Railway a acessar seus repositórios

---

### ETAPA 5 · Criar o projeto

1. No painel do Railway, clique em **"New Project"**
2. Escolha **"Deploy from GitHub repo"**
3. Selecione o repositório **`brisa-imoveis`**
4. O Railway detecta o `Dockerfile` automaticamente e inicia o deploy
5. Aguarde a barra de progresso terminar (leva ~2 minutos)

---

### ETAPA 6 · Adicionar variáveis de segurança (opcional mas recomendado)

Para não deixar seu número exposto no código, adicione as variáveis no Railway:

1. Clique no seu projeto
2. Vá na aba **"Variables"**
3. Clique em **"New Variable"** e adicione:

| Nome da variável | Valor |
|---|---|
| `WHATSAPP_NUMERO` | +5521971626391 |
| `CALLMEBOT_APIKEY` | 3420482 |

4. O Railway reinicia automaticamente após salvar

> ⚠️ Se não adicionar as variáveis, tudo bem — os valores já estão configurados direto no `monitor.py`.

---

### ETAPA 7 · Confirmar que a Brisa está rodando

1. No painel do Railway, clique no seu projeto
2. Vá na aba **"Deployments"**
3. Clique no deploy mais recente
4. Clique em **"View Logs"**
5. Você deve ver algo assim:

```
🌊  BRISA · Monitora de Imóveis — Iniciando
   ⏱  Tempo real   : a cada 30 min
   📋 Resumo diário : 08:00 (máx. 10 imóveis)
   🚇 17 metrôs monitorados · raio 1.5km
   🔌 4 site(s): zapimoveis, vivareal, olx, quintoandar
🔍 Brisa verificando novos imóveis...
```

6. Em poucos minutos você recebe a primeira mensagem no WhatsApp! 🎉

---

## 💬 Mensagens que você vai receber

### Resumo diário (todo dia às 08h)
```
🌊 Brisa · Resumo do dia 02/05/2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Olha só o que eu garimpei pra você hoje! 🔍

📊 3 imóvel(is) selecionado(s) pra você analisar com calma
💰 Até R$ 200.000  |  🛏 2+ quartos
🚇 Raio de 1500m dos metrôs · Zona Sul & Tijuca
────────────────────────────────

#1 · ZAP Imóveis
🏠 Apartamento 2 quartos Botafogo
💰 R$ 185.000
🛏 2 quartos  |  📐 58m²
📍 Botafogo  |  🚗 ✅ Garagem
🚇 320m do Metrô Botafogo
🔗 https://zapimoveis.com.br/...
```

### Alerta de imóvel novo (tempo real)
```
🚨 Brisa aqui! Chegou imóvel novo! 🌊
────────────────────────────────
Acabei de achar esse apê e já vim te contar:

🏠 Apartamento reformado Flamengo
💰 R$ 195.000
🛏 2 quartos  |  📐 62m²
📍 Flamengo  |  🚗 ❌ Sem garagem
🚇 480m do Metrô Flamengo
🔗 https://vivareal.com.br/...

────────────────────────────────
Corre lá dar uma olhada enquanto tá fresquinho! 😄
```

### Quando não há novidades
```
🌊 Brisa · Resumo do dia 02/05/2026

Eita, hoje o mercado tá quietinho por aqui…
Mas não desanima não, amanhã cedo eu já tô de volta na missão! 🌊
```

---

## ⚙️ Como ajustar os filtros

Abra o `monitor.py` e edite o bloco `CONFIG` (no início do arquivo):

```python
"preco_maximo":    200_000,   # mude para o valor que quiser
"quartos_minimo":  2,          # mínimo de quartos
"metros_minimo":   0,          # 0 = sem filtro de metragem
"vagas_garagem":   False,      # True = só imóveis com garagem
"horario_resumo_diario": "08:00",    # horário do resumo
"intervalo_tempo_real_min": 30,      # frequência da varredura (minutos)
"raio_km": 1.5,                      # raio em km ao redor dos metrôs
```

Após editar, faça upload do `monitor.py` atualizado no GitHub e o Railway faz o novo deploy automaticamente.

---

## ➕ Como adicionar um site de imobiliária

1. Abra o `monitor.py`
2. Copie o template comentado no meio do arquivo (seção "ADICIONE NOVOS SITES AQUI")
3. Adapte para o site da imobiliária desejada
4. Adicione a função na lista `SCRAPERS`:

```python
SCRAPERS = [
    scrape_zapimoveis,
    scrape_vivareal,
    scrape_olx,
    scrape_quintoandar,
    scrape_minhaImobiliaria,  # ← adicione aqui
]
```

---

## 🔄 Como pausar ou parar a Brisa

**Pausar temporariamente:**
No Railway, vá em seu projeto → clique nos três pontinhos → **"Suspend"**

**Retomar:**
No mesmo lugar → **"Resume"**

**Parar o CallMeBot:**
Envie **Stop** para o número do CallMeBot.
Para reativar, envie **Resume**.

---

## 💰 Custo mensal

| Serviço | Custo |
|---|---|
| GitHub | Gratuito |
| CallMeBot | Gratuito |
| Railway (após trial) | ~$5/mês (≈ R$ 28/mês) |
| OpenStreetMap (geocodificação) | Gratuito |

---

## ❓ Problemas comuns

| Problema | Solução |
|---|---|
| Não recebo mensagens | Verifique nos logs do Railway se há erros. Confirme que o CallMeBot está ativo (não enviou "Stop") |
| Railway parou o projeto | Plano trial expirou — adicione um cartão no Railway para continuar |
| Nenhum imóvel encontrado | Os sites podem ter atualizado o HTML. Entre em contato para ajustar os seletores |
| Mensagens duplicadas | Não deve ocorrer — a Brisa tem memória. Se ocorrer, delete o arquivo `brisa_vistos.json` nos logs do Railway |

---

## 📞 Resumo rápido

```
GitHub  →  guarda seu código
   ↓
Railway →  roda a Brisa 24h na nuvem
   ↓
CallMeBot → entrega as mensagens
   ↓
WhatsApp → você recebe tudo no celular 📱
```

---

*🌊 Brisa — Monitora de Imóveis · Rio de Janeiro*
