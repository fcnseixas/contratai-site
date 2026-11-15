#!/usr/bin/env python3
"""
Gerador do blog do contrataí.

    python3 gerar-blog.py

Lê `conteudo/*.md` e escreve `blog/index.html`, um `blog/<slug>.html` por texto
e o `sitemap.xml`.

Duas decisões que explicam o resto do arquivo:

1. **Os textos não têm data.** São guias perenes, não notícia. Sem data na tela
   e sem `datePublished` no schema, a biblioteca nunca parece abandonada e nada
   é falso — datar no passado para simular cadência seria prova social
   inventada, que é a regra que mantém número de cliente fictício fora da
   landing. Também é o que a política de dados estruturados do Google cobra:
   data declarada tem que ser data real.

2. **Markdown próprio, sem biblioteca.** Para o site não ganhar a primeira
   dependência de instalação. O subconjunto está documentado em `converter()`.

O nome do arquivo é a URL:  conteudo/slug-do-texto.md → /blog/slug-do-texto
A ordem dentro da categoria sai do campo `ordem` do front matter.
"""

import html
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
ORIGEM = os.path.join(RAIZ, "conteudo")
SAIDA = os.path.join(RAIZ, "blog")
SITE = "https://contratai.net"

# A ordem aqui é a ordem na página. Categoria fora desta lista para a geração,
# em vez de aparecer solta no fim — nome errado no front matter é erro de
# digitação, não uma categoria nova.
CATEGORIAS = [
    ("Triagem e seleção",
     "O trabalho de reduzir muita gente a poucas pessoas, sem perder as certas."),
    ("IA no recrutamento",
     "O que a automação resolve de verdade, o que ela só parece resolver, e onde ela não deveria entrar."),
    ("LGPD e dados de candidato",
     "O que a lei cobra de quem guarda currículo, áudio e avaliação de gente."),
]

FIXAS = [("/", "1.0"), ("/blog", "0.8"), ("/privacidade", "0.3"), ("/termos", "0.3")]


# ---------------------------------------------------------------- leitura

def ler(caminho):
    """Front matter simples (`chave: valor`) separado do corpo por `---`."""
    with open(caminho, encoding="utf-8") as f:
        bruto = f.read().replace("\r\n", "\n")

    meta, corpo = {}, bruto
    if bruto.startswith("---\n"):
        fim = bruto.find("\n---\n", 4)
        if fim == -1:
            raise ValueError("%s: front matter sem fechamento" % caminho)
        for linha in bruto[4:fim].split("\n"):
            if not linha.strip():
                continue
            if ":" not in linha:
                raise ValueError("%s: linha de front matter sem ':' → %r" % (caminho, linha))
            k, v = linha.split(":", 1)
            v = v.strip()
            # Título com dois-pontos precisa vir entre aspas para o `split`
            # acima não cortar no lugar errado; as aspas são da sintaxe, não
            # do texto, e não podem chegar à tela.
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            meta[k.strip()] = v
        corpo = bruto[fim + 5:]

    slug = os.path.basename(caminho)[:-3]
    if not re.match(r"^[a-z0-9-]+$", slug):
        raise ValueError("%s: o nome do arquivo vira URL — só minúsculas, números e hífen"
                         % caminho)

    for obrigatorio in ("titulo", "resumo", "categoria"):
        if not meta.get(obrigatorio):
            raise ValueError("%s: falta `%s` no front matter" % (caminho, obrigatorio))

    validas = [c for c, _ in CATEGORIAS]
    if meta["categoria"] not in validas:
        raise ValueError("%s: categoria %r não existe. As que existem: %s"
                         % (caminho, meta["categoria"], ", ".join(validas)))

    return {
        "slug": slug,
        "titulo": meta["titulo"],
        "resumo": meta["resumo"],
        "categoria": meta["categoria"],
        "ordem": int(meta.get("ordem", 99)),
        "corpo": corpo.strip(),
    }


# ---------------------------------------------------------------- markdown

def esc(txt):
    return html.escape(txt, quote=False)


def inline(txt):
    """Formatação dentro de uma linha. O texto já chega escapado."""
    txt = re.sub(r"`([^`]+)`", r"<code>\1</code>", txt)
    txt = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', txt)
    txt = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", txt)
    txt = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", txt)
    return txt


