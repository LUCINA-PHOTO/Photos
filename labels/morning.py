# Утренняя сборка WB: таблица заказов на сборке + PDF этикеток (стикер WB, затем этикетка товара) в том же порядке.
# Вывод: путь к PDF, ссылка на GitHub, HTML и текст письма в файлах scratchpad.
import json,sys,io,base64,time,math,datetime,secrets,subprocess,urllib.request,urllib.error,html
sys.path.insert(0,"/home/claude/labels")
from mklabels import label,W,H,is_dir
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from PIL import Image
SP="/tmp/claude-0/-home-claude/8ff3b9a6-a369-58cb-98f2-fc8b117999e6/scratchpad/"
T=open(SP+"wb_token_mp").read().strip()
TR=open(SP+"wb_token").read().strip()
B="https://marketplace-api.wildberries.ru/api/v3"
def req(u,body=None,tok=T):
    r=urllib.request.Request(u,data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization":tok,"Content-Type":"application/json"},method="POST" if body is not None else "GET")
    for i in range(5):
        try: return json.load(urllib.request.urlopen(r,timeout=90))
        except urllib.error.HTTPError as e:
            if e.code not in (429,500,502,503) or i==4: raise
            time.sleep(6)
        except urllib.error.URLError:
            if i==4: raise
            time.sleep(6)
# свежие карточки (названия)
cards=[];cur={"limit":100}
while True:
    d=req("https://content-api.wildberries.ru/content/v2/get/cards/list",{"settings":{"cursor":cur,"filter":{"withPhoto":-1}}},TR)
    cards+=d["cards"]
    if len(d["cards"])<100: break
    c=d["cursor"];cur={"limit":100,"updatedAt":c["updatedAt"],"nmID":c["nmID"]}
json.dump(cards,open(SP+"cards_lbl.json","w"),ensure_ascii=False)
CARD={c["nmID"]:c for c in cards}
def item(nm):
    c=CARD.get(nm)
    if not c: return None
    return {"barcode":c["sizes"][0]["skus"][0],"title":c["title"],"vc":c["vendorCode"],"nm":nm}
def kind(c):
    t=c["title"].lower(); v=c["vendorCode"].lower()
    if "подвесн" in t or v.startswith("подвесн"): return (1,"Люстра подвесная")
    if "потолочн" in t or v.startswith(("потолоч","потлоч","полочн")): return (2,"Люстра потолочная")
    if c["subjectName"]=="Абажуры" and ("лампы и бра" in t or v.startswith("абажурчик")): return (4,"Абажурчик")
    if c["subjectName"]=="Абажуры": return (3,"Абажур 37 см")
    return (5,c["subjectName"])
def fabric(c):
    t=c["title"]
    if "ткань " in t: return t.split("ткань ",1)[1].strip()
    return t.rsplit(",",1)[1].strip() if "," in t else "—"
# заказы
now=time.time()
d=req(B+f"/orders?limit=1000&next=0&dateFrom={int(now)-30*86400}")
orders=d["orders"]
st={}
for i in range(0,len(orders),1000):
    for s in req(B+"/orders/status",{"orders":[o["id"] for o in orders[i:i+1000]]})["orders"]: st[s["id"]]=s
new_ids={o["id"] for o in req(B+"/orders/new")["orders"]}
SAM=datetime.timezone(datetime.timedelta(hours=4))
today=datetime.datetime.now(SAM).date()
rows=[]
for o in orders:
    s=st.get(o["id"],{})
    ss=s.get("supplierStatus"); ws=s.get("wbStatus")
    import os
    if not (ss=="confirm" or o["id"] in new_ids or (os.environ.get("TEST") and ss=="complete" and o["createdAt"]>"2026-11-06")): continue
    if ws in ("canceled","canceled_by_client","declined_by_client","defect"): continue
    c=CARD.get(o["nmId"],{"title":"?","vendorCode":o.get("article",""),"subjectName":"?"})
    cr=datetime.datetime.fromisoformat(o["createdAt"].replace("Z","+00:00")).astimezone(SAM)
    k=kind(c)
    rows.append({"id":o["id"],"nm":o["nmId"],"created":cr,"carry":cr.date()<today,"kind":k[1],"ko":k[0],
                 "fab":fabric(c),"vc":c["vendorCode"],"confirm":ss=="confirm","dir":bool(item(o["nmId"])) and is_dir(item(o["nmId"]))})
rows.sort(key=lambda r:(not r["carry"],r["ko"],r["fab"],r["created"]))
# стикеры WB
conf=[r["id"] for r in rows if r["confirm"]]
stick={}
for i in range(0,len(conf),100):
    for s in req(B+"/orders/stickers?type=png&width=58&height=40",{"orders":conf[i:i+100]}).get("stickers",[]): stick[s["orderId"]]=s["file"]
stamp=datetime.datetime.now(SAM).strftime("%Y%m%d_%H%M")
pdf=SP+f"sborka_{stamp}.pdf"
cv=canvas.Canvas(pdf,pagesize=(W,H))
for r in rows:
    f=stick.get(r["id"])
    if f:
        im=Image.open(io.BytesIO(base64.b64decode(f))).convert("L").point(lambda v:255 if v>140 else 0).convert("1")
        bb=io.BytesIO(); im.save(bb,"PNG",optimize=True); bb.seek(0)
        cv.drawImage(ImageReader(bb),0,0,W,H); cv.showPage()
    it=item(r["nm"])
    if it: label(cv,it); cv.showPage()
    r["sticker"]=bool(f)
cv.save()
# публикация PDF
url=None
if rows and not __import__('os').environ.get('TEST'):
    REPO="/home/claude/lucina-photo/photos"
    name=f"sborka_{stamp}_{secrets.token_hex(6)}.pdf"
    subprocess.run(f'mkdir -p {REPO}/labels/kit && cp {pdf} {REPO}/labels/kit/{name} && cd {REPO} && git pull -q --rebase; git add labels/kit && git -c user.name=Claude -c user.email=noreply@anthropic.com commit -qm "labels: sborka {stamp}\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_015ywHCScXCsiQktP2X8NbJk" && (git push -q origin HEAD:main || (git pull -q --rebase && git push -q origin HEAD:main) || (sleep 5; git pull -q --rebase && git push -q origin HEAD:main))',shell=True)
    url=f"https://raw.githubusercontent.com/LUCINA-PHOTO/Photos/main/labels/kit/{name}"
    for i in range(6):
        try:
            if urllib.request.urlopen(url,timeout=30).status==200: break
        except Exception: time.sleep(5)
# сводка
from collections import Counter,OrderedDict
lights=OrderedDict()
for r in rows:
    if r["ko"] in (1,2): lights.setdefault(r["fab"],Counter())[r["kind"]]+=1
other=Counter(r["kind"] for r in rows if r["ko"] not in (1,2))
n=len(rows); places=math.ceil(n/2) if n else 0
dt=datetime.datetime.now(SAM).strftime("%d.%m.%Y %H:%M")
e=html.escape
h=[f"<p><b>Сборка WB на {dt}</b> — заказов: {n} (перенос со вчера: {sum(r['carry'] for r in rows)}, новых: {sum(not r['carry'] for r in rows)}). Грузомест WB: <b>{places}</b> (заказов пополам, вверх).</p>"]
if url: h.append(f'<p><a href="{url}"><b>Открыть PDF этикеток</b></a> — 58×40, масштаб 100%, порядок как в таблице.</p>')
h.append('<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;font-family:Arial;font-size:13px">')
h.append("<tr style='background:#eee'><th>№</th><th>Заказ</th><th>Создан</th><th>Вид</th><th>Ткань</th><th>Артикул</th><th>Отметки</th></tr>")
for i,r in enumerate(rows,1):
    m=[]
    if r["carry"]: m.append("перенос")
    if not r["confirm"]: m.append("<b>не взят в сборку — нет стикера WB</b>")
    elif not r["sticker"]: m.append("стикер WB не получен")
    if r["dir"]: m.append("↑ рисунок вверх")
    bg=" style='background:#fff4d6'" if r["carry"] else ""
    h.append(f"<tr{bg}><td>{i}</td><td>{r['id']}</td><td>{r['created'].strftime('%d.%m %H:%M')}</td><td>{e(r['kind'])}</td><td>{e(r['fab'])}</td><td>{e(r['vc'])}</td><td>{'; '.join(m)}</td></tr>")
h.append("</table>")
if lights:
    h.append("<p><b>Люстры по тканям</b></p><table border='1' cellpadding='4' cellspacing='0' style='border-collapse:collapse;font-family:Arial;font-size:13px'><tr style='background:#eee'><th>Ткань</th><th>Подвесные</th><th>Потолочные</th></tr>")
    for f,c in lights.items(): h.append(f"<tr><td>{e(f)}</td><td>{c['Люстра подвесная'] or ''}</td><td>{c['Люстра потолочная'] or ''}</td></tr>")
    tp=sum(c["Люстра подвесная"] for c in lights.values()); tt=sum(c["Люстра потолочная"] for c in lights.values())
    h.append(f"<tr><td><b>Итого</b></td><td><b>{tp}</b></td><td><b>{tt}</b></td></tr></table>")
if other:
    h.append("<p><b>Остальное:</b> "+", ".join(f"{e(k)} — {v}" for k,v in sorted(other.items()))+"</p>")
if not rows: h=[f"<p><b>Сборка WB на {dt}</b>: заказов на сборке нет.</p>"]
open(SP+"sborka_mail.html","w").write("\n".join(h))
subj=f"WB сборка {datetime.datetime.now(SAM).strftime('%d.%m')} — {n} заказ(ов), грузомест {places}"
open(SP+"sborka_subject.txt","w").write(subj)
print(subj); print(pdf); print(url)
for i,r in enumerate(rows,1): print(i,r["id"],r["kind"],r["fab"],"перенос" if r["carry"] else "", "" if r["confirm"] else "NEW", "стикер" if r.get("sticker") else "")
