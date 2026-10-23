#include "raylib.h"
#include "extrator.h" 
#include <stdio.h>    
#include <string.h>
#include <stdlib.h> 
#include <sys/stat.h> 
#include <direct.h>

#define COR_FUNDO       (Color){ 24, 24, 27, 255 }   
#define COR_PAINEL      (Color){ 39, 39, 42, 255 }   
#define COR_DESTAQUE    (Color){ 59, 130, 246, 255 } 
#define COR_TEXTO       (Color){ 228, 228, 231, 255 } 
#define COR_TEXTO_DIM   (Color){ 161, 161, 170, 255 } 
#define COR_ICONE_PASTA (Color){ 250, 204, 21, 255 } 
#define COR_SUCESSO     (Color){ 74, 222, 128, 255 } 
#define COR_AVISO       (Color){ 249, 115, 22, 255 } 
#define COR_SELECAO     (Color){ 14, 165, 233, 255 } 
#define COR_ATALHO      (Color){ 250, 204, 21, 255 } 

#define MAX_FILA 200

typedef enum { ESTADO_NAVEGACAO, ESTADO_CRIAR_PASTA } EstadoApp;

char filaSelecao[MAX_FILA][MAX_CAMINHO];
int totalSelecionados = 0;

char filaMemoria[MAX_FILA][MAX_CAMINHO];
int totalMemoria = 0;

int estaSelecionado(const char *caminho) {
    for (int i = 0; i < totalSelecionados; i++) {
        if (strcmp(filaSelecao[i], caminho) == 0) return i + 1; 
    }
    return 0; 
}

static int caractereValidoNome(int c) {
    return c >= 32 && c <= 125 && strchr("<>:\"/\\|?*", c) == NULL;
}

void DesenharAtalhos(int startX, int startY, const char* texto) {
    int posX = startX;
    char buffer[256];
    int bufIdx = 0;
    int len = strlen(texto);

    for (int i = 0; i <= len; i++) {
        if (texto[i] == '[' || texto[i] == '\0') {
            if (bufIdx > 0) {
                buffer[bufIdx] = '\0';
                DrawText(buffer, posX, startY, 18, COR_TEXTO_DIM);
                posX += MeasureText(buffer, 18);
                bufIdx = 0;
            }
        }
        
        if (texto[i] == '\0') break;
        
        buffer[bufIdx++] = texto[i];
        

        if (texto[i] == ']') {
            buffer[bufIdx] = '\0';
            DrawText(buffer, posX, startY, 18, COR_ATALHO); 
            posX += MeasureText(buffer, 18);
            bufIdx = 0;
        }
    }
}

