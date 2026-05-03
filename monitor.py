"""
🌊 BRISA — Robô Monitor de Imóveis · Rio de Janeiro
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Monitora múltiplos sites de imóveis e envia alertas
pelo WhatsApp via CallMeBot.

Modos de operação:
  • Tempo real  — verifica a cada X minutos e alerta
                  imediatamente ao encontrar imóvel novo
  • Resumo diário — envia até 10 imóveis por dia no
                    horário configurado, para análise
                    tranquila

Para adicionar novos sites, crie uma função
scrape_<nomedosite>() seguindo o padrão dos existentes
e registre-a na lista SCRAPERS no final do arquivo.
"""

import os
import requests
import json
import time
import logging
import math
import random
from datetime import datetime
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Optional

# ══════════════════════════════════════════════════════
#  ⚙️  CONFIGURAÇÕES — EDITE AQUI
# ══════════════════════════════════════════════════════
CONFIG = {
    # ── WhatsApp (CallMeBot) ───────────────────────────
    "whatsapp_numero":  os.environ.get("WHATSAPP_NUMERO",  "+5521971626391"),
    "callmebot_apikey": os.environ.get("CALLMEBOT_APIKEY", "3420482"),

    # ── Filtros de busca ───────────────────────────────
    "cidade":          "rio-de-janeiro",
    "preco_maximo":    200_000,
    "quartos_minimo":  2,
    "metros_minimo":   0,       # 0 = sem filtro de metragem
    "vagas_garagem":   False,   # True = exige pelo menos 1 vaga

    # ── Comportamento ─────────────────────────────────
    "horario_resumo_diario":    "08:00",  # Horário do resumo diário
    "max_resumo_diario":        10,       # Máx de imóveis no resumo diário
    "intervalo_tempo_real_min": 30,       # Verifica novos a cada X minutos
    "max_coleta_por_site":      15,       # Coleta mais para garantir 10 após filtros

    # ── Raio geográfico ───────────────────────────────
    # Imóvel precisa estar a até raio_km de pelo menos 1 metrô
    "raio_km": 1.5,
    "pontos_referencia": [
        # ── Linha 1 · Laranja (Zona Sul / Centro) ─────
        {"nome": "Metrô Glória",            "lat": -22.9233, "lon": -43.1763},
        {"nome": "Metrô Largo do Machado",  "lat": -22.9303, "lon": -43.1789},
        {"nome": "Metrô Catete",            "lat": -22.9264, "lon": -43.1756},
        {"nome": "Metrô Flamengo",          "lat": -22.9356, "lon": -43.1769},
        {"nome": "Metrô Botafogo",          "lat": -22.9519, "lon": -43.1876},
        {"nome": "Metrô Cardeal Arcoverde", "lat": -22.9671, "lon": -43.1888},
        {"nome": "Metrô Siqueira Campos",   "lat": -22.9699, "lon": -43.1851},
        {"nome": "Metrô Cantagalo",         "lat": -22.9729, "lon": -43.1871},
        {"nome": "Metrô General Osório",    "lat": -22.9869, "lon": -43.1966},
        {"nome": "Metrô N. Sra da Paz",     "lat": -22.9842, "lon": -43.2044},
        {"nome": "Metrô Jardim de Allah",   "lat": -22.9901, "lon": -43.2153},
        {"nome": "Metrô Antero de Quental", "lat": -22.9934, "lon": -43.2235},
        {"nome": "Metrô São Conrado",       "lat": -23.0001, "lon": -43.2673},
        {"nome": "Metrô Jardim Oceânico",   "lat": -23.0047, "lon": -43.3097},
        # ── Linha 2 · Verde (Tijuca) ──────────────────
        {"nome": "Metrô Saens Peña",        "lat": -22.9232, "lon": -43.2344},
        {"nome": "Metrô Uruguai",           "lat": -22.9195, "lon": -43.2432},
        {"nome": "Metrô Afonso Pena",       "lat": -22.9264, "lon": -43.2289},
    ],
}

# ══════════════════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("brisa.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("brisa")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9",
}


