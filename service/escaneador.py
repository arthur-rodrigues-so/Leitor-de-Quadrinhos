# servicos/escaneador.py
import os
from config.constantes import  EXTENSOES_ARQUIVOS_HQ
from service.leitor_arquivos import obter_imagens_da_pasta, extrair_metadados_pasta

def sincronizar_acervo_disco_com_banco(db_manager, RAIZ_ACERVO, MAPA_PASTAS_EDITORAS) -> int:
    """
    Varre o disco, registra novos quadrinhos e remove os obsoletos.
    Retorna a quantidade de quadrinhos válidos encontrados.
    """
    if not os.path.exists(RAIZ_ACERVO):
        return 0

    caminhos_validos = set()

    for pasta_editoras, tag_editoras in MAPA_PASTAS_EDITORAS.items():
        caminho_editoras = os.path.join(RAIZ_ACERVO, pasta_editoras)
        if not os.path.isdir(caminho_editoras):
            continue

        for root, _, arquivos in os.walk(caminho_editoras):
            if any(f.lower().endswith(EXTENSOES_ARQUIVOS_HQ) for f in arquivos):
                caminhos_validos.add(root)
                nome_pasta = os.path.basename(root)

                titulo_limpo, ano_detectado, eh_descompactada = extrair_metadados_pasta(nome_pasta)
                imagens = obter_imagens_da_pasta(root)
                capa = imagens[0] if imagens else None

                db_manager.salvar_ou_migrar_quadrinho(
                    caminho=root,
                    caminho_capa=capa,
                    titulo=titulo_limpo,
                    editora=tag_editoras,
                    ano=ano_detectado,
                    total_pags=len(imagens),
                    descompactada=eh_descompactada,
                    tem_imagens=bool(imagens)
                )

    db_manager.limpar_pastas_obsoletas(caminhos_validos)
    return len(caminhos_validos)