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
import os as _os
AC={"taken":[],"failed":[],"supply":None}
if not _os.environ.get("TEST"):
    try:
        import autoconfirm; AC=autoconfirm.confirm_new()
    except Exception as _e: AC={"taken":[],"failed":[("ошибка",str(_e)[:200])],"supply":None}
print("в сборку:",AC)
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
SLOT=__import__("os").environ.get("SLOT","")  # "" — утро, "1500" — дневная часть
MORNING_MISSING=False
if SLOT:
    mfile=today.strftime("%Y-%m-%d")+"_wb.json"; seen=set()
    try:
        mj=json.load(open(SP+mfile))
    except Exception:
        try: mj=json.load(urllib.request.urlopen("https://raw.githubusercontent.com/LUCINA-PHOTO/Photos/main/labels/kit/parts/"+mfile,timeout=30))
        except Exception: mj=None; MORNING_MISSING=True
    if mj: seen={str(r["order"]) for r in mj.get("rows",[])}
    rows=[r for r in rows if str(r["id"]) not in seen]
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
n=len(rows)
# Грузоместа (правило Сергея 09.11): большие (абажур 37, подвесная, потолочная) по 2 в место;
# все абажурчики дня — одно место; если абажурчик один и есть большие — кладётся третьим в последнее место;
# полка = абажурчик; торшер и прочее — место не создаётся, вопрос Сергею.
# Полка приравнена к абажурчику; торшер — место не создаём, спрашиваем Сергея.
big=sum(1 for r in rows if r["ko"] in (1,2,3))
small=sum(1 for r in rows if r["ko"]==4 or (r["ko"]>=5 and "олк" in r["kind"]))
tor=sum(1 for r in rows if r["ko"]>=5 and "олк" not in r["kind"])
oth=0
places=math.ceil(big/2)+(0 if small==0 or (small==1 and big>0) else 1)
import os
nowS=datetime.datetime.now(SAM)
out_rows=[]
for i,r in enumerate(rows,1):
    m=[]
    if not r["confirm"]: m.append("не взят в сборку — нет стикера WB")
    elif not r["sticker"]: m.append("стикер WB не получен")
    out_rows.append({"n":i,"order":str(r["id"]),"kind":r["kind"],"fabric":r["fab"],"qty":1,
        "slot_or_marks":"; ".join(m) or None,"deadline":None,"created":r["created"].strftime("%Y-%m-%d %H:%M"),
        "article":r["vc"],"carry":r["carry"],"arrow":r["dir"],
        "flags":[x for x,y in (("перенос",r["carry"]),("стрелка",r["dir"])) if y]})
summary={"lights_by_fabric":[{"fabric":f,"podvesnye":c["Люстра подвесная"],"potolochnye":c["Люстра потолочная"]} for f,c in lights.items()],
         "lights_total":{"podvesnye":sum(c["Люстра подвесная"] for c in lights.values()),"potolochnye":sum(c["Люстра потолочная"] for c in lights.values())},
         "other":dict(sorted(other.items())),"orders_total":n}
notes=[f"Грузомест WB: {places} (большие по 2 в место: {big}; абажурчики и полки одним местом: {small}{', третьим в последнее место' if small==1 and big>0 else ''}; полки считаются как абажурчики)"]
if tor: notes.append(f"ВОПРОС СЕРГЕЮ: в сборке торшер/прочее ({tor} шт.) — грузоместо под него не создано, как упаковать?")
nn=sum(1 for r in rows if not r["confirm"])
if nn: notes.append(f"{nn} заказ(ов) не взяты в сборку — стикер WB появится после добавления в поставку; в PDF только этикетка товара")
ns=sum(1 for r in rows if r["confirm"] and not r["sticker"])
if ns: notes.append(f"{ns} стикер(ов) WB не получены по API — напечатать в кабинете")
if AC.get("taken"): notes.append(f"Взято в сборку автоматически: {len(AC['taken'])} (поставка {AC['supply']})")
if AC.get("failed"): notes.append(f"Не удалось взять в сборку: {AC['failed']}")
if not rows: notes=["Новых заказов WB после утреннего файла нет" if SLOT else "Заказов WB на сборке нет"]
if SLOT: notes.insert(0,"Дневная часть 15:00: только заказы, которых не было в утреннем файле"+(" (утренний файл не найден — показаны все заказы на сборке)" if MORNING_MISSING else ""))
part={"market":"wb","slot":SLOT or "0900","generated_at":nowS.strftime("%Y-%m-%d %H:%M"),"rows":out_rows,"summary":summary,
      "pdf_url":url,"notes":notes,"places":places}
pname=nowS.strftime("%Y-%m-%d")+(f"_{SLOT}" if SLOT else "")+"_wb.json"
json.dump(part,open(SP+pname,"w"),ensure_ascii=False,indent=1)
if not os.environ.get("TEST"):
    REPO="/home/claude/lucina-photo/photos"
    cl=subprocess.run(f"cd {REPO} && git pull -q --rebase; mkdir -p labels/kit/parts && cp {SP+pname} labels/kit/parts/{pname} && git add labels/kit/parts",shell=True)
    # удалить файлы labels/kit старше 7 дней (по дате последнего коммита)
    lim=time.time()-7*86400
    files=subprocess.run(f"cd {REPO} && git ls-files labels/kit",shell=True,capture_output=True,text=True).stdout.split()
    old=[]
    for f in files:
        ct=subprocess.run(f"cd {REPO} && git log -1 --format=%ct -- '{f}'",shell=True,capture_output=True,text=True).stdout.strip()
        if ct and int(ct)<lim: old.append(f)
    if old: subprocess.run(["git","-C",REPO,"rm","-q","--"]+old)
    subprocess.run(f'cd {REPO} && git -c user.name=Claude -c user.email=noreply@anthropic.com commit -qm "labels: wb part {pname}; cleanup {len(old)} old\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\nClaude-Session: https://claude.ai/code/session_015ywHCScXCsiQktP2X8NbJk" && (git push -q origin HEAD:main || (git pull -q --rebase && git push -q origin HEAD:main) || (sleep 5; git pull -q --rebase && git push -q origin HEAD:main))',shell=True)
    print("removed old:",len(old))
print(json.dumps({k:part[k] for k in ("generated_at","pdf_url","notes","summary")},ensure_ascii=False))
print("part:",pname)
for r in out_rows: print(r["n"],r["order"],r["kind"],r["fabric"],r["flags"],r["slot_or_marks"] or "")