def converter(md):
    """
    Subconjunto de Markdown, de propósito:

      ## título        ### subtítulo
      parágrafo        **negrito**  *itálico*  `código`  [texto](url)
      - lista          1. lista numerada
      > citação        ---  (linha)
      | tabela | com | cabeçalho |

    Tudo o que não for um desses vira parágrafo.
    """
    linhas = md.split("\n")
    saida, i = [], 0

    while i < len(linhas):
        bruta = linhas[i].rstrip()

        if not bruta.strip():
            i += 1
            continue

        if re.match(r"^-{3,}$", bruta.strip()):
            saida.append("<hr>")
            i += 1
            continue

        m = re.match(r"^(#{2,4})\s+(.*)$", bruta)
        if m:
            n = len(m.group(1))
            saida.append("<h%d>%s</h%d>" % (n, inline(esc(m.group(2).strip())), n))
            i += 1
            continue

        if bruta.lstrip().startswith("|") and i + 1 < len(linhas) \
           and re.match(r"^\s*\|[\s:|-]+\|\s*$", linhas[i + 1]):
            def celulas(l):
                return [c.strip() for c in l.strip().strip("|").split("|")]
            cab = celulas(bruta)
            i += 2
            corpo = []
            while i < len(linhas) and linhas[i].lstrip().startswith("|"):
                corpo.append(celulas(linhas[i]))
                i += 1
            th = "".join("<th>%s</th>" % inline(esc(c)) for c in cab)
            trs = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % inline(esc(c)) for c in l)
                          for l in corpo)
            saida.append("<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>"
                         % (th, trs))
            continue

        if bruta.lstrip().startswith(">"):
            partes = []
            while i < len(linhas) and linhas[i].lstrip().startswith(">"):
                partes.append(linhas[i].lstrip()[1:].strip())
                i += 1
            saida.append("<blockquote><p>%s</p></blockquote>" % inline(esc(" ".join(partes))))
            continue

        ordenada = re.match(r"^\s*\d+\.\s+", bruta)
        if ordenada or re.match(r"^\s*[-*]\s+", bruta):
            padrao = r"^\s*\d+\.\s+" if ordenada else r"^\s*[-*]\s+"
            itens = []
            while i < len(linhas) and re.match(padrao, linhas[i].rstrip()):
                itens.append(re.sub(padrao, "", linhas[i].rstrip()))
                i += 1
                while i < len(linhas) and linhas[i].startswith("  ") and linhas[i].strip() \
                      and not re.match(r"^\s*(\d+\.|[-*])\s+", linhas[i]):
                    itens[-1] += " " + linhas[i].strip()
                    i += 1
            tag = "ol" if ordenada else "ul"
            saida.append("<%s>%s</%s>"
                         % (tag, "".join("<li>%s</li>" % inline(esc(x)) for x in itens), tag))
            continue

        # Parágrafo: junta até a linha em branco. A lista numerada só interrompe
        # parágrafo se começar em `1.` — é a regra do CommonMark, e aqui ela não
        # é purismo: sem isso, uma linha que quebra em "art. 20" e continua com
        # "20. Se a resposta..." vira item de lista e parte o parágrafo em três.
        partes = []
        while i < len(linhas) and linhas[i].strip() \
              and not re.match(r"^\s*(#{2,4}\s|>|[-*]\s|1\.\s|\||-{3,}$)", linhas[i].rstrip()):
            partes.append(linhas[i].strip())
            i += 1
        if partes:
            saida.append("<p>%s</p>" % inline(esc(" ".join(partes))))

    return "\n      ".join(saida)


# ---------------------------------------------------------------- modelo