int main(void) {
    SetConfigFlags(FLAG_WINDOW_RESIZABLE);
    
    char pastaDownloads[MAX_CAMINHO] = "";
    char *userProfile = getenv("USERPROFILE");

    if (userProfile && userProfile[0]) {
        snprintf(pastaDownloads, sizeof(pastaDownloads), "%s/Downloads", userProfile);
        for (int i = 0; pastaDownloads[i] != '\0'; i++)
            if (pastaDownloads[i] == '\\') pastaDownloads[i] = '/';
    } else {
        printf("Nao conseguiu detectar o nome do usuario do sistema\n");
    }

    strcpy(diretorioAtual, PASTA_RAIZ);
    carregarDiretorio(diretorioAtual);

    int larguraTela = 1100, alturaTela = 750;
    InitWindow(larguraTela, alturaTela, "Organizador de Quadrinhos Pro");
    
    char caminhoIcone[512];
    const char *baseDir = GetApplicationDirectory();
    snprintf(caminhoIcone, sizeof(caminhoIcone), "%s..\\assets\\png_descompactador.png", baseDir);
    
    Image icone = LoadImage(caminhoIcone);
    if (icone.data != NULL) {
        SetWindowIcon(icone);
        UnloadImage(icone);
    }
    
    SetExitKey(0);
     
    SetWindowState(FLAG_WINDOW_TOPMOST);

    SetTargetFPS(60);


    int itemSelecionado = 0, 
        rolagem = 0,
        framesSegurandoBaixo = 0,
        framesSegurandoCima = 0,
        framesSegurandoEspaco = 0;
    
    const int alturaItem = 46; 
    
    int workspaceAtual = 0; 

    EstadoApp estado = ESTADO_NAVEGACAO;
    char nomeNovaPasta[256] = "\0";
    int contLetras = 0;

    int contadorFrames = 0;
    
    while (!WindowShouldClose()) {
        if (contadorFrames == 1) {
            ClearWindowState(FLAG_WINDOW_TOPMOST);
        }
        contadorFrames++;

        if (IsKeyPressed(KEY_F11)) ToggleFullscreen();
        larguraTela = GetScreenWidth(); alturaTela = GetScreenHeight();
        int maxItensNaTela = (alturaTela - 170) / alturaItem;
        if (maxItensNaTela < 1) maxItensNaTela = 1;
        if (totalItens == 0) itemSelecionado = 0;
        else if (itemSelecionado >= totalItens) itemSelecionado = totalItens - 1;
        if (rolagem > itemSelecionado) rolagem = itemSelecionado; 

        if (estado == ESTADO_CRIAR_PASTA) {
            int key = GetCharPressed();
            while (key > 0) {
                if (caractereValidoNome(key) && (contLetras < 255)) {
                    nomeNovaPasta[contLetras] = (char)key;
                    nomeNovaPasta[contLetras+1] = '\0';
                    contLetras++;
                }
                key = GetCharPressed();
            }

            if (IsKeyPressed(KEY_BACKSPACE)) {
                contLetras--;
                if (contLetras < 0) contLetras = 0;
                nomeNovaPasta[contLetras] = '\0';
            }

            if (IsKeyPressed(KEY_ENTER) && contLetras > 0) {
                char caminhoNovaPasta[MAX_CAMINHO];
                int n = snprintf(caminhoNovaPasta, sizeof(caminhoNovaPasta), "%s/%s", diretorioAtual, nomeNovaPasta);
                if (n > 0 && (size_t)n < sizeof(caminhoNovaPasta) && _mkdir(caminhoNovaPasta) == 0)
                    snprintf(mensagemStatus, sizeof(mensagemStatus), "Pasta '%s' criada com sucesso!", nomeNovaPasta);
                else
                    snprintf(mensagemStatus, sizeof(mensagemStatus), "Erro ao criar a pasta '%s'.", nomeNovaPasta);

                snprintf(caminhoNovaPasta, sizeof(caminhoNovaPasta), "%s/%s", diretorioAtual, nomeNovaPasta);
                mkdir(caminhoNovaPasta); 

                snprintf(mensagemStatus, sizeof(mensagemStatus), "Pasta '%s' criada com sucesso!", nomeNovaPasta);
                estado = ESTADO_NAVEGACAO;
                nomeNovaPasta[0] = '\0'; contLetras = 0;
                carregarDiretorio(diretorioAtual);
            }
            if (IsKeyPressed(KEY_ESCAPE)) {
                estado = ESTADO_NAVEGACAO;
                nomeNovaPasta[0] = '\0'; contLetras = 0;
            }
        } 
        else {
            if (IsKeyDown(KEY_DOWN)) {
                framesSegurandoBaixo++;
                if (framesSegurandoBaixo == 1 || (framesSegurandoBaixo > 30 && framesSegurandoBaixo % 4 == 0)) {
                    if (itemSelecionado < totalItens - 1) itemSelecionado++;
                }
            } else framesSegurandoBaixo = 0;

            if (IsKeyDown(KEY_UP)) {
                framesSegurandoCima++;
                if (framesSegurandoCima == 1 || (framesSegurandoCima > 30 && framesSegurandoCima % 4 == 0)) {
                    if (itemSelecionado > 0) itemSelecionado--;
                }
            } else framesSegurandoCima = 0;

            if (itemSelecionado >= rolagem + maxItensNaTela) rolagem = itemSelecionado - maxItensNaTela + 1;
            else if (itemSelecionado < rolagem) rolagem = itemSelecionado;

            if (IsKeyPressed(KEY_TAB)) {
                if (workspaceAtual == 0 && pastaDownloads[0] == '\0') {
                    strcpy(mensagemStatus, "Pasta Downloads indisponivel (USERPROFILE nao definido).");
                } else {
                    workspaceAtual = (workspaceAtual == 0) ? 1 : 0;
                    strcpy(diretorioAtual, (workspaceAtual == 0) ? PASTA_RAIZ : pastaDownloads);
                    carregarDiretorio(diretorioAtual);
                    itemSelecionado = 0; rolagem = 0;
                    totalSelecionados = 0;
                    strcpy(mensagemStatus, "Ambiente alterado.");
                }
            }

            if (IsKeyPressed(KEY_N)) estado = ESTADO_CRIAR_PASTA;

            if (IsKeyPressed(KEY_ESCAPE)) {
                if (totalSelecionados > 0) {
                    totalSelecionados = 0;
                    strcpy(mensagemStatus, "Selecao cancelada.");
                } else if (totalMemoria > 0) {
                    totalMemoria = 0;
                    strcpy(mensagemStatus, "Recortar cancelado. A memoria foi limpa.");
                }
            }

            if (IsKeyPressed(KEY_A) && totalItens > 0) {
                for(int i = 0; i < totalItens; i++) {
                    if (listaAtual[i].tipo != ITEM_VOLTAR && !estaSelecionado(listaAtual[i].caminho)) {
                        if (totalSelecionados < MAX_FILA) {
                            strcpy(filaSelecao[totalSelecionados], listaAtual[i].caminho);
                            totalSelecionados++;
                        }
                    }
                }
                strcpy(mensagemStatus, "Todos os itens selecionados.");
            }

            if (IsKeyDown(KEY_SPACE) && totalItens > 0) {
                framesSegurandoEspaco++;
                if (framesSegurandoEspaco == 1 || (framesSegurandoEspaco > 20 && framesSegurandoEspaco % 4 == 0)) {
                    ItemLista item = listaAtual[itemSelecionado];
                    if (item.tipo != ITEM_VOLTAR) { 
                        int pos = estaSelecionado(item.caminho);
                        if (pos > 0) {
                            for (int j = pos - 1; j < totalSelecionados - 1; j++) {
                                strcpy(filaSelecao[j], filaSelecao[j+1]);
                            }
                            totalSelecionados--;
                        } else if (totalSelecionados < MAX_FILA) {
                            strcpy(filaSelecao[totalSelecionados], item.caminho);
                            totalSelecionados++;
                            if (itemSelecionado < totalItens - 1) itemSelecionado++; 
                        }
                    }
                }
            } else {
                framesSegurandoEspaco = 0;
            }

            if (IsKeyPressed(KEY_E) && totalSelecionados > 0) {
                for(int i = 0; i < totalSelecionados; i++) {
                    strcpy(filaMemoria[i], filaSelecao[i]);
                }
                totalMemoria = totalSelecionados;
                totalSelecionados = 0; 
                snprintf(mensagemStatus, sizeof(mensagemStatus), "%d itens guardados na memoria. Navegue e aperte [V] para Colar.", totalMemoria);
            }

            if (IsKeyPressed(KEY_V) && totalMemoria > 0) {
                int movidos = 0;
                for (int i = 0; i < totalMemoria; i++) {
                    char *nomeArquivo = strrchr(filaMemoria[i], '/');
                    if (!nomeArquivo) nomeArquivo = strrchr(filaMemoria[i], '\\');
                    nomeArquivo = nomeArquivo ? nomeArquivo + 1 : filaMemoria[i];

                    char novoCaminho[MAX_CAMINHO];
                    snprintf(novoCaminho, sizeof(novoCaminho), "%s/%s", diretorioAtual, nomeArquivo);

                    if (rename(filaMemoria[i], novoCaminho) == 0) movidos++;
                }
                totalMemoria = 0; 
                carregarDiretorio(diretorioAtual); 
                snprintf(mensagemStatus, sizeof(mensagemStatus), "Sucesso! %d itens colados.", movidos);
            }

            if (IsKeyPressed(KEY_ENTER)) {
                if (totalSelecionados > 0) {
                    BeginDrawing();
                    ClearBackground(COR_FUNDO);
                    DrawText(TextFormat("Processando lote de %d itens...", totalSelecionados), 40, alturaTela / 2, 24, COR_ICONE_PASTA);
                    EndDrawing();
                    
                    for(int i = 0; i < totalSelecionados; i++) {
                        struct stat info;
                        if (stat(filaSelecao[i], &info) == 0 && !S_ISDIR(info.st_mode)) { 
                            processarQuadrinho(filaSelecao[i]);
                        }
                    }
                    totalSelecionados = 0;
                    carregarDiretorio(diretorioAtual);
                    strcpy(mensagemStatus, "Lote extraido com sucesso!");
                    
                } else if (totalItens > 0) {
                    ItemLista item = listaAtual[itemSelecionado];
                    if (item.tipo == ITEM_PASTA || item.tipo == ITEM_VOLTAR) {
                        if (item.tipo == ITEM_VOLTAR) {
                            char *ultimoBarra = strrchr(diretorioAtual, '/');
                            if (!ultimoBarra) ultimoBarra = strrchr(diretorioAtual, '\\');
                            if (ultimoBarra) *ultimoBarra = '\0'; 
                        } else {
                            strcpy(diretorioAtual, item.caminho);
                        }
                        carregarDiretorio(diretorioAtual);
                        itemSelecionado = 0; rolagem = 0;
                        strcpy(mensagemStatus, "Pronto. Navegue e aperte ENTER para extrair.");
                    } 
                    else if (item.tipo == ITEM_ARQUIVO) {
                        BeginDrawing();
                        ClearBackground(COR_FUNDO);
                        DrawText("Extraindo imagens... Por favor, aguarde.", 40, alturaTela / 2, 24, COR_ICONE_PASTA);
                        EndDrawing();
                        processarQuadrinho(item.caminho);
                        WaitTime(1.0); 
                    }
                }
            }

            // ==========================================
            // TECLA 'D': ARQUIVAR CBR EM D:\Emulador\HQ\CBR\... OU EXTRAIR DE LÁ
            // ==========================================
            if (IsKeyPressed(KEY_D)) {
                BeginDrawing();
                ClearBackground(COR_FUNDO);
                DrawText("Arquivando arquivos CBR e organizando pasta... Aguarde.", 40, alturaTela / 2, 24, COR_ICONE_PASTA);
                EndDrawing();

                concluirPasta(diretorioAtual);
                
                // Verifica se a função adicionou "(Descompactada)" ou "(Descompactado)" no caminho
                if (strstr(diretorioAtual, "(Descompactada)") != NULL || strstr(diretorioAtual, "(Descompactado)") != NULL) {
                    // Volta um diretório automaticamente
                    char *ultimoBarra = strrchr(diretorioAtual, '/');
                    if (!ultimoBarra) ultimoBarra = strrchr(diretorioAtual, '\\');
                    if (ultimoBarra) *ultimoBarra = '\0'; 
                }

                carregarDiretorio(diretorioAtual);
                itemSelecionado = 0; rolagem = 0; totalSelecionados = 0;
            }
        }

        // ==========================================
        // RENDERIZAÇÃO
        // ==========================================
        BeginDrawing();
        ClearBackground(COR_FUNDO);

        DrawRectangle(0, 0, larguraTela, 90, COR_PAINEL);
        DrawText("GERENCIADOR DE HQs", 30, 20, 24, COR_TEXTO);
        
        const char* nomeWorkspace = (workspaceAtual == 0) ? "[ WORKSPACE: HQ ]" : "[ WORKSPACE: DOWNLOADS ]";
        DrawText(nomeWorkspace, larguraTela - MeasureText(nomeWorkspace, 20) - 30, 22, 20, COR_AVISO);
        DrawText(TextFormat("Caminho: %s", diretorioAtual), 30, 55, 18, COR_TEXTO_DIM);

        for (int i = rolagem; i < totalItens && i < rolagem + maxItensNaTela; i++) {
            int posY = 105 + ((i - rolagem) * alturaItem);
            
            if (i == itemSelecionado) {
                DrawRectangleRounded((Rectangle){ 15, (float)posY, (float)larguraTela - 30, (float)alturaItem - 6 }, 0.3f, 10, COR_DESTAQUE);
            }

            Color corPrincipal = (i == itemSelecionado) ? WHITE : COR_TEXTO;
            int pos = estaSelecionado(listaAtual[i].caminho); 
            
            if (listaAtual[i].tipo == ITEM_VOLTAR) {
                DrawText("<--", 30, posY + 8, 20, COR_ICONE_PASTA);
                DrawText(listaAtual[i].nome, 70, posY + 8, 20, corPrincipal);
            } 
            else if (listaAtual[i].tipo == ITEM_PASTA) {
                if (pos > 0) {
                    char textoMarca[32];
                    snprintf(textoMarca, sizeof(textoMarca), "[ %d ]", pos);
                    DrawText(textoMarca, 30, posY + 8, 18, COR_SELECAO);
                    DrawText(listaAtual[i].nome, 90, posY + 8, 20, COR_SELECAO);
                } else {
                    DrawText("[DIR]", 30, posY + 8, 18, COR_ICONE_PASTA);
                    DrawText(listaAtual[i].nome, 90, posY + 8, 20, corPrincipal);
                }
            } 
            else {
                if (pos > 0) {
                    char textoMarca[32];
                    snprintf(textoMarca, sizeof(textoMarca), "[ %d ]", pos);
                    DrawText(textoMarca, 30, posY + 8, 18, COR_SELECAO);
                    DrawText(listaAtual[i].nome, 90, posY + 8, 20, COR_SELECAO);
                }
                else if (foiExtraido(listaAtual[i].caminho)) {
                    DrawText("[OK]", 30, posY + 8, 18, COR_SUCESSO);
                    DrawText(listaAtual[i].nome, 90, posY + 8, 20, (i == itemSelecionado) ? WHITE : COR_SUCESSO);
                } else {
                    DrawText("[HQ]", 30, posY + 8, 18, COR_TEXTO_DIM);
                    DrawText(listaAtual[i].nome, 90, posY + 8, 20, corPrincipal);
                }
            }
        }

        if (estado == ESTADO_CRIAR_PASTA) {
            DrawRectangle(0, 0, larguraTela, alturaTela, (Color){0, 0, 0, 180}); 
            DrawRectangleRounded((Rectangle){ larguraTela/2 - 250, alturaTela/2 - 60, 500, 120 }, 0.2f, 10, COR_PAINEL);
            DrawText("NOME DA NOVA PASTA:", larguraTela/2 - 230, alturaTela/2 - 40, 20, COR_TEXTO_DIM);
            DrawText(nomeNovaPasta, larguraTela/2 - 230, alturaTela/2 - 10, 24, COR_DESTAQUE);
            DrawText("ENTER: Confirmar | ESC: Cancelar", larguraTela/2 - 230, alturaTela/2 + 30, 14, COR_TEXTO_DIM);
        }

        DrawRectangle(0, alturaTela - 60, larguraTela, 60, COR_PAINEL);
        DrawText(mensagemStatus, 30, alturaTela - 40, 18, COR_SUCESSO);
        
        char atalhos[256];
        if (totalSelecionados > 0) {
            snprintf(atalhos, sizeof(atalhos), "Fila: %d   [E] Recortar   [ENTER] Extrair Lote   [ESC] Cancelar", totalSelecionados);
            DesenharAtalhos(larguraTela - MeasureText(atalhos, 18) - 30, alturaTela - 40, atalhos);
        } else if (totalMemoria > 0) {
            snprintf(atalhos, sizeof(atalhos), "Memoria: %d itens   [V] Colar Aqui   [ESC] Cancelar", totalMemoria);
            DesenharAtalhos(larguraTela - MeasureText(atalhos, 18) - 30, alturaTela - 40, atalhos);
        } else {
            snprintf(atalhos, sizeof(atalhos), "[A] Tudo   [ESPACO] Sel   [TAB] Local   [N] Nova   [D] Arquivar CBR");
            DesenharAtalhos(larguraTela - MeasureText(atalhos, 18) - 30, alturaTela - 40, atalhos);
        }

        EndDrawing();
    }

    CloseWindow();
    return 0;
}