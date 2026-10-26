"""Plain-English decoding of Thunderbird log templates. Pure Python (no Spark/Mongo)."""
import re

NUM = r"(?:\d+|<N>)"   # a number that may or may not have been masked

# ---- copy of masking.py RULES (verify_glossary.py checks they are identical) ----
MASK_RULES = [
    (r"(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}", "<MAC>"),
    (r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "<IP>"),
    (r"0x[0-9a-fA-F]+", "<HEX>"),
    (r"krb5cc_\w+", "krb5cc_<ID>"),
    (r"\bI-x\w+(?:-x\w+)*", "<OBJID>"),
    (r"\b[jk](?=[A-Za-z]*\d)(?=[0-9a-z]*[A-Z])[0-9A-Za-z]{8,}\b", "<QID>"),
    (r"/tmp/tmp\.\w+", "/tmp/tmp.<ID>"),
    (r"\b(?=[0-9]*[a-fA-F])[0-9a-fA-F]{8,}\b", "<HEX>"),
    (r"#\d+#", "<ANON>"),
    (r"\d+", "<N>"),
]
MASK_RULE_NOTES = [
    "MAC address (aa:bb:cc:dd:ee:ff)",
    "IPv4 address",
    "hex number starting 0x",
    "Kerberos credential-cache name (krb5cc_...)",
    "object ID starting I-x",
    "queue-style ID (starts with j or k, 8+ letters/digits, mixed case)",
    "temporary file name /tmp/tmp.xxxx",
    "long hex string (8+ hex characters including a letter)",
    "anonymized token written #number#",
    "any other number",
]
_MASK = [(re.compile(p, re.ASCII), r) for p, r in MASK_RULES]


def mask_msg(s):
    for rx, rep in _MASK:
        s = rx.sub(rep, s)
    return s


PLACEHOLDERS = {
    "<N>":     ("[number]", "Any run of digits: counters, process IDs, ports, device numbers, line numbers."),
    "<IP>":    ("[IP address]", "An IPv4 address (four numbers separated by dots)."),
    "<MAC>":   ("[MAC address]", "A hardware network-card address such as aa:bb:cc:dd:ee:ff."),
    "<HEX>":   ("[hex value]", "A hexadecimal value: 0x..., or 8+ hex characters containing a letter a-f."),
    "<ANON>":  ("[anonymized]", "A value (for example a user or host name) that the dataset's publishers anonymized; it appears as #number# in the raw log."),
    "<OBJID>": ("[object ID]", "An identifier starting with I-x."),
    "<QID>":   ("[queue-style ID]", "An identifier starting with j or k followed by 8+ mixed-case letters/digits (pattern from masking.py)."),
    "<ID>":    ("[ID]", "A random-looking suffix, e.g. in krb5cc_... (Kerberos ticket cache) or /tmp/tmp.... (temporary file)."),
}
_TOK = re.compile(r"<(MAC|IP|HEX|OBJID|QID|ID|ANON|N)>")
_TOKEN_RX = {
    "N": r"(\d+)", "IP": r"(\d{1,3}(?:\.\d{1,3}){3})",
    "MAC": r"((?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})",
    "HEX": r"(0x[0-9a-fA-F]+|[0-9a-fA-F]{8,})", "ANON": r"(#\d+#)",
    "OBJID": r"(I-x\w+(?:-x\w+)*)", "QID": r"([jk][0-9A-Za-z]{8,})", "ID": r"(\w+)",
}


def readable(template):
    return _TOK.sub(lambda m: PLACEHOLDERS["<" + m.group(1) + ">"][0], template)


def variables_in(template):
    seen, out = set(), []
    for m in _TOK.finditer(template):
        k = "<" + m.group(1) + ">"
        if k not in seen:
            seen.add(k)
            out.append((k, PLACEHOLDERS[k][0], PLACEHOLDERS[k][1]))
    return out


# ---- parsing a raw line the same way process_full.py does ----
_PROG = re.compile(r"^([^\s\[:]+)(?:\[(\d+)\])?:\s?(.*)$")


def split_raw_line(line):
    parts = line.strip("\r\n").split(None, 8)
    if len(parts) < 4 or not parts[1].isdigit():
        return None
    return {"label": parts[0], "epoch": int(parts[1]), "node": parts[3],
            "rest": parts[8] if len(parts) > 8 else ""}


