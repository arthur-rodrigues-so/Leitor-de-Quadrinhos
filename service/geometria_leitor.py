from typing import Tuple

def calcular_dimensao_base(orig_w: int, orig_h: int, canvas_w: int, canvas_h: int) -> Tuple[int, int]:
    """Calcula o tamanho ideal da imagem para caber na tela mantendo a proporção."""
    if orig_w == 0 or orig_h == 0:
        return 1, 1
    max_w = max(100, canvas_w - 20)
    max_h = max(100, canvas_h - 12)
    ratio = min(max_w / orig_w, max_h / orig_h)
    return max(1, int(orig_w * ratio)), max(1, int(orig_h * ratio))

def calcular_ponto_zoom(mx: int, my: int, centro_x: int, centro_y: int, 
                        largura_atual: int, altura_atual: int, 
                        nova_largura: int, nova_altura: int) -> Tuple[int, int]:
    """Calcula as novas coordenadas do centro para que o zoom aconteça onde o mouse está apontando."""
    rx = (mx - (centro_x - largura_atual / 2)) / largura_atual
    ry = (my - (centro_y - altura_atual / 2)) / altura_atual
    novo_centro_x = int(mx - rx * nova_largura + nova_largura / 2)
    novo_centro_y = int(my - ry * nova_altura + nova_altura / 2)
    return novo_centro_x, novo_centro_y