# ══════════════════════════════════════════════════════
#  MODELO DE IMÓVEL
# ══════════════════════════════════════════════════════
@dataclass
class Imovel:
    titulo:        str
    preco:         int
    quartos:       int
    metros:        int
    bairro:        str
    link:          str
    fonte:         str
    garagem:       bool            = False
    lat:           Optional[float] = None
    lon:           Optional[float] = None
    ponto_proximo: str             = ""
    distancia_m:   float           = 0.0

    def formatar_whatsapp(self) -> str:
        preco_fmt   = f"R$ {self.preco:,.0f}".replace(",", ".")
        garagem_txt = "✅ Garagem" if self.garagem else "❌ Sem garagem"
        metros_txt  = f"{self.metros}m²" if self.metros else "–"
        geo_txt     = (
            f"🚇 {self.distancia_m:.0f}m do {self.ponto_proximo}\n"
            if self.ponto_proximo else ""
        )
        return (
            f"🏠 *{self.titulo[:55]}*\n"
            f"💰 {preco_fmt}\n"
            f"🛏 {self.quartos} quartos  |  📐 {metros_txt}\n"
            f"📍 {self.bairro.title()}  |  🚗 {garagem_txt}\n"
            f"{geo_txt}"
            f"🔗 {self.link}\n"
        )


# ══════════════════════════════════════════════════════
#  GEOLOCALIZAÇÃO  (OpenStreetMap · gratuito · sem chave)
# ══════════════════════════════════════════════════════
def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1))
         * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def geocodificar(texto: str) -> Optional[tuple]:
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": f"{texto}, Rio de Janeiro, Brasil", "format": "json", "limit": 1},
            headers={"User-Agent": "Brisa-MonitorImoveis/2.0"},
            timeout=10,
        )
        data = resp.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        log.debug(f"Geocodificação falhou para '{texto}': {e}")
    return None


def ponto_mais_proximo(lat: float, lon: float) -> tuple:
    melhor = min(
        CONFIG["pontos_referencia"],
        key=lambda p: haversine(lat, lon, p["lat"], p["lon"]),
    )
    return melhor["nome"], haversine(lat, lon, melhor["lat"], melhor["lon"])


def dentro_do_raio(lat: float, lon: float) -> bool:
    return any(
        haversine(lat, lon, p["lat"], p["lon"]) <= CONFIG["raio_km"]
        for p in CONFIG["pontos_referencia"]
    )


def enriquecer_geo(im: Imovel) -> Imovel:
    if not (im.lat and im.lon):
        coords = geocodificar(im.bairro)
        if coords:
            im.lat, im.lon = coords
            time.sleep(1)
    if im.lat and im.lon:
        nome, dist_km = ponto_mais_proximo(im.lat, im.lon)
        im.ponto_proximo = nome
        im.distancia_m   = dist_km * 1000
    return im


# ══════════════════════════════════════════════════════
#  SCRAPERS
#  ─────────────────────────────────────────────────────
#  Para adicionar um novo site, crie uma função com a
#  assinatura:
#
#      def scrape_nomedosite() -> list[Imovel]:
#          ...
#
#  e adicione-a à lista SCRAPERS no final deste bloco.
# ══════════════════════════════════════════════════════

def scrape_zapimoveis() -> list:
    imoveis   = []
    preco_max = CONFIG["preco_maximo"]
    quartos   = CONFIG["quartos_minimo"]
    limite    = CONFIG["max_coleta_por_site"]
    try:
        url = (
            f"https://www.zapimoveis.com.br/venda/apartamentos/{CONFIG['cidade']}/"
            f"?quartos={quartos}&precoMaximo={preco_max}"
        )
        log.info(f"[ZAP] Buscando: {url}")
        soup = BeautifulSoup(requests.get(url, headers=HEADERS, timeout=15).text, "html.parser")
        for card in soup.select("div[data-testid='card-premium'], div[data-testid='card']")[:limite]:
            try:
                titulo_el  = card.select_one("h2, [class*='title']")
                preco_el   = card.select_one("[class*='price']")
                quartos_el = card.select_one("[aria-label*='quarto'], [class*='bedroom']")
                metros_el  = card.select_one("[aria-label*='metros'], [class*='area']")
                bairro_el  = card.select_one("[class*='address'], [class*='location']")
                link_el    = card.select_one("a[href]")
                garagem_el = card.select_one("[aria-label*='vaga'], [class*='parking']")

                preco = int("".join(filter(str.isdigit, preco_el.text)) or 0) if preco_el else 0
                if preco == 0 or preco > preco_max:
                    continue

                link = link_el["href"] if link_el else ""
                if link and not link.startswith("http"):
                    link = "https://www.zapimoveis.com.br" + link

                imoveis.append(Imovel(
                    titulo  = titulo_el.text.strip()  if titulo_el  else "Apartamento",
                    preco   = preco,
                    quartos = int("".join(filter(str.isdigit, quartos_el.text)) or quartos) if quartos_el else quartos,
                    metros  = int("".join(filter(str.isdigit, metros_el.text))  or 0)       if metros_el  else 0,
                    bairro  = bairro_el.text.strip()  if bairro_el  else "Rio de Janeiro",
                    link    = link,
                    fonte   = "ZAP Imóveis",
                    garagem = bool(garagem_el),
                ))
            except Exception as e:
                log.debug(f"[ZAP] Erro no card: {e}")
    except Exception as e:
        log.error(f"[ZAP] Falha geral: {e}")
    log.info(f"[ZAP] {len(imoveis)} coletado(s)")
    return imoveis


