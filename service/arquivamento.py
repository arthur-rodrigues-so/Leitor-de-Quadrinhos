# servicos/arquivamento.py
import os
import shutil
from PIL import Image
from config.inicializar import obter_hash_caminho
from config.constantes import PASTA_HISTORICO

def processar_arquivamento_fisico(quadrinho_id: int, caminho_capa: str, caminho_pasta: str) -> str | None:
    """
    Copia a capa para o histórico permanente e apaga a pasta descompactada para liberar espaço.
    Retorna o novo caminho da capa no histórico.
    """
    nova_capa = None

    if caminho_capa and os.path.exists(caminho_capa):
        hash_id = obter_hash_caminho(f"historico_{quadrinho_id}")
        nova_capa = os.path.join(PASTA_HISTORICO, f"{hash_id}.jpg")
        try:
            with Image.open(caminho_capa) as img:
                img.convert("RGB").save(nova_capa, "JPEG", quality=85)
        except Exception as e:
            print(f"[ERRO ARQUIVAMENTO] Falha ao salvar capa de histórico: {e}")

    if caminho_pasta and os.path.exists(caminho_pasta):
        try:
            shutil.rmtree(caminho_pasta)
        except Exception as e:
            print(f"[ERRO ARQUIVAMENTO] Falha ao deletar pasta {caminho_pasta}: {e}")

    return nova_capa