# Mesmos tokens do index.html e da privacidade. Repetidos aqui porque o projeto
# é de páginas autocontidas — uma folha externa custaria uma requisição a mais
# em toda visita para economizar repetição que o gerador já centraliza.
ESTILO = """
  html{color-scheme:light}
  html[data-mode="dark"]{color-scheme:dark}
  *{box-sizing:border-box}
  img{max-width:100%}

  :root{
    --paper:#FFFFFF; --surface:#FFFFFF; --ink:#0E3629; --muted:#5B7A6B;
    --line:#E4EBE6; --brand:#089D5C; --brand-bright:#07894F; --brand-soft:#E9F7F0;
    --faixa:#F4FAF7; --faixa-line:#E7F1EB; --radius:14px;
  }
  :root[data-mode="dark"]{
    --paper:#06120E; --surface:#0C1F17; --ink:#E6F0EA; --muted:#8FA89A;
    --line:#193026; --brand:#12B86C; --brand-bright:#3FD592; --brand-soft:#0E2F22;
    --faixa:#0A1B14; --faixa-line:#15291F;
  }

  body{
    margin:0;background:var(--paper);color:var(--ink);
    font-family:"Instrument Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
    font-size:16px;line-height:1.6;-webkit-font-smoothing:antialiased;
  }
  .wrap{max-width:720px;margin-inline:auto;padding-inline:20px}

  .nav{display:flex;align-items:center;justify-content:space-between;gap:16px;padding-block:18px}
  .mark img{height:34px;width:auto;display:block}
  .mark .escuro{display:none}
  :root[data-mode="dark"] .mark .claro{display:none}
  :root[data-mode="dark"] .mark .escuro{display:block}
  .navdir{display:flex;align-items:center;gap:18px;font-size:14.5px}
  .navdir a{color:var(--muted);text-decoration:none}
  .navdir a:hover{color:var(--ink)}

  .kicker{
    font-family:"IBM Plex Mono",monospace;font-size:11.5px;letter-spacing:.14em;
    text-transform:uppercase;color:var(--brand);margin:0 0 13px;
  }
  h1{font-family:"Archivo",sans-serif;font-size:clamp(29px,4.4vw,41px);font-weight:800;
     letter-spacing:-.035em;line-height:1.13;margin:0}
  .resumo{margin-top:16px;font-size:18.5px;color:var(--muted);line-height:1.5}
  .topo{padding-block:42px 30px;border-bottom:1px solid var(--line)}

  article{padding-bottom:40px}
  article h2{font-family:"Archivo",sans-serif;font-size:24px;font-weight:700;
             letter-spacing:-.025em;line-height:1.2;margin:40px 0 0}
  article h3{font-size:18.5px;font-weight:700;letter-spacing:-.015em;margin:30px 0 0}
  article p{margin:17px 0 0}
  article ul,article ol{margin:17px 0 0;padding-left:21px;display:grid;gap:9px}
  article li{padding-left:3px}
  article a{color:var(--brand-bright);text-underline-offset:3px}
  article code{font-family:"IBM Plex Mono",monospace;font-size:.9em;
               background:var(--faixa);border:1px solid var(--faixa-line);
               border-radius:5px;padding:1px 5px}
  article hr{margin:38px 0 0;border:0;border-top:1px solid var(--line)}
  article blockquote{margin:24px 0 0;padding:4px 0 4px 20px;border-left:3px solid var(--brand);
                     color:var(--ink);font-size:17.5px}
  article blockquote p{margin:0}
  article table{width:100%;margin-top:22px;border-collapse:collapse;font-size:15px}
  article th,article td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);
                        vertical-align:top}
  article th{font-weight:600;font-size:12.5px;text-transform:uppercase;
             letter-spacing:.07em;color:var(--muted)}

  .grupo{margin-top:46px}
  .grupo > h2{font-family:"Archivo",sans-serif;font-size:21px;font-weight:700;
              letter-spacing:-.02em;margin:0}
  .grupo > p{margin:7px 0 0;color:var(--muted);font-size:15.5px;max-width:52ch}
  .lista{list-style:none;margin:20px 0 0;padding:0;border-top:1px solid var(--line)}
  .lista li{border-bottom:1px solid var(--line)}
  .lista a{display:block;padding:19px 2px;text-decoration:none;color:inherit}
  .lista a:hover strong{color:var(--brand-bright)}
  .lista strong{display:block;font-size:17px;font-weight:600;letter-spacing:-.015em;
                line-height:1.3}
  .lista span{display:block;margin-top:6px;color:var(--muted);font-size:15px}

  .vizinhos{margin-top:40px;padding-top:26px;border-top:1px solid var(--line)}
  .vizinhos .kicker{margin-bottom:14px}
  .vizinhos ul{list-style:none;margin:0;padding:0;display:grid;gap:11px}
  .vizinhos a{color:var(--ink);text-decoration:none;font-weight:500}
  .vizinhos a:hover{color:var(--brand-bright);text-decoration:underline;text-underline-offset:3px}

  .chamada{
    margin-top:42px;background:var(--brand-soft);border:1px solid var(--faixa-line);
    border-radius:var(--radius);padding:28px 26px;
  }
  .chamada strong{display:block;font-family:"Archivo",sans-serif;font-size:19px;
                  font-weight:700;letter-spacing:-.02em}
  .chamada p{margin:9px 0 0;color:var(--muted);font-size:15.5px}
  .chamada a{display:inline-block;margin-top:16px;background:var(--brand);color:#fff;
             text-decoration:none;font-weight:600;font-size:15px;
             padding:11px 18px;border-radius:10px}

  footer{display:flex;justify-content:space-between;align-items:center;gap:16px;
         flex-wrap:wrap;margin-top:48px;padding-block:28px 40px;
         border-top:1px solid var(--line);font-size:13.5px;color:var(--muted)}
  footer nav{display:flex;gap:18px;flex-wrap:wrap}
  footer a{color:var(--muted);text-decoration:none}
  footer a:hover{color:var(--ink);text-decoration:underline;text-underline-offset:3px}

  @media (max-width:560px){
    .topo{padding-block:30px 24px}
    article h2{margin-top:32px}
    .grupo{margin-top:38px}
  }
"""

