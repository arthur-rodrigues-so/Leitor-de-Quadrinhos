"""
==============================================================================
 CONFIGURAÇÕES DO SISTEMA - Qt
==============================================================================
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QVBoxLayout, QWidget,
)

from service.configuracoes import normalizar_config_grade, LIMITE_LINHAS, LIMITE_COLUNAS
from view.estilo import BTN_PADRAO, BTN_PADRAO_HOVER, cor_texto, qss_botao, qss_entry
from view.widgets import ScrollAreaRapida, SegmentedButton


def _arial(pontos: int, negrito: bool = False) -> QFont:
    """O modal original usava Arial com tamanho em pontos (tuplas do Tk)."""
    f = QFont("Arial")
    f.setPointSize(pontos)
    f.setBold(negrito)
    return f


class ConfiguracoesModal(QDialog):
    """Abra com .exec(). `funcao_salvar_callback(novos_dados)` é chamada ao salvar."""

    def __init__(self, parent, funcao_salvar_callback, configs_atuais=None):
        super().__init__(parent)

        self.funcao_salvar_callback = funcao_salvar_callback
        self.configs_atuais = configs_atuais or {}

        self.setWindowTitle("Configurações do Sistema - Gerenciador de HQs")
        # Altura limitada pela tela (em pixels lógicos): em monitores com escala de DPI
        # alta o espaço útil é pequeno, então o conteúdo rola e o botão Salvar fica fixo.
        tela = self.screen() or parent.screen()
        altura = min(700, max(420, tela.geometry().height() - 110))
        self.setFixedSize(580, altura)
        self.setModal(True)

        principal = QVBoxLayout(self)
        principal.setContentsMargins(0, 0, 0, 0)
        principal.setSpacing(0)

        # Corpo rolável com todas as seções
        self.corpo = ScrollAreaRapida()
        conteudo = QWidget()
        self._lay = QVBoxLayout(conteudo)
        self._lay.setContentsMargins(25, 0, 25, 8)
        self._lay.setSpacing(0)
        self.corpo.setWidget(conteudo)
        principal.addWidget(self.corpo, 1)

        # Botão Salvar fixo na base
        self.btn_salvar = QPushButton("Salvar Configurações")
        self.btn_salvar.setFixedSize(220, 45)
        self.btn_salvar.setFont(_arial(13))
        self.btn_salvar.setStyleSheet(qss_botao(BTN_PADRAO, BTN_PADRAO_HOVER, "#ffffff", raio=8))
        self.btn_salvar.clicked.connect(self.processar_e_salvar)
        principal.addSpacing(10)
        principal.addWidget(self.btn_salvar, 0, Qt.AlignmentFlag.AlignHCenter)
        principal.addSpacing(16)

        # ==========================
        # 1. SEÇÃO: PASTA RAIZ
        # ==========================
        self._titulo("1. Pasta Raiz do Acervo")
        self._descricao("Selecione a pasta principal onde estão armazenadas todas as suas HQs e subpastas.")

        self.frame_raiz = QWidget()
        lay_raiz = QHBoxLayout(self.frame_raiz)
        lay_raiz.setContentsMargins(0, 0, 0, 0)
        lay_raiz.setSpacing(10)

        self.entry_pasta = QLineEdit()
        self.entry_pasta.setFixedHeight(35)
        self.entry_pasta.setStyleSheet(qss_entry())
        # Preenche com o valor atual ou um padrão sugerido
        self.entry_pasta.setText(self.configs_atuais.get("pasta_raiz", r"D:\Emulador\HQ"))
        lay_raiz.addWidget(self.entry_pasta, 1)

        self.btn_explorar = QPushButton("Procurar...")
        self.btn_explorar.setFixedSize(110, 35)
        self.btn_explorar.setFont(_arial(11))
        self.btn_explorar.setStyleSheet(qss_botao(BTN_PADRAO, BTN_PADRAO_HOVER, "#ffffff", raio=6))
        self.btn_explorar.clicked.connect(self.escolher_pasta)
        lay_raiz.addWidget(self.btn_explorar)
        self._lay.addWidget(self.frame_raiz)
        self._lay.addSpacing(5)

        # ==========================
        # 2. SEÇÃO: EDITORAS FIXAS
        # ==========================
        self._titulo("2. Editoras Atendidas")
        self._descricao("Digite os nomes das editoras separados por vírgula.")

        self.entry_editoras = QLineEdit()
        self.entry_editoras.setFixedHeight(35)
        self.entry_editoras.setStyleSheet(qss_entry())
        # Converte a lista atual em uma string separada por vírgula para o usuário editar
        editoras_atuais = self.configs_atuais.get("editoras", ["MARVEL", "DC", "VERTIGO", "DYNAMITE"])
        self.entry_editoras.setText(", ".join(editoras_atuais))
        self._lay.addWidget(self.entry_editoras)
        self._lay.addSpacing(5)

        # ==========================
        # 3. SEÇÃO: MAPA DE PASTAS
        # ==========================
        self._titulo("3. Mapeamento de Pastas")
        self._descricao("Relacione o nome da pasta física do seu computador com a respectiva editora.\n"
                        "Formato padrão:\n NOME_PASTA_DISCO_EM_DISCO:EDITORA (uma por linha).")

        self.textbox_mapa = QPlainTextEdit()
        self.textbox_mapa.setFixedHeight(100)
        mapa_atual = self.configs_atuais.get("mapa_pastas_editoras", {
            "COLETANIA MARVEL": "MARVEL",
            "COLETANIA DC": "DC",
            "COLETANIA VERTIGO": "VERTIGO",
            "COLETANIA DYNAMITE": "DYNAMITE"
        })
        texto_mapa_formatado = "\n".join([f"{pasta} : {editora}" for pasta, editora in mapa_atual.items()])
        self.textbox_mapa.setPlainText(texto_mapa_formatado)
        self._lay.addWidget(self.textbox_mapa)
        self._lay.addSpacing(5)

        # ==========================
        # 4. SEÇÃO: GRADE DE QUADRINHOS
        # ==========================
        grade_atual = normalizar_config_grade(self.configs_atuais.get("grade"))

        self._titulo("4. Grade de Quadrinhos")
        self._descricao("Automático: mostra só as linhas que cabem inteiras na janela.\n"
                        "Manual: você escolhe quantas linhas e colunas aparecem por página.")

        self.seg_modo_grade = SegmentedButton(["Automático", "Manual"], command=self._ao_mudar_modo_grade,
                                              altura=32, largura_fixa=240)
        self._lay.addWidget(self.seg_modo_grade, 0, Qt.AlignmentFlag.AlignLeft)
        self._lay.addSpacing(5)

        self.frame_grade_manual = QWidget()
        lay_manual = QHBoxLayout(self.frame_grade_manual)
        lay_manual.setContentsMargins(0, 0, 0, 0)
        lay_manual.setSpacing(0)

        lbl_linhas = QLabel("Linhas:")
        lbl_linhas.setFont(_arial(12))
        lay_manual.addWidget(lbl_linhas)
        lay_manual.addSpacing(6)
        self.entry_linhas = QLineEdit(str(grade_atual["linhas"]))
        self.entry_linhas.setFixedSize(60, 32)
        self.entry_linhas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.entry_linhas.setStyleSheet(qss_entry())
        lay_manual.addWidget(self.entry_linhas)
        lay_manual.addSpacing(18)

        lbl_colunas = QLabel("Colunas:")
        lbl_colunas.setFont(_arial(12))
        lay_manual.addWidget(lbl_colunas)
        lay_manual.addSpacing(6)
        self.entry_colunas = QLineEdit(str(grade_atual["colunas"]))
        self.entry_colunas.setFixedSize(60, 32)
        self.entry_colunas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.entry_colunas.setStyleSheet(qss_entry())
        lay_manual.addWidget(self.entry_colunas)
        lay_manual.addStretch(1)
        self._lay.addWidget(self.frame_grade_manual)
        self._lay.addSpacing(2)

        self.lbl_erro_grade = QLabel("")
        self.lbl_erro_grade.setFont(_arial(11))
        cor_texto(self.lbl_erro_grade, "#ff6b6b")
        self._lay.addWidget(self.lbl_erro_grade)
        self._lay.addStretch(1)

        modo_inicial = "Manual" if grade_atual["modo"] == "manual" else "Automático"
        self.seg_modo_grade.set(modo_inicial)
        self._ao_mudar_modo_grade(modo_inicial)

    # ------------------------------------------------------------------
    # Helpers de montagem
    # ------------------------------------------------------------------
    def _titulo(self, texto: str):
        lbl = QLabel(texto)
        lbl.setFont(_arial(14, negrito=True))
        self._lay.addSpacing(20)
        self._lay.addWidget(lbl)
        self._lay.addSpacing(2)
        return lbl

    def _descricao(self, texto: str):
        lbl = QLabel(texto)
        lbl.setFont(_arial(11))
        lbl.setWordWrap(True)
        cor_texto(lbl, "gray")
        self._lay.addWidget(lbl)
        self._lay.addSpacing(5)
        return lbl

    # ------------------------------------------------------------------
    # Grade
    # ------------------------------------------------------------------
    def _ao_mudar_modo_grade(self, valor):
        """Linhas/colunas só podem ser editadas no modo manual."""
        habilitado = valor == "Manual"
        self.entry_linhas.setEnabled(habilitado)
        self.entry_colunas.setEnabled(habilitado)
        self.lbl_erro_grade.setText("")

    def _ler_grade(self):
        """
        Devolve (config_grade, mensagem_de_erro).
        No modo automático, valores inválidos viram os últimos válidos/padrão (sem erro).
        """
        manual = self.seg_modo_grade.get() == "Manual"
        try:
            linhas = int(self.entry_linhas.text().strip())
            colunas = int(self.entry_colunas.text().strip())
        except ValueError:
            if manual:
                return None, "Informe números inteiros para linhas e colunas."
            return normalizar_config_grade({"modo": "automatico"}), ""

        if manual and not (LIMITE_LINHAS[0] <= linhas <= LIMITE_LINHAS[1]):
            return None, f"Linhas deve estar entre {LIMITE_LINHAS[0]} e {LIMITE_LINHAS[1]}."
        if manual and not (LIMITE_COLUNAS[0] <= colunas <= LIMITE_COLUNAS[1]):
            return None, f"Colunas deve estar entre {LIMITE_COLUNAS[0]} e {LIMITE_COLUNAS[1]}."

        return normalizar_config_grade(
            {"modo": "manual" if manual else "automatico", "linhas": linhas, "colunas": colunas}
        ), ""

    # ------------------------------------------------------------------
    # Ações
    # ------------------------------------------------------------------
    def escolher_pasta(self):
        """Abre a janela nativa do sistema para selecionar a pasta raiz"""
        caminho_selecionado = QFileDialog.getExistingDirectory(self, "Selecione a pasta raiz")
        if caminho_selecionado:
            self.entry_pasta.setText(caminho_selecionado)

    def processar_e_salvar(self):
        """Lê os dados da tela, converte para os tipos corretos e envia para o callback"""

        # 1. Pega a pasta raiz
        pasta_raiz = self.entry_pasta.text().strip()

        # 2. Transforma o texto separado por vírgula em uma lista de strings limpas
        texto_editoras = self.entry_editoras.text()
        lista_editoras = [e.strip().upper() for e in texto_editoras.split(",") if e.strip()]

        # 3. Lê a caixa de texto e reconstrói o dicionário de mapeamento
        linhas_mapa = self.textbox_mapa.toPlainText().split("\n")
        novo_mapa = {}

        for linha in linhas_mapa:
            if ":" in linha:
                partes = linha.split(":")
                pasta_disco = partes[0].strip().upper()
                nome_editora = partes[1].strip().upper()
                if pasta_disco and nome_editora:
                    novo_mapa[pasta_disco] = nome_editora

        # 4. Grade de quadrinhos (valida antes de fechar a janela)
        config_grade, erro_grade = self._ler_grade()
        if config_grade is None:
            self.lbl_erro_grade.setText(erro_grade)
            return

        # Monta o dicionário final no formato exato que o seu config.json espera
        novos_dados = {
            "pasta_raiz": pasta_raiz,
            "editoras": lista_editoras,
            "mapa_pastas_editoras": novo_mapa,
            "grade": config_grade
        }

        # Envia para a função de salvamento externa que você já criou
        self.funcao_salvar_callback(novos_dados)

        # Fecha a modal
        self.accept()
