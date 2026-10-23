from config.constantes import RESERVA_ALTURA, RESERVA_LARGURA, PAD_GRADE, LARGURA_MIN_CARD, LARGURA_MAX_CARD, LARGURA_MAX_MANUAL, LARGURA_ALVO_CARD, PROPORCAO_CAPA, MARGEM_HORIZONTAL

def calcular_grade(largura_area, 
                   altura_area, 
                   extra_card, 
                   modo="automatico",
                   linhas_fixas=None, 
                   colunas_fixas=None
                   ):
    """
    Devolve (colunas, linhas, largura_do_card). Medidas em pixels "lógicos"
    (já divididos pela escala de DPI).

    modo "automatico": escolhe linhas COMPLETAS que cabem na altura visível, com o
                       card o mais próximo possível de LARGURA_ALVO_CARD.

    modo "manual":     usa as linhas/colunas escolhidas pelo usuário. O card é
                       dimensionado para caber; se mesmo no tamanho mínimo as linhas
                       não couberem na altura, a página ganha rolagem. Se a janela for
                       estreita demais, o número de colunas é reduzido.
    """
    disp_w = largura_area - RESERVA_LARGURA
    disp_h = altura_area - RESERVA_ALTURA
    pad2 = 2 * PAD_GRADE

    if modo == "manual" and linhas_fixas and colunas_fixas:
        colunas_max = max(1, int(disp_w // (LARGURA_MIN_CARD + pad2)))
        colunas = max(1, min(int(colunas_fixas), colunas_max))
        linhas = max(1, int(linhas_fixas))
        w_h = (disp_h / linhas - extra_card - pad2) / PROPORCAO_CAPA + MARGEM_HORIZONTAL
        w_l = disp_w / colunas - pad2
        w = max(LARGURA_MIN_CARD, min(LARGURA_MAX_MANUAL, w_h, w_l))
        return colunas, linhas, int(w) // 8 * 8

    melhor = None

    for linhas in range(1, 9):
        # maior largura de card cuja altura permite `linhas` linhas inteiras
        w_h = (disp_h / linhas - extra_card - pad2) / PROPORCAO_CAPA + MARGEM_HORIZONTAL
        if w_h < LARGURA_MIN_CARD and linhas > 1:
            continue  # não cabe com esse número de linhas

        w_ref = max(LARGURA_MIN_CARD, min(LARGURA_MAX_CARD, w_h))
        colunas = max(1, int(disp_w // (w_ref + pad2)))

        # se cabe mais uma coluna encolhendo no máximo 10%, aproveita o espaço
        w_mais = disp_w / (colunas + 1) - pad2
        if w_mais >= LARGURA_MIN_CARD and w_mais >= 0.9 * w_ref:
            colunas += 1

        w_l = disp_w / colunas - pad2
        w = max(LARGURA_MIN_CARD, min(LARGURA_MAX_CARD, w_h, w_l))
        w = int(w) // 8 * 8   # passos de 8px: limita o cache interno do CTkImage

        # nota = distância do tamanho ideal + fração da altura que ficaria sem uso
        altura_card = (w - MARGEM_HORIZONTAL) * PROPORCAO_CAPA + extra_card + pad2
        usado = min(1.0, linhas * altura_card / max(disp_h, 1))
        nota = abs(w - LARGURA_ALVO_CARD) / LARGURA_ALVO_CARD + (1.0 - usado)

        candidato = (nota, -(colunas * linhas), colunas, linhas, w)
        if melhor is None or candidato < melhor:
            melhor = candidato

    _, _, colunas, linhas, w = melhor
    return colunas, linhas, w