MOLDE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{{TITULO_ABA}}</title>
<meta name="description" content="{{RESUMO}}">
<link rel="canonical" href="{{URL}}">
<link rel="icon" type="image/png" href="/mic.png">
<meta property="og:type" content="{{OG_TIPO}}">
<meta property="og:site_name" content="contratai">
<meta property="og:locale" content="pt_BR">
<meta property="og:title" content="{{TITULO_ABA}}">
<meta property="og:description" content="{{RESUMO}}">
<meta property="og:url" content="{{URL}}">
<meta property="og:image" content="https://contratai.net/og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
</head>
<body>
<script>
  (function(){ try{ if(localStorage.getItem("contratai-tema")==="dark")
    document.documentElement.setAttribute("data-mode","dark"); }catch(e){} })();
</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800&family=IBM+Plex+Mono:wght@400;500&family=Instrument+Sans:wght@400;500;600&display=swap">

<style>{{ESTILO}}</style>

<div class="wrap">

  <nav class="nav">
    <a class="mark" href="/" aria-label="contratai, página inicial">
      <img class="claro"  src="/logo-claro.png"  alt="contratai" width="640" height="218">
      <img class="escuro" src="/logo-escuro.png" alt="contratai" width="640" height="218">
    </a>
    <div class="navdir">
      <a href="/blog">Guias</a>
      <a href="/">O produto</a>
      <a href="https://app.contratai.net">Entrar</a>
    </div>
  </nav>

{{CORPO}}

  <footer>
    <span>contratai.net</span>
    <nav>
      <a href="/">O produto</a>
      <a href="/blog">Guias</a>
      <a href="/privacidade">Privacidade</a>
      <a href="/termos">Termos</a>
    </nav>
  </footer>

</div>
{{SCHEMA}}
</body>
</html>
"""

CHAMADA = """
      <div class="chamada">
        <strong>O agente entrevista; você só lê.</strong>
        <p>Entrevistas por áudio no WhatsApp do candidato, com transcrição e relatório
        prontos quando você abrir o painel. As 10 primeiras são por nossa conta.</p>
        <a href="https://app.contratai.net/criar-conta">Criar conta grátis</a>
      </div>"""


def montar(titulo_aba, resumo, url, corpo, og_tipo="article", schema=""):
    pagina = MOLDE
    for chave, valor in (("{{ESTILO}}", ESTILO), ("{{TITULO_ABA}}", titulo_aba),
                         ("{{RESUMO}}", html.escape(resumo, quote=True)),
                         ("{{URL}}", url), ("{{OG_TIPO}}", og_tipo),
                         ("{{CORPO}}", corpo), ("{{SCHEMA}}", schema)):
        pagina = pagina.replace(chave, valor)
    return pagina


def pagina_post(post, irmaos):
    url = "%s/blog/%s" % (SITE, post["slug"])

    vizinhos = ""
    if irmaos:
        itens = "".join('<li><a href="/blog/%s">%s</a></li>'
                        % (o["slug"], html.escape(o["titulo"], quote=False))
                        for o in irmaos)
        vizinhos = ('\n    <div class="vizinhos">\n'
                    '      <p class="kicker">Mais sobre %s</p>\n'
                    '      <ul>%s</ul>\n    </div>'
                    % (html.escape(post["categoria"], quote=False), itens))

    corpo = """  <header class="topo">
    <p class="kicker">%s</p>
    <h1>%s</h1>
    <p class="resumo">%s</p>
  </header>

  <article>
      %s
