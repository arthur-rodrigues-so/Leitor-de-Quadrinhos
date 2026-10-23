import os
def abrir_arquivo_externo(caminho_arquivo: str):
    """Abre qualquer arquivo ou pasta usando o visualizador padrão do sistema operacional."""
    if caminho_arquivo and os.path.exists(caminho_arquivo):
        try:
            os.startfile(caminho_arquivo)
        except Exception as e:
            print(f"[ERRO SISTEMA] Falha ao abrir arquivo externamente: {e}")