def template_from_rest(rest):
    m = _PROG.match(rest)
    prog = m.group(1) if m else ""
    msg = m.group(3) if m else rest
    program = prog or None
    if msg == "":
        return "(empty)", program, msg
    return (program or "(none)") + ": " + mask_msg(msg), program, msg


def extract_values(template, msg):
    """Which concrete values sat where each placeholder is. None if it can't be aligned."""
    body = template.split(": ", 1)[1] if ": " in template else template
    toks = list(_TOK.finditer(body))
    if not toks or len(toks) > 10 or len(msg) > 600:
        return None
    pat, pos = "", 0
    for m in toks:
        pat += re.escape(body[pos:m.start()]) + _TOKEN_RX[m.group(1)]
        pos = m.end()
    pat += re.escape(body[pos:])
    try:
        mm = re.fullmatch(pat, msg, re.ASCII)
    except re.error:
        return None
    if not mm:
        return None
    return [(PLACEHOLDERS["<" + t.group(1) + ">"][0], v) for t, v in zip(toks, mm.groups())]


# ---- programs: key -> (display name, description, category, basis) ----
PROGRAMS = {
    "kernel": ("Linux kernel", "The operating-system core. Its messages cover hardware drivers, disks and filesystems, and the network.", "Kernel (general)", "standard Linux"),
    "sshd": ("SSH server (sshd)", "Handles remote logins over SSH.", "Logins & sessions", "standard software"),
    "sshd2": ("SSH server (sshd2)", "A variant of the SSH login server.", "Logins & sessions", "standard software"),
    "login": ("login", "Console/terminal logins.", "Logins & sessions", "standard software"),
    "su": ("su", "Switching to another user account.", "Logins & sessions", "standard software"),
    "sudo": ("sudo", "Running a command with another user's privileges.", "Logins & sessions", "standard software"),
    "crond": ("Cron scheduler (crond)", "Runs scheduled jobs (hourly, daily, ...) on each node.", "Scheduled jobs", "standard software"),
    "anacron": ("anacron", "Runs scheduled jobs that were missed while the machine was off.", "Scheduled jobs", "standard software"),
    "atd": ("at daemon (atd)", "Runs one-off jobs scheduled with the 'at' command.", "Scheduled jobs", "standard software"),
    "xinetd": ("xinetd", "A 'super-server' that starts network services (e.g. rsync) on demand when another machine connects.", "Network services", "standard software"),
    "ntpd": ("NTP daemon (ntpd)", "Keeps a node's clock in sync with a time server.", "Time sync", "standard software"),
    "dhcpd": ("DHCP server (dhcpd)", "Hands out IP addresses and network settings to machines that ask for them.", "Network services", "standard software"),
    "named": ("DNS server (named)", "Answers host-name lookups.", "Network services", "standard software"),
    "snmpd": ("SNMP agent (snmpd)", "Answers network-management queries.", "Network services", "standard software"),
    "pbs_mom": ("PBS node agent (pbs_mom)", "Runs on each compute node; starts, monitors and cleans up the batch jobs the PBS scheduler gives it ('MOM' = Machine Oriented Mini-server).", "Job scheduler (PBS)", "standard PBS/Torque software"),
    "pbs_server": ("PBS server", "The central PBS daemon that queues jobs and tracks nodes.", "Job scheduler (PBS)", "standard PBS/Torque software"),
    "pbs_sched": ("PBS scheduler", "Decides which queued job runs where.", "Job scheduler (PBS)", "standard PBS/Torque software"),
    "ib_sm": ("InfiniBand subnet manager (ib_sm)", "Discovers and configures the InfiniBand network that links the nodes.", "InfiniBand network", "inferred from the name and message text"),
    "RT": ("RT application", "A program whose messages print file paths under /opt/rt3/, most likely the Request Tracker ticket system.", "Other services", "inferred from file paths in the messages"),
    "syslog-ng": ("syslog-ng", "Collects and forwards log messages.", "System services", "standard software"),
    "syslogd": ("syslogd", "Collects and stores log messages.", "System services", "standard software"),
    "klogd": ("klogd", "Passes kernel messages to the system log.", "System services", "standard software"),
    "gmond": ("Ganglia monitor (gmond)", "Reports node metrics (load, memory, ...) to the Ganglia monitoring system.", "Monitoring", "standard software"),
    "smartd": ("SMART disk monitor (smartd)", "Watches disks' built-in health indicators.", "Storage & filesystems", "standard software"),
    "automount": ("Automounter", "Mounts network filesystems on demand.", "Storage & filesystems", "standard software"),
    "sendmail": ("sendmail", "Mail server.", "System services", "standard software"),
    "postfix": ("postfix", "Mail server.", "System services", "standard software"),
}

