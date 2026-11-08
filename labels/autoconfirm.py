# Берёт новые заказы WB FBS в сборку: добавляет в открытую поставку (или создаёт новую «LUCINA ДД.ММ»).
import json,time,urllib.request,urllib.error,datetime
SP="/tmp/claude-0/-home-claude/8ff3b9a6-a369-58cb-98f2-fc8b117999e6/scratchpad/"
T=open(SP+"wb_token_mp").read().strip()
H="https://marketplace-api.wildberries.ru"
def call(method,path,body=None):
    r=urllib.request.Request(H+path,data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization":T,"Content-Type":"application/json"},method=method)
    for i in range(5):
        try:
            resp=urllib.request.urlopen(r,timeout=90); txt=resp.read().decode()
            return resp.status,(json.loads(txt) if txt.strip() else None)
        except urllib.error.HTTPError as e:
            if e.code in (429,500,502,503) and i<4: time.sleep(6); continue
            return e.code,e.read().decode()[:400]
        except urllib.error.URLError:
            if i<4: time.sleep(6); continue
            raise
def open_supply():
    nxt=0; cand=[]
    while True:
        st,d=call("GET",f"/api/v3/supplies?limit=1000&next={nxt}")
        if st!=200: raise RuntimeError(f"supplies list {st} {d}")
        cand+=[s for s in d["supplies"] if not s.get("done")]
        if not d["supplies"] or d.get("next",0)==nxt or len(d["supplies"])<1000: break
        nxt=d["next"]
    if cand:
        cand.sort(key=lambda s:s.get("createdAt",""))
        return cand[-1]["id"],False
    name="Поставка от "+datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=4))).strftime("%d.%m.%Y")
    st,d=call("POST","/api/v3/supplies",{"name":name})
    if st not in (200,201): raise RuntimeError(f"supply create {st} {d}")
    return d["id"],True
def confirm_new():
    st,d=call("GET","/api/v3/orders/new")
    if st!=200: raise RuntimeError(f"orders/new {st} {d}")
    ids=[o["id"] for o in d["orders"]]
    if not ids: return {"taken":[],"failed":[],"supply":None}
    sid,created=open_supply()
    taken=[];failed=[]
    # пакетный метод, если есть; иначе по одному
    st,res=call("PATCH",f"/api/marketplace/v3/supplies/{sid}/orders",{"orders":ids})
    if st in (200,204):
        taken=ids
    else:
        for oid in ids:
            s2,r2=call("PATCH",f"/api/v3/supplies/{sid}/orders/{oid}")
            (taken if s2 in (200,204) else failed).append(oid if s2 in (200,204) else (oid,s2,str(r2)[:120]))
    return {"taken":taken,"failed":failed,"supply":sid,"supply_created":created}
if __name__=="__main__":
    print(confirm_new())
