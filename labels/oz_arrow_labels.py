import json,sys
sys.path.insert(0,'/home/claude/photos/labels')
import types; sys.modules['names']=types.SimpleNamespace(fix=lambda x:x)
import mklabels as M
from reportlab.pdfgen import canvas
def label(c,it):
    W,H,mm=M.W,M.H,M.mm
    M.arrow(c); L=9*mm
    bc=it['barcode']
    from reportlab.graphics.barcode import code128
    b=code128.Code128(bc,barHeight=13*mm,barWidth=0.33*mm,humanReadable=False,quiet=False); bw=b.width
    if bw>W-4*mm-L:
        b=code128.Code128(bc,barHeight=13*mm,barWidth=0.33*mm*(W-4*mm-L)/bw,humanReadable=False,quiet=False); bw=b.width
    b.drawOn(c,L+(W-L-bw)/2,H-2*mm-13*mm)
    c.setFont('DVB',9); c.drawCentredString(L+(W-L)/2,H-19*mm,bc)
    c.setFont('DV',6.6); y=H-22.5*mm
    for ln in M.wrap(it['title'],'DV',6.6,W-3*mm-L)[:3]:
        c.drawCentredString(L+(W-L)/2,y,ln); y-=2.6*mm
    c.setFont('DV',6)
    c.drawString(1.5*mm+L,4.0*mm,('Арт.: '+it['vc'])[:32])
    c.drawString(1.5*mm+L,1.2*mm,'Бренд: LUCINA')
    c.drawRightString(W-1.5*mm,1.2*mm,'OZON '+str(it['sku']))
items=json.load(open('arrow_items.json'))
rank={'Абажур':0,'Абажурчик':1,'Подвесной':2,'Потолочный':3}
items.sort(key=lambda i:(rank.get(i['vc'].split('-')[0],4),i['vc']))
out=sys.argv[1]
c=canvas.Canvas(out,pagesize=(M.W,M.H))
for it in items: label(c,it); c.showPage()
c.save(); print(len(items))
