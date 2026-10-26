from collections import defaultdict
from pymongo import MongoClient
import glossary.template_glossary as tg

ok = True


def check(name, cond, extra=""):
    global ok
    print(("PASS  " if cond else "FAIL  ") + name + (("   " + extra) if extra else ""))
    ok = ok and cond


# 1. masking rules identical to your masking.py
try:
    import utils.masking as masking
    check("MASK_RULES identical to masking.RULES", masking.RULES == tg.MASK_RULES)
except Exception as e:
    check("import masking.py", False, repr(e))

# 2. rule self-tests (shapes taken from your screenshot, both digit styles)
TESTS = [
    ("xinetd: START: rsync pid=<N> from=<IP>", "Network services"),
    ("ntpd: synchronized to <IP>, stratum <N>", "Time sync"),
    ("crond(pam_unix): session closed for user root", "Scheduled jobs"),
    ("crond(pam_unix): session opened for user root by (uid=<N>)", "Scheduled jobs"),
    ('sshd: connection from "<ANON>"', "Logins & sessions"),
    ("crond: (root) CMD (run-parts /etc/cron.hourly)", "Scheduled jobs"),
    ("sshd(pam_unix): session opened for user root by (uid=<N>)", "Logins & sessions"),
    ("sshd: Accepted publickey for root from ::ffff:<IP> port <N> ssh2", "Logins & sessions"),
    ("sshd: connection lost: 'Connection closed.'", "Logins & sessions"),
    ("sshd: Local disconnected: Connection closed.", "Logins & sessions"),
    ("sshd2: Now running on <ANON>'s privileges.", "Logins & sessions"),
    ("sshd: authentication cancelled by user: 'Authentication cancelled by user.'", "Logins & sessions"),
    ("sshd: User <ANON>, coming from tbird-<ANON>, authenticated.", "Logins & sessions"),
    ("ib_sm: [ib_sm_sweep.c:<N>]: ********************* NEW SWEEP *********************", "InfiniBand network"),
    ("ib_sm: [ib_sm_sweep.c:<N>]: No topology change", "InfiniBand network"),
    ("ib_sm: [ib_sm_discovery.c:<N>]: Failed to GetNodeInfo() because of NO RESPONSE", "InfiniBand network"),
    ("dhcpd: DHCPDISCOVER from <MAC> via eth<N>: network B_net: no free leases", "Network services"),
    ("dhcpd: DHCPDISCOVER from <MAC> via eth1: network B_net: no free leases", "Network services"),
    ("RT: About to think about scrips for transaction #<N>", "Other services"),
    ("kernel: [KERNEL_IB][tsIbTavorMadProcess][/mnt_projects/sysapps/src/ib/topspin/x] (Fatal error)", "InfiniBand network"),
    ("kernel: THH(<N>): mnt_projects/sysapps/src/ib/topspin/third_party/thca<N>_linux/k", "InfiniBand network"),
    ("kernel: scsi<N> (<N>:<N>): rejecting I/O to offline device", "Storage & filesystems"),
    ("kernel: scsi0 (<N>:<N>): rejecting I/O to offline device", "Storage & filesystems"),
    ("kernel: EXT<N>-fs error (device sda<N>) in start_transaction: Journal has aborted", "Storage & filesystems"),
    ("kernel: EXT3-fs error (device sda5) in start_transaction: Journal has aborted", "Storage & filesystems"),
    ("kernel: ext<N>_journal_start_sb: Detected aborted journal", "Storage & filesystems"),
    ("kernel: mptscsih: ioc<N>: attempting task abort! (sc=<HEX>)", "Storage & filesystems"),
    ("kernel: mptscsih: ioc0: attempting task abort! (sc=<HEX>)", "Storage & filesystems"),
    ("kernel: Losing some ticks... checking if CPU frequency changed.", "Kernel (general)"),
    ("kernel: Uhhuh. NMI received for unknown reason <HEX>.", "Hardware health"),
    ("pbs_mom: Bad file descriptor (<N>) in tm_request, job <N>.tbird-admin<N> not running", "Job scheduler (PBS)"),
    ("pbs_mom: Connection refused (<N>) in", "Job scheduler (PBS)"),
    ("(none): Server Administrator: Instrumentation Service EventID: <N>", "Hardware health"),
]
for t, cat in TESTS:
    e = tg.explain(t)
    check("rule: " + t[:70], e["category"] == cat and e["level"] == "specific", "got " + e["level"] + "/" + e["category"])

db = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=5000)["thunderbird"]

# 3. Python parse+mask reproduces the stored templates from their stored real examples
tot = same = skipped = 0
bad = []
for d in db.templates.aggregate([{"$sample": {"size": 3000}}]):
    t = d["template"]
    if t == "(empty)":
        skipped += 1
        continue
    prog = t.split(": ", 1)[0]
    for m in (d.get("sample_msgs") or []):
        rest = m if prog == "(none)" else prog + ": " + m
        got = tg.template_from_rest(rest)[0]
        tot += 1
        if got == t:
            same += 1
        elif len(bad) < 8:
            bad.append((t, got, m))
rate = same / tot if tot else 0
check("Python masking port reproduces stored templates", rate >= 0.995,
      f"{same:,}/{tot:,} messages = {rate:.2%} (skipped {skipped} '(empty)' templates)")
for t, got, m in bad:
    print("   stored  :", t[:160]); print("   python  :", got[:160]); print("   message :", m[:160]); print()

# 4. coverage over ALL templates
rows = list(db.templates.find({}, {"template": 1, "n": 1}))
total = sum(r["n"] for r in rows)
by_level, by_cat, unexpl = defaultdict(lambda: [0, 0]), defaultdict(int), []
for r in rows:
    e = tg.explain(r["template"])
    by_level[e["level"]][0] += r["n"]
    by_level[e["level"]][1] += 1
    by_cat[e["category"]] += r["n"]
    if e["level"] != "specific":
        unexpl.append((r["n"], e["level"], e["readable"]))
print("\nCOVERAGE (share of all lines / number of templates)")
for lvl in ["specific", "program", "keyword", "none"]:
    n, k = by_level[lvl]
    print(f"  {lvl:9s} {n / total:7.2%}   {k:>7,} templates")
print("\nLINES BY CATEGORY")
for c, n in sorted(by_cat.items(), key=lambda kv: -kv[1]):
    print(f"  {n / total:7.2%}  {c}")
print("\nTOP 25 TEMPLATES WITHOUT A SPECIFIC EXPLANATION (by lines)")
for n, lvl, rd in sorted(unexpl, reverse=True)[:25]:
    print(f"  {n:>12,} {n / total:6.2%} [{lvl}] {rd[:150]}")

# 5. alert labels covered by the glossary
labels = [x for x in db.alerts.distinct("label")]
missing = [x for x in labels if x not in tg.ALERT_LABELS]
check("every alert label has a glossary entry", not missing, "missing: " + str(missing))

print("\nALL CHECKS PASSED" if ok else "\nSOME CHECKS FAILED (see FAIL lines above)")