%s%s
  </article>""" % (html.escape(post["categoria"], quote=False),
                   html.escape(post["titulo"], quote=False),
                   html.escape(post["resumo"], quote=False),
                   converter(post["corpo"]), CHAMADA, vizinhos)

    # `Article` e não `BlogPosting`: guia perene, sem data de publicação. Schema
    # sem `datePublished` é válido; com uma data inventada, não seria.
    schema = '<script type="application/ld+json">\n%s\n</script>' % json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": post["titulo"],
        "description": post["resumo"],
        "articleSection": post["categoria"],
        "inLanguage": "pt-BR",
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "publisher": {"@type": "Organization", "name": "contratai", "url": SITE + "/"},
    }, ensure_ascii=False, indent=1)

    return montar("%s · contratai" % post["titulo"], post["resumo"], url, corpo,
                  schema=schema)


def pagina_indice(posts):
    grupos = []
    for nome, descricao in CATEGORIAS:
        daqui = [p for p in posts if p["categoria"] == nome]
        if not daqui:
            continue
        itens = "".join("""
      <li><a href="/blog/%s">
        <strong>%s</strong>
        <span>%s</span>
      </a></li>""" % (p["slug"], html.escape(p["titulo"], quote=False),
                      html.escape(p["resumo"], quote=False)) for p in daqui)
        grupos.append("""  <section class="grupo">
    <h2>%s</h2>
    <p>%s</p>
    <ul class="lista">%s
    </ul>
  </section>""" % (html.escape(nome, quote=False), html.escape(descricao, quote=False), itens))

    corpo = """  <header class="topo">
    <p class="kicker">Guias</p>
    <h1>Contratar dá trabalho.<br>Aqui a gente escreve sobre isso.</h1>
    <p class="resumo">Triagem, entrevista, LGPD e o que a tecnologia resolve —
    e o que ela não resolve — em processo seletivo.</p>
  </header>

%s

%s""" % ("\n\n".join(grupos), CHAMADA)

    return montar("Guias · contratai",
                  "Triagem, entrevista, LGPD e tecnologia em processo seletivo — "
                  "escrito por quem constrói o contrataí.",
                  SITE + "/blog", corpo, og_tipo="website")


def gravar_sitemap(posts):
    linhas = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for caminho, prio in FIXAS:
        linhas.append("  <url><loc>%s%s</loc><priority>%s</priority></url>" % (SITE, caminho, prio))
    for p in posts:
        linhas.append("  <url><loc>%s/blog/%s</loc><priority>0.6</priority></url>"
                      % (SITE, p["slug"]))
    linhas.append("</urlset>")
    with open(os.path.join(RAIZ, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")


def main():
    if not os.path.isdir(ORIGEM):
        print("sem pasta `conteudo/` — nada a fazer", file=sys.stderr)
        return 1

    posts = [ler(os.path.join(ORIGEM, x))
             for x in sorted(x for x in os.listdir(ORIGEM) if x.endswith(".md"))]
    ordem_cat = {nome: i for i, (nome, _) in enumerate(CATEGORIAS)}
    posts.sort(key=lambda p: (ordem_cat[p["categoria"]], p["ordem"], p["titulo"]))

    os.makedirs(SAIDA, exist_ok=True)
    gerados = {"index.html"}
    for p in posts:
        # Os outros da mesma categoria viram links no pé do texto: é o que
        # distribui autoridade entre as páginas em vez de deixar cada uma sozinha.
        irmaos = [o for o in posts if o["categoria"] == p["categoria"] and o is not p][:4]
        nome = p["slug"] + ".html"
        with open(os.path.join(SAIDA, nome), "w", encoding="utf-8") as f:
            f.write(pagina_post(p, irmaos))
        gerados.add(nome)

    with open(os.path.join(SAIDA, "index.html"), "w", encoding="utf-8") as f:
        f.write(pagina_indice(posts))

    # Texto renomeado ou apagado não pode ficar de pé no deploy anterior.
    for antigo in os.listdir(SAIDA):
        if antigo.endswith(".html") and antigo not in gerados:
            os.remove(os.path.join(SAIDA, antigo))
            print("  removido: blog/%s" % antigo)

    gravar_sitemap(posts)
    for nome, _ in CATEGORIAS:
        print("  %-28s %d" % (nome, sum(1 for p in posts if p["categoria"] == nome)))
    print("%d textos em blog/, sitemap.xml regravado." % len(posts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
