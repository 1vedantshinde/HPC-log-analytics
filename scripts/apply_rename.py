import os, sys
old, new = "app/pages/1_Research_Findings.py", "app/pages/2_Behavior_Analysis.py"
if not os.path.exists(old):
    sys.exit(old + " not found. Nothing changed.")
if os.path.exists(new):
    sys.exit(new + " already exists. Nothing changed.")
s = open(old).read()
for a, b in [('st.set_page_config(page_title="Research findings", layout="wide")',
              'st.set_page_config(page_title="Behavior analysis", layout="wide")'),
             ('st.title("Research findings")', 'st.title("Behavior analysis")')]:
    c = s.count(a)
    if c != 1:
        sys.exit("expected exactly 1 match, found " + str(c) + " for: " + a + ". Nothing changed.")
    s = s.replace(a, b)
open(new, "w").write(s)
os.replace(old, old + ".renamed.bak")
print("created", new, "| old file kept as", old + ".renamed.bak")
