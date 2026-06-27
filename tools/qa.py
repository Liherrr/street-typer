# qa.py  — run with: python tools/qa.py   (from the street-typer/ project root)
# Builds a dark-background contact sheet per character and auto-flags bad frames.
import numpy as np, glob, os, json, sys
from PIL import Image
import cv2
STATES=["intro","idle","attack1","attack2","attack3","attack4","hurt","win","lose"]
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
any_flag=False
for ch in ["p1","p2"]:
    d=f"characters/{ch}"; man=json.load(open(f"{d}/manifest.json"))
    cellw,cellh=150,190; cols=6; sheet=np.full((len(STATES)*cellh,cols*cellw,3),(20,22,34),np.uint8)
    print(f"\n=== {ch}  (ext={man['ext']}) ===")
    for ri,st in enumerate(STATES):
        files=sorted(glob.glob(f"{d}/{st}_*.png"))
        print(f"  {st:8} files={len(files)} manifest={man['states'].get(st,{}).get('count','-')}")
        for ci,fp in enumerate(files[:cols]):
            arr=np.asarray(Image.open(fp).convert("RGBA")); H,W=arr.shape[:2]
            a=arr[...,3]; af=(a/255.0)[...,None]
            bg=np.zeros((H,W,3),np.uint8); bg[:]=(20,22,34)
            comp=(arr[...,:3]*af+bg*(1-af)).astype(np.uint8)
            cv2.line(comp,(0,int(0.96*H)),(W,int(0.96*H)),(255,80,80),1)   # baseline
            # ---- automatic flags ----
            ys,xs=np.where(a>40)
            flags=[]
            if len(ys):
                if ys.min()<=1 or ys.max()>=H-1 or xs.min()<=1 or xs.max()>=W-1: flags.append("CLIPPED-EDGE")
                if (ys.max()-ys.min())<0.70*H: flags.append("SHORT(no legs?)")
                if ys.max()<0.90*H: flags.append("FEET-OFF-BASELINE")
                hsv=cv2.cvtColor(arr[...,:3],cv2.COLOR_RGB2HSV)
                bright=((a>40)&(arr[...,:3].mean(2)>150)&(hsv[...,1]<70)).mean()*100
                if bright>0.4: flags.append(f"BRIGHT-REMNANT({bright:.1f}%)")
            else:
                flags.append("EMPTY")
            if flags:
                any_flag=True
                print(f"      ! {os.path.basename(fp)}: {', '.join(flags)}")
            comp=cv2.resize(comp,(cellw,cellh)); sheet[ri*cellh:(ri+1)*cellh,ci*cellw:(ci+1)*cellw]=comp
    Image.fromarray(sheet).save(f"qa_{ch}_dark.png")
    dims={Image.open(f).size for f in glob.glob(f"{d}/*.png")}
    print(f"  dims={dims} (must be one size); files vs manifest must match above")
print("\nOpen qa_p1_dark.png and qa_p2_dark.png and inspect every frame.")
print("RESULT:", "FLAGS PRESENT" if any_flag else "ZERO FLAGS")