def scrape_vivareal() -> list:
    imoveis   = []
    preco_max = CONFIG["preco_maximo"]
    quartos   = CONFIG["quartos_minimo"]
    limite    = CONFIG["max_coleta_por_site"]
    try:
        url = (
            f"https://www.vivareal.com.br/venda/rj/{CONFIG['cidade']}/apartamento_residencial/"
            f"?quartos={quartos}&preco-ate={preco_max}"
        )
        log.info(f"[VivaReal] Buscando: {url}")
        soup = BeautifulSoup(requests.get(url, headers=HEADERS, timeout=15).text, "html.parser")
        for card in soup.select("article[data-type='property']")[:limite]:
            try:
                titulo_el  = card.select_one("h2, .property-card__title")
                preco_el   = card.select_one(".property-card__price")
                quartos_el = card.select_one("[class*='bedrooms']")
                metros_el  = card.select_one("[class*='area']")
                bairro_el  = card.select_one(".property-card__address")
                link_el    = card.select_one("a[href]")
                garagem_el = card.select_one("[class*='parking'], [class*='garage']")

                preco = int("".join(filter(str.isdigit, preco_el.text)) or 0) if preco_el else 0
                if preco == 0 or preco > preco_max:
                    continue

                link = link_el["href"] if link_el else ""
                if link and not link.startswith("http"):
                    link = "https://www.vivareal.com.br" + link

                imoveis.append(Imovel(
                    titulo  = titulo_el.text.strip()  if titulo_el  else "Apartamento",
                    preco   = preco,
                    quartos = int("".join(filter(str.isdigit, quartos_el.text)) or quartos) if quartos_el else quartos,
                    metros  = int("".join(filter(str.isdigit, metros_el.text))  or 0)       if metros_el  else 0,
                    bairro  = bairro_el.text.strip()  if bairro_el  else "Rio de Janeiro",
                    link    = link,
                    fonte   = "Viva Real",
                    garagem = bool(garagem_el),
                ))
            except Exception as e:
                log.debug(f"[VivaReal] Erro no card: {e}")
    except Exception as e:
        log.error(f"[VivaReal] Falha geral: {e}")
    log.info(f"[VivaReal] {len(imoveis)} coletado(s)")
    return imoveis


def scrape_olx() -> list:
    imoveis   = []
    preco_max = CONFIG["preco_maximo"]
    limite    = CONFIG["max_coleta_por_site"]
    try:
        url = (
            f"https://rj.olx.com.br/rio-de-janeiro-e-regiao/imoveis/venda/apartamentos"
            f"?pe={preco_max}&ros=2"
        )
        log.info(f"[OLX] Buscando: {url}")
        soup = BeautifulSoup(requests.get(url, headers=HEADERS, timeout=15).text, "html.parser")
        for card in soup.select("li[class*='sc-'], section[class*='AdCard']")[:limite]:
            try:
                titulo_el = card.select_one("h2, h3, [class*='title']")
                preco_el  = card.select_one("[class*='price'], [class*='Price']")
                bairro_el = card.select_one("[class*='location'], [class*='Location']")
                link_el   = card.select_one("a[href]")

                preco = int("".join(filter(str.isdigit, preco_el.text)) or 0) if preco_el else 0
                if preco == 0 or preco > preco_max:
                    continue

                imoveis.append(Imovel(
                    titulo  = titulo_el.text.strip() if titulo_el else "Apartamento",
                    preco   = preco,
                    quartos = CONFIG["quartos_minimo"],
                    metros  = 0,
                    bairro  = bairro_el.text.strip() if bairro_el else "Rio de Janeiro",
                    link    = link_el["href"] if link_el else "",
                    fonte   = "OLX",
                ))
            except Exception as e:
                log.debug(f"[OLX] Erro no card: {e}")
    except Exception as e:
        log.error(f"[OLX] Falha geral: {e}")
    log.info(f"[OLX] {len(imoveis)} coletado(s)")
    return imoveis


