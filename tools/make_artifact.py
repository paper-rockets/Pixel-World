"""Turns the built game (dist/) into a page that can be published as a claude.ai Artifact.

Run after `npm run build`:  python tools/make_artifact.py [page]
  page "index" (Lost Ducklings, default) -> artifact/index.html
  page "school" (Orange Garden)          -> artifact/school/index.html
The game files it needs stay in dist/.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = sys.argv[1] if len(sys.argv) > 1 else "index"
dist = (ROOT / "dist" / f"{PAGE}.html").read_text(encoding="utf-8")

title = re.search(r"<title>.*?</title>", dist, re.S).group(0)
fonts = "\n".join(re.findall(r'<link rel="(?:preconnect|stylesheet)" href="https://fonts[^>]*>', dist))
css_href = re.search(r'<link rel="stylesheet"[^>]*href="\./(assets/[^"]+\.css)"', dist).group(1)
css = (ROOT / "dist" / css_href).read_text(encoding="utf-8")
script = re.search(r'<script type="module"[^>]*></script>', dist).group(0)
body = re.search(r"<body[^>]*>(.*)</body>", dist, re.S).group(1)
body = re.sub(r'\s*<script type="module"[^>]*></script>', "", body)

page = f"""{title}
{fonts}
<style>
{css}
</style>
{body.strip()}
{script}
"""
out = ROOT / "artifact" if PAGE == "index" else ROOT / "artifact" / PAGE
out.mkdir(parents=True, exist_ok=True)
(out / "index.html").write_text(page, encoding="utf-8")
print("wrote", out / "index.html", len(page), "bytes")
need = set(re.findall(r'(?:src|href)="\./([^"]+)"', dist))
js = [n for n in need if n.endswith(".js")]
for n in list(js):
    need |= {"assets/" + m for m in re.findall(r'from"\./([\w.-]+\.js)"|import\("\./([\w.-]+\.js)"', (ROOT / "dist" / n).read_text(encoding="utf-8")) for m in m if m}
    need |= {"assets/" + m for m in re.findall(r'"\./([\w.-]+\.js)"', (ROOT / "dist" / n).read_text(encoding="utf-8"))}
# both pages hold both islands (the boat sails between them), so both need every picture and sound
extra = [p.relative_to(ROOT / "dist").as_posix() for folder in ("assets", "school", "boat")
         for p in (ROOT / "dist" / folder).rglob("*") if p.is_file() and not p.name.endswith((".css", ".js"))]
files = sorted({n for n in need if not n.endswith(".css") and (ROOT / "dist" / n).is_file()} | set(extra))
(out / "files.json").write_text(json.dumps({f: f for f in files}, indent=1))
print(len(files), "files ->", out / "files.json")
