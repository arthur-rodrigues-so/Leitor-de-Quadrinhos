"""
==============================================================================
 MINIATURAS DAS CAPAS
==============================================================================
"""
import os

from PIL import Image
from typing import Optional
from functools import lru_cache

from PySide6.QtGui import QImage, QPixmap

from config.constantes import PASTA_CACHE
from config.inicializar import obter_hash_caminho

# Resolução das miniaturas em disco. Deve ser >= à maior largura de card
# (LARGURA_MAX_MANUAL ~ 280px, mais folga para telas com escala de DPI).
MINIATURA_MAX = (320, 480)

# O tamanho entra no nome do arquivo (igual ao original).
_SUFIXO = f"{MINIATURA_MAX[0]}x{MINIATURA_MAX[1]}"


def _pil_para_qimage(img: Image.Image) -> QImage:
    img = img.convert("RGB")
    largura, altura = img.size
    return QImage(img.tobytes("raw", "RGB"), largura, altura, largura * 3,
                  QImage.Format.Format_RGB888).copy()


# O cache guarda apenas o QImage (somente leitura, pode ser compartilhado).
# 320x480 RGB ocupa ~460 KB; 150 itens ~ 70 MB (cobre páginas de até 60 cards).
@lru_cache(maxsize=150)
def _carregar_qimage_miniatura(caminho_identificador: str, caminho_capa: Optional[str]) -> Optional[QImage]:
    if not caminho_capa:
        return None

    caminho_hash = obter_hash_caminho(caminho_identificador)
    caminho_thumb = os.path.join(PASTA_CACHE, f"{caminho_hash}_{_SUFIXO}.jpg")

    try:
        # Se a thumbnail já foi gerada no disco anteriormente:
        if os.path.exists(caminho_thumb):
            imagem = QImage(caminho_thumb)  # leitura nativa do Qt
            if not imagem.isNull():
                return imagem
            with Image.open(caminho_thumb) as img:
                return _pil_para_qimage(img)

        if not os.path.exists(caminho_capa):
            return None

        with Image.open(caminho_capa) as img_orig:
            img_orig.draft("RGB", (MINIATURA_MAX[0] * 2, MINIATURA_MAX[1] * 2))
            pil_thumb = img_orig.convert("RGB")

        # Gerada uma única vez e guardada em disco, então vale usar LANCZOS (melhor qualidade).
        pil_thumb.thumbnail(MINIATURA_MAX, Image.Resampling.LANCZOS)
        pil_thumb.save(caminho_thumb, "JPEG", quality=85, optimize=False)
        return _pil_para_qimage(pil_thumb)

    except Exception as e:
        print(f"[ERRO CACHE] Falha ao carregar miniatura ({caminho_capa}): {e}")
        return None


def carregar_miniatura_otimizada(caminho_identificador: str, caminho_capa: Optional[str]) -> Optional[QPixmap]:
    """Devolve um QPixmap novo a cada chamada (um por card), ou None se não houver capa."""
    imagem = _carregar_qimage_miniatura(caminho_identificador, caminho_capa)
    if imagem is None:
        return None
    return QPixmap.fromImage(imagem)
