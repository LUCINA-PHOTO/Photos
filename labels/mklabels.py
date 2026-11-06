import json,sys
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.barcode import code128
pdfmetrics.registerFont(TTFont("DV","/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf"))
pdfmetrics.registerFont(TTFont("DVB","/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"))
W,H=58*mm,40*mm
import sys as _s; _s.path.insert(0,'/home/claude/labels'); from names import fix
def wrap(t,font,size,maxw):
    out=[];line=""
    for w in t.split():
        s=(line+" "+w).strip()
        if pdfmetrics.stringWidth(s,font,size)<=maxw: line=s
        else: out.append(line); line=w
    out.append(line); return out
DIR=("луговые цветы","зеленая листва","зелёная листва","красные маки","леопард","пантера","мишка")
def is_dir(item):
    v=item["vc"].lower()
    return any(k in v for k in DIR)
def arrow(c):
    x=4.2*mm; y0=1.5*mm; y1=37.5*mm
    c.setLineWidth(2.2*mm); c.line(x,y0,x,y1-4*mm)
    p=c.beginPath(); p.moveTo(x-3.3*mm,y1-5*mm); p.lineTo(x+3.3*mm,y1-5*mm); p.lineTo(x,y1); p.close()
    c.drawPath(p,fill=1,stroke=0)
    c.setLineWidth(1)
def label(c,item):
    d=is_dir(item)
    if d: arrow(c)
    L=9*mm if d else 0
    bc=item["barcode"]
    b=code128.Code128(bc,barHeight=13*mm,barWidth=0.33*mm,humanReadable=False,quiet=False)
    bw=b.width
    if bw>W-4*mm-L:
        b=code128.Code128(bc,barHeight=13*mm,barWidth=0.33*mm*(W-4*mm-L)/bw,humanReadable=False,quiet=False); bw=b.width
    b.drawOn(c,L+(W-L-bw)/2,H-2*mm-13*mm)
    c.setFont("DVB",9); c.drawCentredString(L+(W-L)/2,H-19*mm,bc)
    c.setFont("DV",6.6)
    y=H-22.5*mm
    for ln in wrap(item["title"],"DV",6.6,W-3*mm-L)[:3]:
        c.drawCentredString(L+(W-L)/2,y,ln); y-=2.6*mm
    c.setFont("DV",6)
    c.drawString(1.5*mm+L,4.0*mm,("Арт.: "+item["vc"])[:44-int(L/mm*1.3)])
    c.drawString(1.5*mm+L,1.2*mm,"Бренд: LUCINA")
    c.drawRightString(W-1.5*mm,1.2*mm,"WB "+str(item["nm"]))
def build(items,out):
    c=canvas.Canvas(out,pagesize=(W,H))
    for it in items: label(c,it); c.showPage()
    c.save()
if __name__=="__main__":
    cards=json.load(open(sys.argv[1]))
    order={"Люстры":0,"Абажуры":1}
    items=[]
    for cd in sorted(cards,key=lambda c:(order.get(c["subjectName"],2),c["title"])):
        for z in cd["sizes"]:
            for s in z["skus"]:
                items.append({"barcode":s,"title":cd["title"],"vc":cd["vendorCode"],"nm":cd["nmID"]})
    json.dump({i["nm"]:i for i in items},open("/home/claude/labels/items.json","w"),ensure_ascii=False)
    build(items,sys.argv[2]); print(len(items))
