import os
import re
from typing import List, Tuple, Optional
from config.constantes import EXTENSOES_IMAGEM

def obter_imagens_da_pasta(caminho_pasta: str) -> List[str]:
    """
    Retorna a lista ordenada de caminhos completos de imagens válidas de uma pasta.
    Usada pelo Escaneador do Acervo e pelo Leitor de Quadrinhos.
    """
    if not caminho_pasta or not os.path.exists(caminho_pasta):
        return []
    try:
        arquivos = sorted(os.listdir(caminho_pasta))
        return [
            os.path.join(caminho_pasta, f) 
            for f in arquivos 
            if f.lower().endswith(EXTENSOES_IMAGEM)
        ]
    except Exception:
        return []

def extrair_metadados_pasta(nome_pasta: str) -> Tuple[str, Optional[int], bool]:
    """
    Extrai título limpo, ano de publicação e status de descompactação a partir do nome da pasta.
    
    :return: (titulo_limpo, ano_detectado, eh_descompactada)
    """
    eh_descompactada = bool(re.search(r'\(descompactada\)', nome_pasta, re.IGNORECASE))
    titulo_limpo = re.sub(r'\(descompactada\)', '', nome_pasta, flags=re.IGNORECASE).strip()

    match_ano = re.match(r'^(\d{4})\s*-\s*', titulo_limpo) or re.search(r'\b(19\d\d|20\d\d)\b', titulo_limpo)
    ano_detectado = int(match_ano.group(1)) if match_ano else None

    return titulo_limpo, ano_detectado, eh_descompactada