CATEGORY_ORDER = ["Logins & sessions", "Scheduled jobs", "Time sync", "Network services", "InfiniBand network",
                  "Storage & filesystems", "Job scheduler (PBS)", "Hardware health", "Kernel (general)",
                  "System services", "Monitoring", "Other services", "Unclassified"]

_RULES = []


def _add(pattern, category, headline, detail, basis):
    _RULES.append((re.compile(pattern, re.I), category, headline, detail, basis))


_PAPER = "source paper (Oliner & Stearley) + message text"
_TXT = "message text (literal reading)"

_add(r"^\(empty\)$", "Unclassified", "Empty message",
     "The line had a valid header but no message text after the program name.", "pipeline rule in process_full.py")
_add(r"\[KERNEL_IB\]", "InfiniBand network", "InfiniBand driver error report",
     "The kernel's InfiniBand driver stack printed a report tagged [KERNEL_IB]. InfiniBand is the high-speed network linking the nodes. The experts' 'VAPI' alert tag is attached to messages of this kind; the source paper calls them 'Local Catastrophic Errors' and says many were not well understood. Only some lines of this family carry the tag, so check the Alerts count.", _PAPER)
_add(r"^kernel: (?:THH|VIPKL|MOSAL)\(", "InfiniBand network", "InfiniBand adapter driver message",
     "THH, VIPKL and MOSAL are prefixes used by the InfiniBand adapter driver's code (the file paths in these messages point into the Topspin InfiniBand source tree). A VIPKL line with a VAPI error code appears in the source paper.", "inferred from file paths in the messages + source paper")
_add(r"^ib_sm: .*NEW SWEEP", "InfiniBand network", "The InfiniBand subnet manager started a new network scan",
     "A 'sweep' is a periodic pass over the InfiniBand network to check devices and routes. One line per scan, so the count is large.", "inferred from program name and message text")
_add(r"^ib_sm: .*No topology change", "InfiniBand network", "Network scan finished: nothing changed",
     "The subnet manager's scan found the same InfiniBand devices and links as last time.", _TXT)
_add(r"^ib_sm: .*No configuration change", "InfiniBand network", "Network scan finished: no reconfiguration needed",
     "The subnet manager's scan found nothing to reconfigure.", _TXT)
_add(r"^ib_sm: .*Failed to GetNodeInfo.*NO RESPONSE", "InfiniBand network", "The subnet manager got no answer from an InfiniBand device",
     "It asked a device for its node information (GetNodeInfo) and the device did not respond. The message also lists hop count and path details.", _TXT)
_add(r"^ib_sm: .*Failed to GetNodeInfo", "InfiniBand network", "The subnet manager could not read an InfiniBand device's information",
     "The GetNodeInfo request to a device failed.", _TXT)
_add(r"^dhcpd: DHCPDISCOVER.*no free leases", "Network services", "A machine asked for an IP address but none were available",
     "DHCPDISCOVER is a machine asking the network for settings; 'no free leases' means the server's address pool for that network had no free address. The line names the requesting machine's MAC address.", _TXT)
_add(r"^dhcpd: DHCP(?:DISCOVER|OFFER|REQUEST|ACK|NAK|INFORM|RELEASE)", "Network services", "DHCP address negotiation",
     "A step in the exchange where a machine asks a DHCP server for network settings.", "standard DHCP behaviour")
_add(r"^xinetd: START: (?P<svc>\S+)", "Network services", "xinetd started a service for an incoming connection",
     "xinetd launched the '{svc}' service because another machine connected to it (pid is the new process, from is who connected). One line per connection, so busy services produce huge counts.", "message text + standard xinetd behaviour")