def scrape_quintoandar() -> list:
    imoveis   = []
    preco_max = CONFIG["preco_maximo"]
    quartos   = CONFIG["quartos_minimo"]
    limite    = CONFIG["max_coleta_por_site"]
    try:
        url = (
            f"https://www.quintoandar.com.br/comprar/imovel/rio-de-janeiro-rj-brasil"
            f"?maxPrice={preco_max}&minBedrooms={quartos}"
        )
        log.info(f"[QuintoAndar] Buscando: {url}")
        soup = BeautifulSoup(requests.get(url, headers=HEADERS, timeout=15).text, "html.parser")
        for card in soup.select("[data-testid='house-card'], [class*='HouseCard']")[:limite]:
            try:
                titulo_el = card.select_one("h2, [class*='title']")
                preco_el  = card.select_one("[class*='price'], [class*='Price']")
                bairro_el = card.select_one("[class*='address'], [class*='neighborhood']")
                link_el   = card.select_one("a[href]")

                preco = int("".join(filter(str.isdigit, preco_el.text)) or 0) if preco_el else 0
                if preco == 0 or preco > preco_max:
                    continue

                link = link_el["href"] if link_el else ""
                if link and not link.startswith("http"):
                    link = "https://www.quintoandar.com.br" + link

                imoveis.append(Imovel(
                    titulo  = titulo_el.text.strip() if titulo_el else "Apartamento",
                    preco   = preco,
                    quartos = quartos,
                    metros  = 0,
                    bairro  = bairro_el.text.strip() if bairro_el else "Rio de Janeiro",
                    link    = link,
                    fonte   = "QuintoAndar",
                ))
            except Exception as e:
                log.debug(f"[QuintoAndar] Erro no card: {e}")
    except Exception as e:
        log.error(f"[QuintoAndar] Falha geral: {e}")
    log.info(f"[QuintoAndar] {len(imoveis)} coletado(s)")
    return imoveis


# ──────────────────────────────────────────────────────
#  ➕ ADICIONE NOVOS SITES AQUI
#
#  Template para imobiliária carioca:
#
#  def scrape_minhaImobiliaria() -> list:
#      imoveis   = []
#      preco_max = CONFIG["preco_maximo"]
#      quartos   = CONFIG["quartos_minimo"]
#      limite    = CONFIG["max_coleta_por_site"]
#      try:
#          url  = f"https://www.minhaimobiliaria.com.br/busca?preco={preco_max}"
#          soup = BeautifulSoup(requests.get(url, headers=HEADERS, timeout=15).text, "html.parser")
#          for card in soup.select(".card-imovel")[:limite]:
#              ...
#              imoveis.append(Imovel(..., fonte="Minha Imobiliária"))
#      except Exception as e:
#          log.error(f"[MinhaImob] Falha: {e}")
#      return imoveis
#
# ──────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════
#  LISTA DE SCRAPERS ATIVOS
#  Comente/descomente para ligar ou desligar um site
# ══════════════════════════════════════════════════════
SCRAPERS = [
    scrape_zapimoveis,
    scrape_vivareal,
    scrape_olx,
    scrape_quintoandar,
    # scrape_minhaImobiliaria,  ← descomente quando adicionar
]


# ══════════════════════════════════════════════════════
#  FILTROS
# ══════════════════════════════════════════════════════
def filtrar(imoveis: list) -> list:
    filtrados = []
    total = len(imoveis)
    log.info(f"Filtrando + geocodificando {total} imóvel(is)...")
    for i, im in enumerate(imoveis, 1):
        if im.preco > CONFIG["preco_maximo"]:
            continue
        if im.quartos < CONFIG["quartos_minimo"]:
            continue
        if CONFIG["metros_minimo"] > 0 and im.metros > 0 and im.metros < CONFIG["metros_minimo"]:
            continue
        if CONFIG["vagas_garagem"] and not im.garagem:
            continue
        log.info(f"  [{i}/{total}] Geocodificando '{im.bairro}' ({im.fonte})")
        im = enriquecer_geo(im)
        if im.lat and im.lon:
            if not dentro_do_raio(im.lat, im.lon):
                log.info(f"    ↳ Fora do raio ({im.distancia_m:.0f}m). Descartado.")
                continue
            log.info(f"    ↳ ✅ {im.distancia_m:.0f}m de {im.ponto_proximo}")
        else:
            log.warning("    ↳ ⚠️  Sem coordenadas — mantido sem filtro geo.")
        filtrados.append(im)
    return filtrados


