#ifndef EXTRATOR_H
#define EXTRATOR_H

#define MAX_ITENS 2000
#define MAX_CAMINHO 512
#define PASTA_RAIZ "D:/Emulador/HQ"
#define PASTA_CBR  "D:/Emulador/HQ/CBR"

typedef enum { ITEM_VOLTAR, ITEM_PASTA, ITEM_ARQUIVO } TipoItem;

typedef struct {
    char nome[256];
    char caminho[MAX_CAMINHO];
    TipoItem tipo;
} ItemLista;

extern ItemLista listaAtual[MAX_ITENS];
extern int totalItens;
extern char diretorioAtual[MAX_CAMINHO];
extern char mensagemStatus[256];

/* Funções principais de navegação e extração */
void carregarDiretorio(const char *pasta);
void processarQuadrinho(const char *caminhoCBZ);
void concluirPasta(char *caminhoPasta);

/* Histórico e verificação de extração */
int foiExtraido(const char *caminho);
void registrarExtraido(const char *caminho);

/* Funções auxiliares de diretórios e espelhamento CBR */
void normalizarCaminho(char *destino, const char *origem);
void criarDiretoriosRecursivo(const char *caminho);
int estaDentroDeCBR(const char *caminho, char *subcaminhoOut);
int obterSubcaminhoRaiz(const char *caminho, char *subcaminhoOut);

#endif