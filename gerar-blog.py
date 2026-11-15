#!/usr/bin/env python3
"""
Gerador do blog do contrataí.

    python3 gerar-blog.py

Lê os arquivos de `conteudo/*.md` e escreve `blog/index.html` (o índice) e
`blog/<slug>.html` (um por post), além de regravar o `sitemap.xml`.

O índice é `blog/index.html` e não `blog.html` de propósito: com `cleanUrls`
ligado os dois serviriam em `/blog`, e eu não quero depender de qual deles a
Vercel escolhe para desempatar.

Por que um gerador e não um framework: o site é estático e escrito à mão, e
continua assim — a saída daqui é HTML puro, sem runtime, sem hidratação, sem
nada para baixar além das fontes. E por que um Markdown próprio em vez de uma
biblioteca: para o site não ganhar a primeira dependência de instalação. O
subconjunto suportado está documentado em `converter()` e é o bastante para
post de texto. Se um dia precisar de mais, trocar por `markdown` é meia hora.

Nome do arquivo manda na URL e na data:  2026-11-15-slug-do-post.md
"""

import html
import os
import re
import sys
from datetime import date

RAIZ = os.path.dirname(os.path.abspath(__file__))
ORIGEM = os.path.join(RAIZ, "conteudo")
SAIDA = os.path.join(RAIZ, "blog")
SITE = "https://contratai.net"

MESES = ("janeiro fevereiro março abril maio junho julho agosto setembro "
         "outubro novembro dezembro").split()

# Páginas fixas que entram no sitemap junto com os posts.
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
            meta[k.strip()] = v.strip()
        corpo = bruto[fim + 5:]

    nome = os.path.basename(caminho)[:-3]
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})-(.+)$", nome)
    if not m:
        raise ValueError("%s: o nome precisa ser AAAA-MM-DD-slug.md" % caminho)
    ano, mes, dia, slug = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4)

    for obrigatorio in ("titulo", "resumo"):
        if not meta.get(obrigatorio):
            raise ValueError("%s: falta `%s` no front matter" % (caminho, obrigatorio))

    return {
        "slug": slug,
        "data": date(ano, mes, dia),
        "titulo": meta["titulo"],
        "resumo": meta["resumo"],
        "categoria": meta.get("categoria", ""),
        "corpo": corpo.strip(),
    }


def por_extenso(d):
    return "%d de %s de %d" % (d.day, MESES[d.month - 1], d.year)


# ---------------------------------------------------------------- markdown

def inline(txt):
    """Formatação dentro de uma linha. O texto já chega escapado."""
    txt = re.sub(r"`([^`]+)`", r"<code>\1</code>", txt)
    txt = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', txt)
    txt = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", txt)
    txt = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", txt)
    return txt


def esc(txt):
    return html.escape(txt, quote=False)


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
        linha = linhas[i]
        bruta = linha.rstrip()

        if not bruta.strip():
            i += 1
            continue

        # linha divisória
        if re.match(r"^-{3,}$", bruta.strip()):
            saida.append("<hr>")
            i += 1
            continue

        # títulos
        m = re.match(r"^(#{2,4})\s+(.*)$", bruta)
        if m:
            n = len(m.group(1))
            saida.append("<h%d>%s</h%d>" % (n, inline(esc(m.group(2).strip())), n))
            i += 1
            continue

        # tabela — precisa de cabeçalho e da linha de traços
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
            trs = "".join(
                "<tr>%s</tr>" % "".join("<td>%s</td>" % inline(esc(c)) for c in linha_c)
                for linha_c in corpo)
            saida.append("<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" % (th, trs))
            continue

        # citação
        if bruta.lstrip().startswith(">"):
            partes = []
            while i < len(linhas) and linhas[i].lstrip().startswith(">"):
                partes.append(linhas[i].lstrip()[1:].strip())
                i += 1
            saida.append("<blockquote><p>%s</p></blockquote>" % inline(esc(" ".join(partes))))
            continue

        # listas
        ordenada = re.match(r"^\s*\d+\.\s+", bruta)
        if ordenada or re.match(r"^\s*[-*]\s+", bruta):
            padrao = r"^\s*\d+\.\s+" if ordenada else r"^\s*[-*]\s+"
            itens = []
            while i < len(linhas) and re.match(padrao, linhas[i].rstrip()):
                itens.append(re.sub(padrao, "", linhas[i].rstrip()))
                i += 1
                # continuação indentada vira parte do mesmo item
                while i < len(linhas) and linhas[i].startswith("  ") and linhas[i].strip() \
                      and not re.match(r"^\s*(\d+\.|[-*])\s+", linhas[i]):
                    itens[-1] += " " + linhas[i].strip()
                    i += 1
            tag = "ol" if ordenada else "ul"
            lis = "".join("<li>%s</li>" % inline(esc(x)) for x in itens)
            saida.append("<%s>%s</%s>" % (tag, lis, tag))
            continue

        # parágrafo: junta até a linha em branco
        partes = []
        while i < len(linhas) and linhas[i].strip() \
              and not re.match(r"^\s*(#{2,4}\s|>|[-*]\s|\d+\.\s|\||-{3,}$)", linhas[i].rstrip()):
            partes.append(linhas[i].strip())
            i += 1
        if partes:
            saida.append("<p>%s</p>" % inline(esc(" ".join(partes))))

    return "\n      ".join(saida)