_add(r"^ntpd: synchronized to", "Time sync", "A node's clock synchronised to a time server",
     "ntpd reports which server (IP) it is following and its stratum, the number of hops from a reference clock (1 = directly attached, larger = further away).", "message text + standard NTP behaviour")
_add(r"^crond\(pam_unix\): session (?P<what>opened|closed)", "Scheduled jobs", "A scheduled (cron) job's login session {what}",
     "cron opens a short session for the user (usually root) each time it runs a job and closes it afterwards. PAM is Linux's authentication framework.", "message text + standard cron/PAM behaviour")
_add(r"^crond: \((?P<user>[^)]*)\) CMD \((?P<cmd>.*)\)", "Scheduled jobs", "cron ran a scheduled command",
     "cron ran this command as user '{user}': {cmd}. For example, run-parts /etc/cron.hourly runs every script in the hourly maintenance folder.", "message text + standard cron behaviour")
_add(r"^sshd2?\(pam_unix\): session (?P<what>opened|closed)", "Logins & sessions", "An SSH login session {what}",
     "The PAM authentication framework recorded that a user's SSH session {what}.", "message text + standard PAM behaviour")
_add(r"^sshd2?: Accepted (?P<how>\S+) for (?P<user>\S+) from", "Logins & sessions", "Successful SSH login ({how})",
     "User '{user}' logged in over SSH using {how} authentication ('publickey' means a cryptographic key, no password typed). The source IP and port follow in the line.", "message text")
_add(r"^sshd2?: .*authentication cancelled by user", "Logins & sessions", "An SSH login attempt was cancelled before finishing",
     "The log says the authentication step ended as 'cancelled by user', i.e. the connecting side gave up before logging in.", _TXT)
_add(r"^sshd2?: .*(?:connection lost|Local disconnected|Remote host disconnected)", "Logins & sessions", "An SSH connection ended",
     "Records which side closed the connection and the stated reason (the quoted text).", _TXT)
_add(r"^sshd2?: connection from", "Logins & sessions", "A host connected to the SSH server",
     "One line per incoming SSH connection, before login completes. The source host name is anonymized in this dataset.", _TXT)
_add(r"^sshd2?: Now running on", "Logins & sessions", "An SSH session started under a user's privileges",
     "sshd2 reports it is now running with the privileges of the (anonymized) user who just logged in.", _TXT)
_add(r"^sshd2?: User .*authenticated", "Logins & sessions", "A user authenticated over SSH",
     "The line names the user (anonymized) and the machine they came from.", _TXT)
_add(r"^kernel: scsi" + NUM + r" \(" + NUM + ":" + NUM + r"\): rejecting I/O to offline device", "Storage & filesystems",
     "A SCSI disk was offline, so a read/write was rejected",
     "The kernel tried to do I/O on a SCSI device marked offline and refused. The numbers identify the controller and target. This is the kind of line the dataset tags as SCSI (hardware type in the source paper).", _PAPER)
_add(r"EXT(?:3|<N>)-fs error.*Journal has aborted", "Storage & filesystems", "An ext3 filesystem's journal aborted",
     "ext3 is the Linux filesystem on a disk partition (the device name, e.g. sda5, is in the message). The journal is its crash-safety log; 'aborted' means it stopped working after an error. Lines like this are what the dataset tags as EXT_FS.", "message text + your alert data")
_add(r"ext(?:3|<N>)_journal_start_sb: Detected aborted journal", "Storage & filesystems", "An ext3 filesystem reported an already-aborted journal",
     "The filesystem tried to start a journal transaction but found the journal had already aborted. A follow-on of the error above.", "message text + your alert data")
_add(r"^kernel: EXT(?:3|<N>)-fs", "Storage & filesystems", "ext3 filesystem message",
     "A message from the ext3 filesystem driver; the affected device is named in the line.", "message text")
_add(r"mptscsih: ioc" + NUM + ": attempting task abort", "Storage & filesystems", "The disk-controller driver is aborting a stuck SCSI command",
     "mptscsih is the driver for MPT (Fusion-MPT) SCSI adapters. 'Task abort' means a command did not complete in time and the driver is cancelling it. The dataset tags these as MPT.", _PAPER)
