import json
from config.constantes import CONFIG_DADOS, COLUNAS_GRID, LINHAS_GRID

RAIZ_ACERVO = None
EDITORAS_FIXAS = None
MAPA_PASTAS_EDITORAS = None

def carregar_configuracoes():
    try:
        with open(CONFIG_DADOS, mode="r", encoding="utf-8") as arquivo:
            configuracoes = json.load(arquivo)
    
        RAIZ_ACERVO = configuracoes['pasta_raiz']
        EDITORAS_FIXAS = configuracoes['editoras']
        MAPA_PASTAS_EDITORAS = configuracoes['mapa_pastas_editoras']

        return RAIZ_ACERVO, EDITORAS_FIXAS, MAPA_PASTAS_EDITORAS
    
    except (FileNotFoundError, json.JSONDecodeError):
        raise

def salvar_configuracoes(dados_para_salvar=None):
    with open(CONFIG_DADOS, mode="w", encoding="utf-8") as arquivo:
        json.dump(dados_para_salvar, arquivo, ensure_ascii=False, indent=4)


# ==============================================================================
# GRADE DE QUADRINHOS (modo automático ou manual)
# ==============================================================================
GRADE_PADRAO = {"modo": "automatico", "linhas": LINHAS_GRID, "colunas": COLUNAS_GRID}
LIMITE_LINHAS = (1, 10)
LIMITE_COLUNAS = (1, 12)


def normalizar_config_grade(bruto=None) -> dict:
    """Aceita qualquer valor vindo do JSON e devolve sempre uma config de grade válida."""
    bruto = bruto if isinstance(bruto, dict) else {}

    def _inteiro(valor, padrao, limites):
        try:
            valor = int(valor)
        except (TypeError, ValueError):
            return padrao
        return max(limites[0], min(limites[1], valor))

    modo = bruto.get("modo")
    return {
        "modo": modo if modo in ("automatico", "manual") else "automatico",
        "linhas": _inteiro(bruto.get("linhas"), GRADE_PADRAO["linhas"], LIMITE_LINHAS),
        "colunas": _inteiro(bruto.get("colunas"), GRADE_PADRAO["colunas"], LIMITE_COLUNAS),
    }


def carregar_config_grade() -> dict:
    """Lê a seção "grade" do config.json; se faltar, usa o modo automático."""
    try:
        with open(CONFIG_DADOS, mode="r", encoding="utf-8") as arquivo:
            configuracoes = json.load(arquivo)
        return normalizar_config_grade(configuracoes.get("grade"))
    except (FileNotFoundError, json.JSONDecodeError):
        return normalizar_config_grade(None)
