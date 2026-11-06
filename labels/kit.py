# Комплект на печать: для каждого заказа FBS «на сборке» — стикер WB, следом этикетка товара (58x40)
import json,sys,base64,io,urllib.request,urllib.error,time
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
sys.path.insert(0,"/home/claude/labels")
from mklabels import label,W,H
SP="/tmp/claude-0/-home-claude/8ff3b9a6-a369-58cb-98f2-fc8b117999e6/scratchpad/"
T=open(SP+"wb_token_mp").read().strip()
B="https://marketplace-api.wildberries.ru/api/v3"
def req(u,body=None):
    r=urllib.request.Request(u,data=json.dumps(body).encode() if body is not None else None,headers={"Authorization":T,"Content-Type":"application/json"},method="POST" if body is not None else "GET")
    for i in range(4):
        try: return json.load(urllib.request.urlopen(r,timeout=60))
        except urllib.error.URLError as e:
            if i==3 or getattr(e,"code",None) not in (None,429,500,502,503): raise
            time.sleep(5)
items={int(k):v for k,v in json.load(open("/home/claude/labels/items.json")).items()}
d=req(B+f"/orders?limit=1000&next=0&dateFrom={int(time.time())-14*86400}")
orders=d["orders"]
st={s["id"]:s for s in req(B+"/orders/status",{"orders":[o["id"] for o in orders]})["orders"]} if orders else {}
want=[o for o in orders if st.get(o["id"],{}).get("supplierStatus")=="confirm"]
if len(sys.argv)>1: want=[o for o in orders if str(o["id"]) in sys.argv[1:]]
print("заказов на сборке:",len(want))
stick={}
if want:
    r=req(B+"/orders/stickers?type=png&width=58&height=40",{"orders":[o["id"] for o in want]})
    stick={s["orderId"]:s["file"] for s in r.get("stickers",[])}
out=SP+"kit_"+time.strftime("%Y%m%d_%H%M")+".pdf"
c=canvas.Canvas(out,pagesize=(W,H))
for o in want:
    f=stick.get(o["id"])
    if f:
        c.drawImage(ImageReader(io.BytesIO(base64.b64decode(f))),0,0,W,H); c.showPage()
    it=items.get(o["nmId"])
    if it: label(c,it); c.showPage()
    print(o["id"],o["nmId"],"стикер" if f else "БЕЗ стикера",it["title"] if it else "нет этикетки")
c.save(); print(out)
