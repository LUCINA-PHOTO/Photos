# Переводит страницы 58x40 (альбом) в книжные 40x58 с поворотом содержимого, чтобы диалог печати не переключал ориентацию.
import sys
from pypdf import PdfReader,PdfWriter,Transformation
from pypdf.generic import RectangleObject
def to_portrait(src,dst,direction="cw"):
    r=PdfReader(src); w=PdfWriter()
    for p in r.pages:
        W=float(p.mediabox.width); H=float(p.mediabox.height)
        if W>H:
            if direction=="cw": t=Transformation().rotate(-90).translate(tx=0,ty=W)
            else: t=Transformation().rotate(90).translate(tx=H,ty=0)
            p.add_transformation(t)
            box=RectangleObject([0,0,H,W])
            p.mediabox=box; p.cropbox=box; p.trimbox=box; p.artbox=box; p.bleedbox=box
        w.add_page(p)
    with open(dst,"wb") as f: w.write(f)
if __name__=="__main__":
    to_portrait(sys.argv[1],sys.argv[2],sys.argv[3] if len(sys.argv)>3 else "cw")
