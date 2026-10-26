import shutil, sys
path = "research_analyses.py"
s = open(path).read()
edits = [
 ("import os, sys, time", "import os, sys, time\nimport pandas as pd"),
 ('daily = tot.join(top5, "day").join(top1, "day").toPandas()',
  'daily = pd.DataFrame([r.asDict() for r in tot.join(top5, "day").join(top1, "day").collect()])'),
]
for old, rep in edits:
    c = s.count(old)
    if c != 1:
        sys.exit(f"expected exactly 1 match, found {c} for: {old!r}. Nothing changed.")
    s = s.replace(old, rep)
shutil.copy(path, path + ".bak2"); open(path, "w").write(s); print("patched", path)
