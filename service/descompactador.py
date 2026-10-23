import subprocess
import os.path

from PySide6.QtCore import QProcess

from config.constantes import DIR_DADOS
from config.inicializar import caminho_absoluto_pasta_executando
# ==============================================================================
# CONFIGURAÇÃO DE CAMINHOS
# ==============================================================================
DIRETORIO_PROJETO = caminho_absoluto_pasta_executando("c")
PASTA_LOCAL_FILES = DIR_DADOS 


EXECUTAVEL_C = os.path.join(PASTA_LOCAL_FILES, "descompactador.exe")

PASTA_C = os.path.join(DIRETORIO_PROJETO) 

# Controle do processo ativo
processo_descompactador = None


# ==============================================================================
# COMPILAÇÃO AUTOMÁTICA (CASO NÃO EXISTA EM .local_files)
# ==============================================================================
def verificar_ou_compilar():
    """Garante que o executável exista; se não, compila com o comando especificado."""
    if os.path.exists(EXECUTAVEL_C):
        return True

    print("[BUILD] descompactador.exe não encontrado em .local_files. Compilando...")

    if not os.path.exists(PASTA_C):
        print(f"[Erro] Pasta C não encontrada em: {PASTA_C}")
        return False

    comando = [
        "gcc",
        "main.c",
        "extrator.c",
        "-o",
        str(EXECUTAVEL_C),
        "-lraylib",
        "-larchive",
        "-lshlwapi"
    ]

    try:
        subprocess.run(
            comando,
            cwd=str(PASTA_C),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        print(f"[BUILD] Sucesso! Executável criado em: {EXECUTAVEL_C}")
        return True
    except Exception as e:
        print(f"[Erro de Compilação] Falha ao compilar: {e}")
        return False

# ==============================================================================
# CONTROLE DE ABERTURA E FECHAMENTO
# ==============================================================================
def abrir_descompactador(ligar, switch_ui=None):
    global processo_descompactador
    
    # Se o usuário desligou o switch ou pediu para fechar
    if not ligar:
        if processo_descompactador is not None and processo_descompactador.state() == QProcess.Running:
            processo_descompactador.terminate()
            processo_descompactador.waitForFinished(2000)
        processo_descompactador = None
        return

    # Se já estiver rodando, não abre de novo
    if processo_descompactador is not None and processo_descompactador.state() == QProcess.Running:
        return

    # Garante que o executável existe antes de abrir
    if not verificar_ou_compilar():
        if switch_ui:
            switch_ui.blockSignals(True)
            switch_ui.setChecked(False)
            switch_ui.blockSignals(False)
        return

    # Abre o executável usando QProcess para monitorar o "X"
    processo_descompactador = QProcess()
    
    if switch_ui is not None:
        # Quando fechar pelo X, limpa a variável e joga o switch para False (cinza)
        processo_descompactador.finished.connect(lambda: _desincronizar_switch(switch_ui))

    processo_descompactador.start(str(EXECUTAVEL_C))


def _desincronizar_switch(switch_ui):
    global processo_descompactador
    
    
    if switch_ui:
        switch_ui.blockSignals(True)
        switch_ui.setChecked(False)
        switch_ui.blockSignals(False)
        
    processo_descompactador = None