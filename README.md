# contratai — site

Landing page e política de privacidade do **contrataí**, plataforma de entrevistas
de candidatos por áudio no WhatsApp conduzidas por um agente de IA.

🔗 [contratai.net](https://contratai.net)

## O que tem aqui

| Arquivo | |
|---|---|
| `index.html` | Landing page |
| `privacidade.html` | Política de privacidade (LGPD) |
| `hero.mp4` · `poster.jpg` | Vídeo da hero e seu quadro de pôster |
| `recrutadora.jpg` | Foto da seção do painel |
| `logo-claro.png` · `logo-escuro.png` | Logo, uma versão por tema |
| `mic.png` | Favicon |
| `og.jpg` | Imagem de compartilhamento (1200×630) |

Site estático, sem build. HTML, CSS e JavaScript escritos à mão, sem dependências
além das fontes do Google Fonts.

## Rodar localmente

```bash
python3 -m http.server 8000
```

E abrir <http://localhost:8000>.

## Deploy

Publicado na Vercel a partir da branch `main`. O `vercel.json` cuida das URLs
limpas (`/privacidade` em vez de `/privacidade.html`) e do cache das mídias.

O painel da aplicação vive separado, em `app.contratai.net`.

## Detalhes que não são acidentais

- **Tema claro é o padrão**, independente do sistema do visitante. O switch no
  cabeçalho alterna, e a escolha fica no `localStorage`. O script que lê a
  preferência roda antes da primeira pintura, para o tema errado não piscar.
- **O player da hero** toca um áudio real e acende a transcrição palavra por
  palavra, em sincronia. O texto fica inteiro e legível mesmo com o áudio parado.
- **O âmbar é exclusivo da voz** — onda de áudio e etiqueta de transcrição. Em dois
  tons, porque o que funciona sobre a bolha verde não tem contraste sobre branco.
- **A paleta sai do logo**, com os verdes extraídos dos pixels do arquivo original.