# ══════════════════════════════════════════════════════
#  MEMÓRIA — nunca reenviar o mesmo imóvel
# ══════════════════════════════════════════════════════
ARQUIVO_VISTOS = "brisa_vistos.json"

def carregar_vistos() -> set:
    try:
        with open(ARQUIVO_VISTOS, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def salvar_vistos(vistos: set):
    with open(ARQUIVO_VISTOS, "w", encoding="utf-8") as f:
        json.dump(sorted(vistos), f, ensure_ascii=False, indent=2)

def id_imovel(im: Imovel) -> str:
    return im.link if im.link else f"{im.fonte}|{im.titulo[:40]}|{im.preco}"


# ══════════════════════════════════════════════════════
#  WHATSAPP via CallMeBot
# ══════════════════════════════════════════════════════
def enviar_whatsapp(mensagem: str) -> bool:
    numero = CONFIG["whatsapp_numero"].replace("+", "")
    apikey = CONFIG["callmebot_apikey"]
    url    = (
        f"https://api.callmebot.com/whatsapp.php"
        f"?phone={numero}&text={requests.utils.quote(mensagem)}&apikey={apikey}"
    )
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200:
            log.info("✅ WhatsApp enviado!")
            return True
        log.error(f"❌ CallMeBot retornou {resp.status_code}: {resp.text[:100]}")
        return False
    except Exception as e:
        log.error(f"❌ Falha ao enviar WhatsApp: {e}")
        return False


# ══════════════════════════════════════════════════════
#  MENSAGENS DA BRISA  🌊  (tom carioca e acolhedor)
# ══════════════════════════════════════════════════════

_SAUDACOES_RESUMO = [
    "Eita, que dia cheio de oportunidade, hein!",
    "Olha só o que eu garimpei pra você hoje! 🔍",
    "Bom dia! Tô chegando com novidade boa, não!",
    "Separei um cardápio bacana de apê pra você analisar!",
    "Achei uns imóveis bem interessantes hoje, dá uma olhada!",
    "Fiz minha rodinha pelos sites e trouxe o melhor pra você!",
    "Hoje tem opção boa no radar, vai lá conferir com calma! 😎",
    "Acordei cedo e já fui garimpando pra você, olha o resultado!",
]

_SEM_NOVIDADE = [
    "Eita, hoje o mercado tá quietinho por aqui… Mas não desanima não, amanhã cedo eu já tô de volta na missão! 🌊",
    "Passei em tudo e não rolou nada novo hoje. Mas pode deixar, tô de olho! 👀",
    "O Rio tá segurando as novidades hoje, mas amanhã a Brisa volta com tudo! 🌊",
    "Nada novo nos sites hoje. Fica tranquilo que eu aviso assim que aparecer! ✨",
    "Dei uma varredura geral e o mercado tá parado hoje. Mas não me preocupa, eu tô de plantão! 🏄",
]

def montar_alerta_novo(im: Imovel) -> str:
    """Alerta imediato — tom animado, carioca."""
    return (
        f"🚨 *Brisa aqui! Chegou imóvel novo!* 🌊\n"
        f"{'─' * 32}\n"
        f"Acabei de achar esse apê e já vim te contar:\n\n"
        f"{im.formatar_whatsapp()}"
        f"{'─' * 32}\n"
        f"_Corre lá dar uma olhada enquanto tá fresquinho! 😄_\n"
        f"🤖 _Brisa · Monitora de Imóveis_"
    )

def montar_resumo_diario(imoveis: list) -> str:
    """Resumo diário com até 10 imóveis — tom acolhedor e organizado."""
    hoje     = datetime.now().strftime("%d/%m/%Y")
    total    = len(imoveis)
    raio     = int(CONFIG["raio_km"] * 1000)
    max_d    = CONFIG["max_resumo_diario"]
    saudacao = random.choice(_SAUDACOES_RESUMO)

    if total == 0:
        return (
            f"🌊 *Brisa · Resumo do dia {hoje}*\n\n"
            f"{random.choice(_SEM_NOVIDADE)}"
        )

    exibir   = imoveis[:max_d]
    restante = total - len(exibir)

    cabecalho = (
        f"🌊 *Brisa · Resumo do dia {hoje}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"_{saudacao}_\n\n"
        f"📊 *{len(exibir)} imóvel(is)* selecionado(s) pra você analisar com calma\n"
        f"💰 Até R$ {CONFIG['preco_maximo']:,.0f}  |  🛏 {CONFIG['quartos_minimo']}+ quartos\n"
        f"🚇 Raio de {raio}m dos metrôs · Zona Sul & Tijuca\n"
        f"{'─' * 32}\n\n"
    )

    corpo = ""
    for i, im in enumerate(exibir, 1):
        corpo += f"*#{i} · {im.fonte}*\n"
        corpo += im.formatar_whatsapp()
        corpo += "\n"

    rodape = ""
    if restante > 0:
        rodape = f"_...e mais {restante} imóvel(is) nos alertas do dia. Fique ligado! 👀_\n\n"
    rodape += "🤖 _Brisa · Monitora de Imóveis · Rio de Janeiro_"

    return cabecalho + corpo + rodape


# ══════════════════════════════════════════════════════
#  COLETA GERAL
# ══════════════════════════════════════════════════════
def coletar_e_filtrar() -> list:
    todos = []
    for scraper in SCRAPERS:
        try:
            todos += scraper()
        except Exception as e:
            log.error(f"Scraper {scraper.__name__} falhou: {e}")
        time.sleep(2)
    log.info(f"Total bruto: {len(todos)}")
    filtrados = filtrar(todos)
    filtrados.sort(key=lambda x: x.preco)
    log.info(f"Após filtros: {len(filtrados)}")
    return filtrados


# ══════════════════════════════════════════════════════
#  MODO 1 · Verificação em tempo real
# ══════════════════════════════════════════════════════
def verificar_novos():
    log.info("─" * 40)
    log.info("🔍 Brisa verificando novos imóveis...")
    vistos    = carregar_vistos()
    filtrados = coletar_e_filtrar()
    novos     = [im for im in filtrados if id_imovel(im) not in vistos]

    if novos:
        log.info(f"🚨 {len(novos)} novo(s) encontrado(s)!")
        for im in novos:
            enviar_whatsapp(montar_alerta_novo(im))
            time.sleep(4)
    else:
        log.info("Nenhum imóvel novo desta rodada.")

    for im in filtrados:
        vistos.add(id_imovel(im))
    salvar_vistos(vistos)


# ══════════════════════════════════════════════════════
#  MODO 2 · Resumo diário (até 10 imóveis)
# ══════════════════════════════════════════════════════
def enviar_resumo_diario():
    log.info("─" * 40)
    log.info("📋 Brisa gerando resumo diário...")
    filtrados = coletar_e_filtrar()
    enviar_whatsapp(montar_resumo_diario(filtrados))
    log.info("✅ Resumo diário enviado!")


# ══════════════════════════════════════════════════════
#  EXECUÇÃO PRINCIPAL
# ══════════════════════════════════════════════════════
if __name__ == "__main__":
    import schedule

    log.info("═" * 50)
    log.info("🌊  BRISA · Monitora de Imóveis — Iniciando")
    log.info(f"   ⏱  Tempo real   : a cada {CONFIG['intervalo_tempo_real_min']} min")
    log.info(f"   📋 Resumo diário : {CONFIG['horario_resumo_diario']} (máx. {CONFIG['max_resumo_diario']} imóveis)")
    log.info(f"   🚇 {len(CONFIG['pontos_referencia'])} metrôs monitorados · raio {CONFIG['raio_km']}km")
    log.info(f"   🔌 {len(SCRAPERS)} site(s): {', '.join(s.__name__.replace('scrape_','') for s in SCRAPERS)}")
    log.info("═" * 50)

    schedule.every(CONFIG["intervalo_tempo_real_min"]).minutes.do(verificar_novos)
    schedule.every().day.at(CONFIG["horario_resumo_diario"]).do(enviar_resumo_diario)

    verificar_novos()  # primeira execução imediata

    while True:
        schedule.run_pending()
        time.sleep(60)
