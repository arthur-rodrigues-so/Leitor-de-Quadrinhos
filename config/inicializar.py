"""
===================================================================================
 GERA HASH DO ARQUIVO CACHE, 
 CRIA TODAS AS PASTAS OBRIGATORIAS PARA FUNCIONAMENTO,
 OBTEM CAMINHO DO ICONE
===================================================================================
"""
import os
import sys
import hashlib

from config.constantes import PASTA_CACHE, PASTA_HISTORICO, DIR_DADOS

def obter_hash_caminho(caminho: str) -> str:
    """Gera um hash MD5 seguro para ser utilizado como nome de arquivo no cache."""
    return hashlib.md5(caminho.encode('utf-8')).hexdigest()

def inicializar_pastas():
    """Garante que as pastas de cache e histórico existam de forma segura."""
    try:
        os.makedirs(DIR_DADOS, exist_ok=True)
        os.makedirs(PASTA_CACHE, exist_ok=True)
        os.makedirs(PASTA_HISTORICO, exist_ok=True)
    except PermissionError:
        print(f"[ERRO] Sem permissão para criar pastas de cache em: {DIR_DADOS}")
        raise

def caminho_absoluto_pasta_executando(relative_path):
    """
    Obtém o caminho absoluto para recursos, funcionando para dev e para o PyInstaller.
    """
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    return os.path.join(base_path, relative_path)