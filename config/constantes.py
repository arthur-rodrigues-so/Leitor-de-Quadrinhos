"""
==============================================================================
CONFIGURAÇÕES GERAIS
==============================================================================
DIR_BASE: pasta raiz do projeto \n
DIR_DADOS: pasta onde ficam os dados dinamicos \n

CONFIG_DADOS: arquivo JSON onde fica as configurações:
 *RAIZ_ACERVO: caminho completo de onde está os quadrinhos\n
 *EDITORIAS_FIXAS: tags padrão dos quadrinho\n
 *MAPA_PASTA_EDITORAS: imbue as editoras fixas com base no nome de pastas dentro da RAIZ_ACERVO\n

BANCO_DADOS: caminho onde fica o arquivo do banco de dados\n
PASTA_CACHE e PASTA_HISTORICO: para guardar a primeira imagem de cada quadrinho e acessar mais rapido\n

COLUNAS E LINHAS: matriz da organização dos quadrinhos na tela inicial\n
ITENS_POR_PAGINA: multiplicação das colunas pelas linhas\n

 EXTENSOES_IMAGEM: tipo de extensões aceitas para serem lidas como imagem e permitir leitura\n
 EXTENSOES_ARQUIVOS_HQ: extensoes permitidas para serem reconhecidos como quadrinhos e aparecerem na tela inicial\n
"""

import os
import sys

# ==============================================================================
#       CONSEGUIR O CAMINHO BASE DO DIRETORIO
# ==============================================================================
# def caminho_pasta():
#     """Retorna o diretório onde o executável está rodando ou onde o script está."""
#     if getattr(sys, 'frozen', False):
#         return os.path.dirname(sys.executable)
#     else:
#         return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def caminho_absoluto_pasta_executando(relative_path):
    """
    Obtém o caminho absoluto para recursos, funcionando para dev e para o PyInstaller.
    """
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    return os.path.join(base_path, relative_path)


# ==============================================================================
#       CONSTANTES
# ==============================================================================
DIR_BASE = caminho_absoluto_pasta_executando("")
DIR_DADOS = os.path.join(DIR_BASE, ".local_files")

CONFIG_DADOS = os.path.join(DIR_DADOS, "config.json")
BANCO_DADOS = os.path.join(DIR_DADOS, "banco.db")
PASTA_CACHE = os.path.join(DIR_DADOS, ".cache_hqs")
PASTA_HISTORICO = os.path.join(PASTA_CACHE, "historico_permanente")

COLUNAS_GRID = 7
LINHAS_GRID = 3
ITENS_POR_PAGINA = COLUNAS_GRID * LINHAS_GRID

EXTENSOES_IMAGEM = ('.jpg', '.jpeg', '.png', '.webp', '.bmp')
EXTENSOES_ARQUIVOS_HQ = EXTENSOES_IMAGEM + ('.cbr', '.cbz', '.zip', '.rar', '.7z')
CACHE_RAM_CAPAS = {}

LARGURA_ALVO_CARD = 160     # largura "ideal" do card quadrinhos (aumente para capas maiores)
LARGURA_MIN_CARD = 112      # largura minima do card quadrinhos
LARGURA_MAX_CARD = 240      # largura maxima do card quadrinhos
LARGURA_MAX_MANUAL = 280    # no modo manual o card pode ficar um pouco maior
PAD_GRADE = 4               # espaço de cada lado do card
LARGURA_SIDEBAR = 270       # igual ao configurar_layout
RESERVA_LARGURA = 8 + 28    # padx da área rolável + barra de rolagem
RESERVA_ALTURA = 76         # barra de paginação (48) + margens; aumente se algum card ainda ficar cortado
EXTRA_ALTURA_CARD = 90     # chute inicial da altura de textos do card (é medido e corrigido sozinho)
VELOCIDADE_SCROLL = 8      # px por "unidade"; no Windows uma volta da roda = 20 unidades (8 -> 160px)
DEBOUNCE_MS = 150

PROPORCAO_CAPA = 1.5
MARGEM_HORIZONTAL = 2 * (2 + 4)


# ------------------------------------------------------------------
# PALETA E TIPOGRAFIA (tudo local ao método, nada vaza para a classe)
# ------------------------------------------------------------------
BG_APP       = "#0d0e12"   # área principal
BG_SIDEBAR   = "#14151b"   # barra lateral
BG_CARD      = "#1a1c24"   # cards internos
BG_INPUT     = "#20222c"   # campos / botões secundários
BG_INPUT_HOV = "#2a2d3a"
BORDER       = "#2a2d3a"
ACCENT       = "#4c8dff"
ACCENT_HOV   = "#3a76e0"
TEXT         = "#e6e8ee"
TEXT_MUTED   = "#8b90a0"

FONT_FAMILY = "Segoe UI"
PAD_X = 14   # margem lateral da sidebar
PAD_C = 12   # margem interna dos cards
RADIUS = 8