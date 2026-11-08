# Обёртка: при ошибке всё равно кладёт part-файл с пометкой об ошибке
import subprocess,sys,json,datetime,traceback
r=subprocess.run([sys.executable,"/home/claude/labels/morning.py"],capture_output=True,text=True,timeout=1200)
print(r.stdout[-4000:])
if r.returncode!=0:
    print(r.stderr[-3000:])
    SAM=datetime.timezone(datetime.timedelta(hours=4)); now=datetime.datetime.now(SAM)
    SP="/tmp/claude-0/-home-claude/8ff3b9a6-a369-58cb-98f2-fc8b117999e6/scratchpad/"
    pname=now.strftime("%Y-%m-%d")+"_wb.json"
    err=(r.stderr.strip().splitlines() or ["?"])[-1][:300]
    json.dump({"market":"wb","generated_at":now.strftime("%Y-%m-%d %H:%M"),"rows":[],"summary":{},"pdf_url":None,
               "notes":[f"ОШИБКА сборки WB: {err}. Этикетки напечатать в кабинете WB."],"places":None},open(SP+pname,"w"),ensure_ascii=False,indent=1)
    REPO="/home/claude/lucina-photo/photos"
    subprocess.run(f'cd {REPO} && git pull -q --rebase; mkdir -p labels/kit/parts && cp {SP+pname} labels/kit/parts/ && git add labels/kit/parts && git -c user.name=Claude -c user.email=noreply@anthropic.com commit -qm "labels: wb part {pname} (error)\\n\\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\\nClaude-Session: https://claude.ai/code/session_015ywHCScXCsiQktP2X8NbJk" && (git push -q origin HEAD:main || (git pull -q --rebase && git push -q origin HEAD:main))',shell=True)
    print("ERROR part written"); sys.exit(1)
