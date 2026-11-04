from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parent
home="--home" in sys.argv
directory=root/("home-models" if home else "exact-models")
directory.mkdir(exist_ok=True)
jobs=sorted((root/"models").glob("[0-9]*.json"))
def job(path):
    target=directory/path.name
    if target.exists():return json.loads(target.read_text())
    design=json.loads(path.read_text());case=design["case"]
    command=["/tmp/ahc074-patch-home" if home else "/tmp/ahc074-patch-exact",f"/home/sato/ahc074/tools/in/{case:04d}.txt",
             f"/home/sato/ahc074/runs/20261103-033246_as6-canon/out/{case:04d}.txt",
             str(design["mask"]),str(design["color"]),"4"]
    with (directory/f"{path.stem}.err").open("w") as log:
        result=subprocess.run(command,stdout=subprocess.PIPE,stderr=log,text=True,check=True,timeout=600)
    row=json.loads(result.stdout);row.update(case=case,price=design["price"],mask=design["mask"],color=design["color"])
    target.write_text(json.dumps(row,indent=2)+"\n")
    a=row["models"][0]
    print(path.stem,[(b["variant"],b["cost"]-a["cost"],b["novel"],b["novel_fee"]) for b in row["models"][1:]],flush=True)
    return row
with ThreadPoolExecutor(max_workers=2) as pool:
    rows=list(pool.map(job,jobs))
(directory/"summary.json").write_text(json.dumps(rows,indent=2)+"\n")