# ---------------------------------------------------------------- modelo

# Mesmos tokens do index.html e da privacidade. Ficam repetidos aqui porque o
# projeto é de páginas autocontidas — uma folha externa custaria uma requisição
# extra em toda visita para economizar repetição que o gerador já centraliza.
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
  h1{font-family:"Archivo",sans-serif;font-size:clamp(30px,4.6vw,43px);font-weight:800;
     letter-spacing:-.035em;line-height:1.12;margin:0}
  .resumo{margin-top:16px;font-size:18.5px;color:var(--muted);line-height:1.5}
  .meta{margin-top:20px;padding-top:18px;border-top:1px solid var(--line);
        font-family:"IBM Plex Mono",monospace;font-size:12.5px;color:var(--muted)}

  .topo{padding-block:42px 36px}

  article{padding-bottom:40px}
  article h2{font-family:"Archivo",sans-serif;font-size:25px;font-weight:700;
             letter-spacing:-.025em;line-height:1.2;margin:42px 0 0}
  article h3{font-size:19px;font-weight:700;letter-spacing:-.015em;margin:32px 0 0}
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

  .lista{list-style:none;margin:0;padding:0;border-top:1px solid var(--line)}
  .lista li{border-bottom:1px solid var(--line)}
  .lista a{display:block;padding:24px 2px;text-decoration:none;color:inherit}
  .lista a:hover h2{color:var(--brand-bright)}
  .lista .quando{font-family:"IBM Plex Mono",monospace;font-size:12px;
                 letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
  .lista h2{font-family:"Archivo",sans-serif;font-size:21px;font-weight:700;
            letter-spacing:-.02em;line-height:1.25;margin:9px 0 0}
  .lista p{margin:8px 0 0;color:var(--muted);font-size:15.5px}

  .chamada{
    margin-top:46px;background:var(--brand-soft);border:1px solid var(--faixa-line);
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
    .topo{padding-block:30px 26px}
    article h2{margin-top:34px}
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
      <a href="/blog">Blog</a>
      <a href="/">O produto</a>
      <a href="https://app.contratai.net">Entrar</a>
    </div>
  </nav>

{{CORPO}}

  <footer>
    <span>contratai.net</span>
    <nav>
      <a href="/">O produto</a>
      <a href="/blog">Blog</a>
      <a href="/privacidade">Privacidade</a>
      <a href="/termos">Termos</a>
    </nav>
  </footer>

</div>
{{SCHEMA}}
</body>
</html>
"""


def montar(titulo_aba, resumo, url, corpo, og_tipo="article", schema=""):
    pagina = MOLDE
    for chave, valor in (("{{ESTILO}}", ESTILO), ("{{TITULO_ABA}}", titulo_aba),
                         ("{{RESUMO}}", html.escape(resumo, quote=True)),
                         ("{{URL}}", url), ("{{OG_TIPO}}", og_tipo),
                         ("{{CORPO}}", corpo), ("{{SCHEMA}}", schema)):
        pagina = pagina.replace(chave, valor)
    return pagina


CHAMADA = """
      <div class="chamada">
        <strong>O agente entrevista; você só lê.</strong>
        <p>Entrevistas por áudio no WhatsApp do candidato, com transcrição e relatório
        prontos quando você abrir o painel. As 10 primeiras são por nossa conta.</p>
        <a href="https://app.contratai.net/criar-conta">Criar conta grátis</a>
      </div>"""


def pagina_post(post):
    url = "%s/blog/%s" % (SITE, post["slug"])
    titulo = html.escape(post["titulo"], quote=False)

    corpo = """  <header class="topo">
    %s<h1>%s</h1>
    <p class="resumo">%s</p>
    <p class="meta">%s</p>
  </header>

  <article>
      %s
%s
  </article>""" % (
        '<p class="kicker">%s</p>\n    ' % html.escape(post["categoria"], quote=False)
        if post["categoria"] else "",
        titulo,
        html.escape(post["resumo"], quote=False),
        por_extenso(post["data"]),
        converter(post["corpo"]),
        CHAMADA)

    # BlogPosting: o que faz o post aparecer como artigo datado na busca.
    import json
    schema = '<script type="application/ld+json">\n%s\n</script>' % json.dumps({
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": post["titulo"],
        "description": post["resumo"],
        "datePublished": post["data"].isoformat(),
        "inLanguage": "pt-BR",
        "mainEntityOfPage": {"@type": "WebPage", "@id": url},
        "publisher": {"@type": "Organization", "name": "contratai",
                      "url": SITE + "/"},
    }, ensure_ascii=False, indent=1)

    return montar("%s · contratai" % post["titulo"], post["resumo"], url, corpo,
                  og_tipo="article", schema=schema)


def pagina_indice(posts):
    itens = []
    for p in posts:
        itens.append("""      <li><a href="/blog/%s">
        <span class="quando">%s</span>
        <h2>%s</h2>
        <p>%s</p>
      </a></li>""" % (p["slug"], por_extenso(p["data"]),
                      html.escape(p["titulo"], quote=False),
                      html.escape(p["resumo"], quote=False)))

    corpo = """  <header class="topo">
    <p class="kicker">Blog</p>
    <h1>Contratar dá trabalho.<br>Aqui a gente escreve sobre isso.</h1>
    <p class="resumo">Triagem, entrevista, LGPD e o que a tecnologia resolve —
    e o que ela não resolve — em processo seletivo.</p>
  </header>

  <ul class="lista">
%s
  </ul>
%s""" % ("\n".join(itens) if itens else
         '      <li><p style="padding:26px 2px;color:var(--muted)">Em breve.</p></li>',
         CHAMADA)

    return montar("Blog · contratai",
                  "Triagem, entrevista, LGPD e tecnologia em processo seletivo — "
                  "escrito por quem constrói o contrataí.",
                  SITE + "/blog", corpo, og_tipo="website")


def gravar_sitemap(posts):
    linhas = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for caminho, prio in FIXAS:
        linhas.append("  <url><loc>%s%s</loc><priority>%s</priority></url>" % (SITE, caminho, prio))
    for p in posts:
        linhas.append('  <url><loc>%s/blog/%s</loc><lastmod>%s</lastmod>'
                      '<priority>0.6</priority></url>'
                      % (SITE, p["slug"], p["data"].isoformat()))
    linhas.append("</urlset>")
    with open(os.path.join(RAIZ, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")


def main():
    if not os.path.isdir(ORIGEM):
        print("sem pasta `conteudo/` — nada a fazer", file=sys.stderr)
        return 1

    arquivos = sorted(x for x in os.listdir(ORIGEM) if x.endswith(".md"))
    posts = [ler(os.path.join(ORIGEM, x)) for x in arquivos]
    posts.sort(key=lambda p: p["data"], reverse=True)

    os.makedirs(SAIDA, exist_ok=True)
    for p in posts:
        destino = os.path.join(SAIDA, p["slug"] + ".html")
        with open(destino, "w", encoding="utf-8") as f:
            f.write(pagina_post(p))
        print("  blog/%s.html" % p["slug"])

    with open(os.path.join(SAIDA, "index.html"), "w", encoding="utf-8") as f:
        f.write(pagina_indice(posts))
    print("  blog/index.html")

    gravar_sitemap(posts)
    print("  sitemap.xml")
    print("%d post(s)." % len(posts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