_add(r"^kernel: Losing some ticks", "Kernel (general)", "The kernel missed some clock ticks",
     "The kernel lost timer interrupts ('ticks') and is checking whether the CPU's clock frequency changed. The dataset tags these as CPU (software type in the source paper).", _PAPER)
_add(r"Uhhuh\. NMI received", "Hardware health", "A non-maskable interrupt (NMI) hit a node",
     "An NMI is a hardware signal the CPU cannot ignore; Linux prints this when one arrives, often because of a hardware fault or watchdog. The dataset tags these as NMI; the source paper lists only 8 of them and calls the cause indeterminate.", "general Linux knowledge + source paper")
_add(r"^pbs_mom: .*Connection refused", "Job scheduler (PBS)", "The PBS node agent's connection was refused",
     "pbs_mom tried to connect somewhere and was refused ('111' is the Linux error code for connection refused: nothing accepting connections on that port, or a firewall rejecting it). The dataset tags these as PBS_CON.", _PAPER)
_add(r"^pbs_mom: .*Bad file descriptor", "Job scheduler (PBS)", "The PBS node agent hit an invalid file/socket handle",
     "It happened while handling a task-manager request (tm_request) for a job the agent says is not running. Lines like this are what the dataset tags as PBS_BFD.", "message text + your alert data")
_add(r"Server Administrator", "Hardware health", "Hardware monitor report (Server Administrator)",
     "Server Administrator is the server vendor's hardware-monitoring agent. According to the source paper, the dataset's ECC alerts (critical memory errors) are reports of this kind; not every such line is an alert, so check the Alerts count.", _PAPER)
_add(r"^RT: ", "Other services", "RT application debug message",
     "Printed by a program called RT whose file paths include /opt/rt3/. The word 'scrips' is Request Tracker terminology, so this is most likely the Request Tracker ticket system. Inferred, not documented in the dataset.", "inferred from file paths and wording")

_KEYWORDS = [
    (re.compile(r"infiniband|\bib_|vapi|topspin|mthca", re.I), "InfiniBand network"),
    (re.compile(r"scsi|\bext(?:3|<N>)|\bnfs|journal|filesystem|\bsd[a-z]", re.I), "Storage & filesystems"),
    (re.compile(r"\bpbs|torque", re.I), "Job scheduler (PBS)"),
    (re.compile(r"ssh|login|authenticat|pam_|\bsudo\b|\bsu\b", re.I), "Logins & sessions"),
    (re.compile(r"\bcron|anacron", re.I), "Scheduled jobs"),
    (re.compile(r"\bntp", re.I), "Time sync"),
    (re.compile(r"dhcp|\bdns\b|named|eth(?:\d+|<N>)|link (?:up|down)", re.I), "Network services"),
    (re.compile(r"\becc\b|machine check|\bmce\b|\bnmi\b|temperature|power supply", re.I), "Hardware health"),
]
_PROBLEM = re.compile(r"\b(error|errors|fail|failed|failure|refused|timed out|timeout|abort|aborted|denied|critical|panic|offline|corrupt\w*|fatal)\b", re.I)


class _Safe(dict):
    def __missing__(self, k):
        return "{" + k + "}"


def explain(template):
    template = template or ""
    prog = template.split(": ", 1)[0] if ": " in template else template
    base = re.split(r"[(\[]", prog)[0]
    pinfo = PROGRAMS.get(base) or PROGRAMS.get(base.lower())
    out = {"program": prog, "readable": readable(template), "variables": variables_in(template),
           "problem_wording": bool(_PROBLEM.search(template))}
    if pinfo:
        out.update(program_name=pinfo[0], program_desc=pinfo[1])
    elif prog == "(none)":
        out.update(program_name="(no program name)",
                   program_desc="The line had no 'program:' prefix, so only the message text is available.")
    else:
        out.update(program_name=prog, program_desc="This program is not in the glossary yet.")
    for rx, cat, head, det, basis in _RULES:
        m = rx.search(template)
        if m:
            g = _Safe({k: (v or "") for k, v in m.groupdict().items()})
            out.update(level="specific", category=cat, headline=head.format_map(g),
                       detail=det.format_map(g), basis=basis)
            return out
    kw = next((c for rx, c in _KEYWORDS if rx.search(template)), None)
    if pinfo and not (base == "kernel" and kw):
        out.update(level="program", category=pinfo[2], headline=pinfo[0] + " message",
                   detail=pinfo[1] + " No message-specific explanation has been written for this exact pattern; read the plain-English template below.",
                   basis=pinfo[3])
    elif kw:
        out.update(level="keyword", category=kw, headline=out["program_name"] + " message (category guessed from keywords)",
                   detail="No verified description exists for this pattern. The category was guessed from words in the message, so treat it as a hint and read the plain-English template below.",
                   basis="keyword match (unverified)")
    else:
        out.update(level="none", category="Unclassified", headline="Message from '" + prog + "' (not explained yet)",
                   detail="This program is not in the glossary and no rule matches. Read the plain-English template below.",
                   basis="n/a")
    return out


# ---- alert labels (first column of the raw log) ----
TYPE_NAMES = {"H": "Hardware", "S": "Software", "I": "Indeterminate (cause unclear)"}
LABEL_SOURCE = ("Oliner & Stearley, 'What Supercomputers Say' (DSN 2007), and Oliner's Stanford PhD thesis, "
                "which has the per-category table for Thunderbird.")
ALERT_LABELS = {
    "VAPI": {"type": "I", "title": "InfiniBand driver errors",
             "summary": "VAPI is Mellanox's low-level programming interface ('verbs API') for InfiniBand, the high-speed network between the nodes. These alerts are kernel messages from the InfiniBand driver stack, described by the authors as 'Local Catastrophic Errors'.",
             "paper": "The paper reports 3,229,194 of them and says the exact nature of many was not well understood by its experts. One single node produced 643,925 of them (their filtering reduces those to 246), and their table places the VAPI alerts in only 276 node-hours. That is why VAPI is 99.4% of all alerts."},
    "ECC": {"type": "H", "title": "Critical memory (ECC) errors",
            "summary": "Memory errors serious enough to be reported as critical (not routine single-bit corrections), reported by the server's hardware-monitoring agent, 'Server Administrator'.",
            "paper": "The paper lists 146 alerts in 143 node-hours and says they behave like independent random hardware failures."},
    "NMI": {"type": "I", "title": "Non-maskable interrupts",
            "summary": "The kernel printed 'Uhhuh. NMI received': the CPU got a hardware signal it cannot ignore, often a hardware fault or watchdog.",
            "paper": "The paper lists only 8 alerts in 4 node-hours and classes the cause as indeterminate."},
    "PBS_CON": {"type": "S", "title": "PBS connection refused",
                "summary": "The PBS node agent (pbs_mom) reported 'Connection refused (111)' when talking to another service.",
                "paper": "The paper lists 5,318 alerts in just 16 node-hours, which means they come in bursts of thousands."},
    "MPT": {"type": "I", "title": "MPT SCSI driver task aborts",
            "summary": "The MPT (Fusion-MPT) SCSI driver reported 'attempting task abort': a disk command did not finish and the driver is cancelling it.",
            "paper": "The paper lists 4,583 alerts in 157 node-hours."},
    "CPU": {"type": "S", "title": "Missed clock ticks",
            "summary": "The kernel reported 'Losing some ticks... checking if CPU frequency changed': timer interrupts were missed.",
            "paper": "The paper lists 2,741 alerts in 367 node-hours."},
    "SCSI": {"type": "H", "title": "SCSI device offline",
             "summary": "The kernel rejected I/O to a SCSI device that was offline.",
             "paper": "The paper lists 2,186 alerts in 317 node-hours."},
    "EXT_FS": {"type": None, "title": "ext3 filesystem errors",
               "summary": "Errors from the ext3 filesystem on node disks, for example an aborted journal. Based on the labelled lines in this dataset (see the examples below).",
               "paper": "Alert type (H/S/I) not verified from the sources I could access."},
    "PBS_BFD": {"type": None, "title": "PBS 'Bad file descriptor'",
                "summary": "The PBS node agent hit a bad file descriptor while handling a task-manager request for a job it said was not running. Based on the labelled lines in this dataset.",
                "paper": "Alert type (H/S/I) not verified from the sources I could access."},
    "CHK_DSK": {"type": None, "title": "Disk-check related",
                "summary": "No verified description found. Read the real examples below, which come straight from the data.",
                "paper": "Alert type (H/S/I) not verified from the sources I could access."},
}
