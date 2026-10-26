# glossary_data.py
# Plain-English meanings for the Thunderbird log analytics project.
#
# "source" tells the reader how much to trust each entry:
#   SRC_MSG : the meaning is stated in the message text itself
#   SRC_GEN : message text + standard Linux / networking / hardware knowledge
#   SRC_INF : our reading of the message; verify before quoting as fact
#   SRC_PAPER_VAPI : category type taken from Oliner's thesis (Stanford), meaning from message text

SRC_MSG = "message text"
SRC_GEN = "message text + general technical knowledge"
SRC_INF = "inferred from the message - verify before citing"
SRC_PAPER_VAPI = "Oliner thesis (category type) + message text"

# --------------------------------------------------------------------------------------
# 1. ALERT LABELS (first column of the raw log; '-' = not an alert)
# --------------------------------------------------------------------------------------
LABELS = {
    "VAPI": dict(
        short="InfiniBand driver error",
        plain=("A fault reported by the cluster's high-speed network driver (InfiniBand). "
               "Almost every alert in the dataset (99.4%) is this single message repeating, "
               "so the alert count mostly measures how often this one condition was logged, "
               "not millions of different problems."),
        type="Indeterminate (in Oliner's study: may come from hardware, software, or an unknown cause)",
        note=("InfiniBand is the fast interconnect that links the cluster's compute nodes. "
              "The message names the Topspin driver and a Tavor-family adapter. "
              "Open Alert Explorer and filter by VAPI to read the full text."),
        source=SRC_PAPER_VAPI),
    "PBS_CON": dict(
        short="Job daemon connection refused",
        plain=("pbs_mom, the per-node daemon of the PBS job scheduler, tried to open a connection "
               "to another machine and was refused ('Connection refused', error 111)."),
        type=None, note=None, source=SRC_GEN),
    "MPT": dict(
        short="Disk controller abort",
        plain=("The Linux driver for the node's SCSI/SAS disk controller (mptscsih, controller ioc0) "
               "is aborting a disk command that did not complete - typically a sign the disk or "
               "controller was not responding."),
        type=None, note=None, source=SRC_GEN),
    "EXT_FS": dict(
        short="Filesystem error (ext3)",
        plain=("The kernel found an error in an ext3 filesystem on a local disk, for example "
               "'Journal has aborted'. When this happens the filesystem is normally switched to "
               "read-only to protect the data."),
        type=None, note=None, source=SRC_GEN),
    "CPU": dict(
        short="Lost timer ticks",
        plain=("Despite the name, the message is a timing warning, not a report of a failed processor: "
               "the kernel noticed it had missed some clock ticks and is checking whether the "
               "CPU's clock speed changed."),
        type=None, note=None, source=SRC_GEN),
    "SCSI": dict(
        short="Disk offline",
        plain=("The kernel refused to send I/O to a SCSI disk because the disk is marked offline "
               "(it stopped responding or was taken out of service)."),
        type=None, note=None, source=SRC_GEN),
    "ECC": dict(
        short="Memory module critical",
        plain=("Dell's server-management software (Server Administrator) reported a memory module "
               "(DIMM) in critical status. ECC stands for Error-Correcting Code, the memory feature "
               "that detects and corrects bit errors."),
        type=None,
        note="Event 1404, 'Memory device status is critical'; the message gives the DIMM slot (e.g. DIMM1_B).",
        source=SRC_GEN),
    "PBS_BFD": dict(
        short="Job daemon bad file descriptor",
        plain=("pbs_mom hit a 'Bad file descriptor' error while handling a task request "
               "for a job that was no longer running."),
        type=None, note=None, source=SRC_GEN),
    "CHK_DSK": dict(
        short="Drive array fault",
        plain=("A disk-check script on an admin node logged a hardware 'Fault Status' on a drive-array "
               "slot (once with its clearing, a 'deassertion event')."),
        type=None,
        note="The format resembles a hardware event log entry; that origin is our inference.",
        source=SRC_INF),
    "NMI": dict(
        short="Unexpected hardware interrupt",
        plain=("The kernel received a Non-Maskable Interrupt (NMI) - a high-priority hardware signal, "
               "often tied to hardware faults - that it did not expect, logged 'Dazed and confused' "
               "and carried on."),
        type=None, note=None, source=SRC_GEN),
}

# --------------------------------------------------------------------------------------
# 2. PROGRAMS (the word before the colon in a log line)
# --------------------------------------------------------------------------------------
PROGRAMS = {
    "kernel": dict(plain="The Linux operating-system core. Hardware, driver and filesystem messages come from here (38% of all lines and almost every alert).", source=SRC_GEN),
    "sshd": dict(plain="SSH server: handles remote logins and authentication.", source=SRC_GEN),
    "sshd(pam_unix)": dict(plain="SSH login sessions as recorded by the PAM authentication module.", source=SRC_GEN),
    "sshd2": dict(plain="SSH2 server daemon (a separate SSH implementation from OpenSSH's sshd).", source=SRC_GEN),
    "xinetd": dict(plain="'Super-server' that starts network services (here mostly rsync) on demand and enforces connection limits.", source=SRC_GEN),
    "crond": dict(plain="Cron: runs scheduled jobs.", source=SRC_GEN),
    "crond(pam_unix)": dict(plain="Login sessions opened and closed for each scheduled (cron) job.", source=SRC_GEN),
    "anacron": dict(plain="Runs periodic jobs that were missed while a machine was off.", source=SRC_GEN),
    "ib_sm": dict(plain="InfiniBand subnet manager: discovers and configures the InfiniBand network fabric.", source=SRC_GEN),
    "ib_sm.x": dict(plain="Executable form of the InfiniBand subnet manager (same role as ib_sm).", source=SRC_INF),
    "ntpd": dict(plain="Network Time Protocol daemon: keeps the node's clock synchronised.", source=SRC_GEN),
    "ntpdate": dict(plain="One-shot clock synchronisation against a time server.", source=SRC_GEN),
    "postfix": dict(plain="Postfix mail system (messages from its sub-programs appear as postfix/...).", source=SRC_GEN),
    "postfix/postdrop": dict(plain="Postfix component that places locally submitted mail into the mail queue.", source=SRC_GEN),
    "postfix/master": dict(plain="Postfix master process that starts and supervises the other Postfix programs.", source=SRC_GEN),
    "postfix/qmgr": dict(plain="Postfix queue manager: decides when queued mail is delivered.", source=SRC_GEN),
    "postfix/smtp": dict(plain="Postfix component that delivers mail to other servers over SMTP.", source=SRC_GEN),
    "sendmail": dict(plain="Sendmail mail transfer agent: accepts and delivers email.", source=SRC_GEN),
    "snmpd": dict(plain="SNMP agent: answers monitoring queries and receives event notifications (traps).", source=SRC_GEN),
    "sysctl": dict(plain="Applies kernel settings, normally at boot.", source=SRC_GEN),
    "dhcpd": dict(plain="DHCP server: hands out IP addresses to machines on the network.", source=SRC_GEN),
    "smartd": dict(plain="Disk health monitor using SMART data (reports disk temperature and errors).", source=SRC_GEN),
    "/apps/x86_64/system/ganglia-3.0.1/sbin/gmetad": dict(plain="Ganglia gmetad: collects and aggregates cluster-monitoring metrics from the nodes.", source=SRC_GEN),
    "/usr/sbin/gmetad": dict(plain="Ganglia gmetad: collects and aggregates cluster-monitoring metrics from the nodes.", source=SRC_GEN),
    "gmond": dict(plain="Ganglia gmond: runs on each node and reports its metrics (CPU, memory, load).", source=SRC_GEN),
    "rc.sysinit": dict(plain="Boot-time system initialisation script.", source=SRC_GEN),
    "rc": dict(plain="Script that starts or stops system services at boot/shutdown.", source=SRC_GEN),
    "fsck": dict(plain="Filesystem check tool, run at boot or on demand.", source=SRC_GEN),
    "mount": dict(plain="Mounts filesystems.", source=SRC_GEN),
    "mount.panfs": dict(plain="Mounts a 'panfs' filesystem. The name suggests the Panasas parallel filesystem.", source=SRC_INF),
    "smokeping": dict(plain="Network latency monitoring tool.", source=SRC_GEN),
    "network": dict(plain="Boot script that brings network interfaces up and down.", source=SRC_GEN),
    "netfs": dict(plain="Boot script that mounts network filesystems.", source=SRC_GEN),
    "syslog": dict(plain="System logging daemon.", source=SRC_GEN),
    "syslog-ng": dict(plain="Syslog-ng: system logging daemon that collects and forwards log messages.", source=SRC_GEN),
    "haldaemon": dict(plain="Hardware abstraction layer daemon: detects hardware changes.", source=SRC_GEN),
    "messagebus": dict(plain="D-Bus system message bus used by system services to talk to each other.", source=SRC_GEN),
    "nfslock": dict(plain="NFS file-locking service.", source=SRC_GEN),
    "rpc.statd": dict(plain="NFS status monitor, used for lock recovery.", source=SRC_GEN),
    "portmap": dict(plain="RPC port mapper: tells clients which port an RPC service listens on.", source=SRC_GEN),
    "acpid": dict(plain="Handles power-management events (ACPI).", source=SRC_GEN),
    "init": dict(plain="The first process started at boot; manages system run levels.", source=SRC_GEN),
    "su": dict(plain="'Switch user' command: logs when someone becomes another user.", source=SRC_GEN),
    "sudo": dict(plain="Runs a command with another user's (usually root's) privileges and logs it.", source=SRC_GEN),
    "logger": dict(plain="Command that writes a message into the system log (used by scripts).", source=SRC_GEN),
    "in.tftpd": dict(plain="TFTP server, typically used for network booting.", source=SRC_GEN),
    "lvm.static": dict(plain="Logical Volume Manager tool.", source=SRC_GEN),
    "udevsend": dict(plain="Device-manager helper that reacts to hardware being added or removed.", source=SRC_GEN),
    "VFS": dict(plain="Messages from the kernel's virtual filesystem layer.", source=SRC_GEN),
    "pbs_mom": dict(plain="Per-node daemon of the PBS job scheduler: starts and monitors jobs on its node.", source=SRC_GEN),
    "PBS_Server": dict(plain="Main server of the PBS job scheduler: queues jobs and assigns them to nodes.", source=SRC_GEN),
    "check-disks": dict(plain="Disk-check script that reports drive faults.", source=SRC_INF),
    "dataeng": dict(plain="Appears to be a Dell OpenManage Server Administrator service (hardware monitoring).", source=SRC_INF),
    "instsvcdrv": dict(plain="Appears to be a Dell OpenManage Server Administrator driver service.", source=SRC_INF),
    "omsad": dict(plain="Appears to be the Dell OpenManage Server Administrator agent.", source=SRC_INF),
    "(none)": dict(plain="Lines where the parser found no 'program:' prefix. Many are Dell Server Administrator hardware-monitoring messages.", source=SRC_MSG),
    "(empty)": dict(plain="Log lines that have a header (time, node) but no message text.", source=SRC_MSG),
    "MDT": dict(plain="Not a program: 'MDT' is Mountain Daylight Time. These are network-switch messages whose timestamp the parser read as a program name.", source=SRC_INF),
    "time.c": dict(plain="Not a program: 'time.c' is a kernel source file. These are kernel timekeeping messages the parser read as a program name.", source=SRC_INF),
}

# --------------------------------------------------------------------------------------
# 3. TEMPLATE RULES - first matching rule wins, so specific rules come before general ones.
#    Patterns are Python regexes searched against the template string, which looks like
#    "program: message with <N>/<IP>/<HEX> placeholders".
# --------------------------------------------------------------------------------------
def R(pattern, title, plain, category, source=SRC_GEN):
    return dict(pattern=pattern, title=title, plain=plain, category=category, source=source)

IB = "Interconnect (InfiniBand)"
ST = "Storage / filesystem"
HW = "Hardware monitoring"
AUTH = "Remote access & authentication"
SCH = "Job scheduling (PBS)"
TIME = "Time / clock"
MAIL = "Mail"
SYS = "Routine system activity"
NET = "Network devices"
BOOT = "Boot / hardware initialisation"

TEMPLATE_RULES = [
    # ---- the alert categories, specific messages first ------------------------------
    R(r"^kernel: \[KERNEL_IB\]\[tsIbTavorMadProcess\]",
      "InfiniBand driver error (the VAPI alert)",
      "Error logged by the InfiniBand driver while processing a management message (MAD) on a "
      "Tavor-family network adapter. This one message is 3.23 million of the 3.25 million alerts in "
      "the dataset. The full text is visible in Alert Explorer.", IB, SRC_PAPER_VAPI),
    R(r"^kernel: \[KERNEL_IB\]\[_tsIbTavorInitOne\]",
      "InfiniBand adapter initialisation error (rare VAPI alert)",
      "Error from the InfiniBand driver while initialising a network adapter (only 31 alerts).", IB, SRC_GEN),
    R(r"^kernel: mptscsih: ioc<N>: attempting task abort",
      "Disk controller aborting a stuck command (MPT alert)",
      "The SCSI/SAS controller driver is aborting a disk command that did not finish.", ST),
    R(r"^kernel: EXT<N>-fs error \(device sda<N>\) in start_transaction: Journal has aborted",
      "ext3 journal aborted (EXT_FS alert)",
      "The ext3 filesystem's journal (its crash-recovery log) aborted on disk partition sda. "
      "The filesystem normally goes read-only afterwards.", ST),
    R(r"^kernel: EXT<N>-fs error \(device sda<N>\): ext<N>_free_blocks: Freeing blocks not in datazone",
      "ext3 freeing blocks outside the data area (EXT_FS alert)",
      "The filesystem tried to free disk blocks outside its data area, a sign of corrupted "
      "filesystem metadata.", ST),
    R(r"^kernel: EXT<N>-fs error \(device sda<N>\): ext<N>_journal_start_sb: Detected aborted journal",
      "ext3 operation attempted on an aborted journal (EXT_FS alert)",
      "The filesystem refused an operation because its journal had already aborted.", ST),
    R(r"^kernel: EXT<N>-fs error",
      "ext3 filesystem error (EXT_FS alert)",
      "The kernel reported an error inside an ext3 filesystem on a local disk.", ST),
    R(r"^kernel: Losing some ticks",
      "Kernel lost timer ticks (the 'CPU' alert)",
      "A timing warning: the kernel missed clock ticks and is checking whether the CPU frequency changed. "
      "It is not a report of a failed processor.", TIME),
    R(r"^kernel: scsi<N> \(<N>:<N>\): rejecting I/O to offline device",
      "Disk offline, I/O rejected (SCSI alert)",
      "The kernel is refusing to send reads/writes to a SCSI disk that is marked offline.", ST),
    R(r"^\(none\): Server Administrator: Instrumentation Service EventID: <N> Memory device status is critical",
      "Memory module (DIMM) critical (ECC alert)",
      "Dell Server Administrator reports a memory module in critical status; the message names the "
      "DIMM slot.", HW),
    R(r"^pbs_mom: Connection refused \(<N>\) in open_demux",
      "Job daemon could not connect (PBS_CON alert)",
      "pbs_mom failed to open a connection to another machine and port (error 111, connection refused).", SCH),
    R(r"^pbs_mom: Bad file descriptor \(<N>\) in tm_request",
      "Job daemon bad file descriptor (PBS_BFD alert)",
      "pbs_mom hit a 'Bad file descriptor' error handling a task request for a job that was no longer "
      "running.", SCH),
    R(r"^check-disks: .*Fault Status assert",
      "Drive array fault status (CHK_DSK alert)",
      "A disk-check script logged a fault status on a drive-array slot (and, once, its clearing).", HW, SRC_INF),
    R(r"^kernel: Uhhuh\. NMI received",
      "Unexpected non-maskable interrupt (NMI alert)",
      "The kernel received a hardware interrupt it did not expect, logged 'Dazed and confused' "
      "and continued.", HW),
    R(r"^\(empty\)$",
      "Header only, no message",
      "A log line with a time and node but no message text.", SYS, SRC_MSG),

    # ---- InfiniBand driver family (mostly NOT labelled as alerts) -------------------
    R(r"^kernel: \[KERNEL_IB\]\[ib_mad_dispatch\]",
      "InfiniBand management-message dispatch",
      "Message from the InfiniBand driver's management-datagram (MAD) dispatcher. Not labelled an alert "
      "in this dataset.", IB),
    R(r"^kernel: \[KERNEL_IB\]",
      "InfiniBand kernel driver message",
      "Message from the InfiniBand kernel driver; the bracketed names are the driver function and source file.", IB),
    R(r"^kernel: VIPKL\(<N>\): \[MM_create_mr\]:MM_mr_get_keys failed",
      "InfiniBand driver: memory-region setup failed",
      "The InfiniBand driver failed to obtain keys for a registered memory region "
      "(MM_create_mr / MM_mr_get_keys). About 3.6 million occurrences; not labelled an alert.", IB),
    R(r"^kernel: THH\(<N>\): XHH_mrwm_register_mr: rc=HH_EAGAIN",
      "InfiniBand driver: memory registration returned 'try again'",
      "Registering memory with the InfiniBand adapter returned HH_EAGAIN (temporarily unavailable, retry).", IB),
    R(r"^kernel: (THH|MOSAL|VIPKL)\(<N>\)",
      "InfiniBand driver diagnostic output",
      "Debug-style lines from the InfiniBand driver stack (modules THH, MOSAL, VIPKL; the file paths point "
      "to Topspin/Mellanox driver source). Several consecutive lines often dump internal state around one error.",
      IB, SRC_INF),
    R(r"^ib_sm(\.x)?: \[ib_sm_discovery\.c:<N>\]: Failed to GetNodeInfo\(\) because of NO RESPONSE",
      "InfiniBand manager: device did not answer",
      "The subnet manager asked a device in the InfiniBand fabric for its information (GetNodeInfo) and got "
      "no response, so it could not reach that device during its sweep.", IB),
    R(r"^ib_sm(\.x)?: \[ib_sm_discovery\.c:<N>\]: Failed to GetNodeInfo\(\) - hop_count",
      "InfiniBand manager: device query failed (with path)",
      "The same GetNodeInfo failure, printed with the number of hops and the port path that was tried.", IB),
    R(r"^ib_sm(\.x)?: \[ib_sm_discovery\.c:<N>\]: Failed discover node test",
      "InfiniBand manager: node discovery test failed",
      "The subnet manager's discovery test failed for a node and port (the message gives the error code).", IB),
    R(r"^ib_sm(\.x)?: \[ib_sm_sweep\.c:<N>\]: \*+ NEW SWEEP",
      "InfiniBand manager: new fabric sweep",
      "Marks the start of the subnet manager's periodic scan of the InfiniBand network.", IB),
    R(r"^ib_sm(\.x)?: \[ib_sm_sweep\.c:<N>\]: No topology change",
      "InfiniBand manager: no change found",
      "A sweep finished and found no change in the InfiniBand network layout.", IB),
    R(r"^ib_sm(\.x)?: ",
      "InfiniBand subnet manager message",
      "Message from the InfiniBand subnet manager.", IB),

    # ---- storage ----------------------------------------------------------------------
    R(r"^kernel: pan_ips: error -- ",
      "Storage client: command timed out",
      "Commands sent to the storage system timed out and were aborted or cleaned up (the text says "
      "'IPS: command timed out'). The 'pan' name suggests Panasas storage.", ST, SRC_INF),
    R(r"^smartd: Device: /dev/sd[a-z], Temperature changed",
      "Disk temperature report",
      "The SMART disk monitor reports that a disk's temperature changed since its last report (degrees Celsius).", HW),
    R(r"^postfix/postdrop: warning: mail_queue_enter: create file maildrop/.*Read-only file system",
      "Mail could not be queued: filesystem is read-only",
      "Local mail submission failed because the filesystem holding the mail queue was read-only. "
      "At 10.5 million lines (5% of the whole log) this is the single most frequent message in the dataset.",
      ST),

    # ---- hardware monitoring ---------------------------------------------------------
    R(r"^\(none\): Server Administrator: Instrumentation Service EventID: <N> Temperature sensor returned to a normal value",
      "Temperature sensor back to normal",
      "Dell Server Administrator reports that the ambient-temperature sensor on the node's management "
      "controller returned to a normal value. It appears 2.41 million times, almost as often as the "
      "matching warning (2.40 million), which suggests a sensor repeatedly crossing its threshold "
      "(an observation from the counts, not a confirmed cause).", HW),
    R(r"^\(none\): Server Administrator: Instrumentation Service EventID: <N> Temperature sensor detected a warning value",
      "Temperature sensor warning",
      "Dell Server Administrator reports that the ambient-temperature sensor detected a warning value. "
      "See the matching 'back to normal' message.", HW),
    R(r"^\(none\): Server Administrator:",
      "Dell Server Administrator hardware event",
      "Event from Dell's server hardware-monitoring software.", HW),

    # ---- time ------------------------------------------------------------------------
    R(r"^ntpd: synchronized to",
      "Clock synchronised to a time server",
      "The node's clock is synchronised to a time server. 'Stratum' is the number of hops from the "
      "reference clock (lower is closer).", TIME),
    R(r"^time\.c: Lost <N> timer tick",
      "Kernel lost timer ticks (not labelled an alert)",
      "The kernel noticed it had lost timer ticks (missed clock interrupts). 2.4 million lines, not labelled "
      "an alert. The parser read the source-file name 'time.c' as the program.", TIME),

    # ---- boot / hardware init --------------------------------------------------------
    R(r"^kernel: ACPI: PCI interrupt",
      "Hardware initialisation: PCI interrupt routed",
      "A kernel line printed while hardware is set up (a PCI device's interrupt line was assigned).", BOOT),
    R(r"^kernel: ACPI: LAPIC_NMI",
      "Boot-time CPU interrupt setup (not an NMI event)",
      "An ACPI table entry describing a CPU's NMI input, printed at boot. Informational: it is not the "
      "NMI alert, which is a different message.", BOOT),

    # ---- network devices -------------------------------------------------------------
    R(r"^MDT: %RPM<N>-P:CP %IFMGR-<N>-OSTATE_DN",
      "Network switch port went down",
      "A network switch reported an interface changing state to down (e.g. 'Gi 8/89' = GigabitEthernet "
      "slot 8, port 89). The parser read the leading 'MDT' (Mountain Daylight Time) as a program name.",
      NET, SRC_INF),
    R(r"^MDT: %RPM<N>-P:CP %IFMGR-<N>-OSTATE_UP",
      "Network switch port came up",
      "A network switch reported an interface changing state to up. The parser read 'MDT' "
      "(Mountain Daylight Time) as a program name.", NET, SRC_INF),
    R(r"^snmpd: Got trap from peer",
      "Monitoring notification received",
      "The SNMP daemon received a trap, an event notification sent by a monitored device.", NET),

    # ---- remote access ---------------------------------------------------------------
    R(r"^sshd: Accepted publickey",
      "Successful SSH login (public key)",
      "Someone or something logged in over SSH using a public key (here as root, from an address inside "
      "the cluster).", AUTH),
    R(r"^sshd\(pam_unix\): session opened",
      "SSH login session opened", "A login session was opened for an SSH connection.", AUTH),
    R(r"^sshd: connection from",
      "SSH connection received",
      "The SSH server accepted a network connection (the client name is anonymised in the dataset).", AUTH),
    R(r"^sshd: (Local disconnected|connection lost)",
      "SSH connection closed", "An SSH connection ended normally ('Connection closed').", AUTH),
    R(r"^sshd: (Remote host disconnected|authentication cancelled)",
      "SSH client gave up during login",
      "The client closed the connection before authentication finished ('Authentication cancelled by user').", AUTH),
    R(r"^sshd2: Now running on",
      "SSH session running as a user",
      "The SSH2 server switched to the logged-in user's privileges (user name anonymised).", AUTH),
    R(r"^sshd: User .*authenticated",
      "SSH user authenticated",
      "A user, coming from a cluster node, passed SSH authentication (names anonymised).", AUTH),

    # ---- routine services -------------------------------------------------------------
    R(r"^xinetd: START: rsync",
      "rsync transfer service started",
      "xinetd started an rsync service for a client at the given IP address - one line per connection "
      "(7.75 million).", SYS),
    R(r"^xinetd: FAIL: rsync service_limit",
      "rsync connection refused: too many at once",
      "xinetd refused a new rsync connection because the service's limit on simultaneous instances "
      "was reached.", SYS),
    R(r"^crond\(pam_unix\): session opened",
      "Scheduled job started", "Cron started a scheduled job as root; each job logs an 'opened' and a 'closed' line.", SYS),
    R(r"^crond\(pam_unix\): session closed",
      "Scheduled job finished", "The login session for a scheduled (cron) job as root ended.", SYS),
    R(r"^crond: \(root\) CMD \(run-parts /etc/cron\.hourly\)",
      "Hourly maintenance jobs run",
      "Cron started the hourly maintenance scripts (run-parts executes every script in /etc/cron.hourly).", SYS),
    R(r"^crond: \(.*\) CMD",
      "Scheduled command run", "Cron ran a scheduled command.", SYS),
]


# ======================================================================================
# ROUND 2: additions based on the user's own coverage report and gap report
# ======================================================================================
PROGRAMS.update({
    "RT": dict(plain="Appears to be the Request Tracker (RT) ticketing system, with an asset-tracking extension (the file paths mention RTx/AssetTracker).", source=SRC_INF),
    "port_mgr.x": dict(plain="Appears to be InfiniBand switch management software that reports port up/down events and configuration changes.", source=SRC_INF),
    "cli.x": dict(plain="Appears to be the command-line interface of InfiniBand switch software; it logs administrators' configuration commands.", source=SRC_INF),
    "irqbalance": dict(plain="Service that spreads hardware interrupts across CPUs.", source=SRC_GEN),
    "start_udev": dict(plain="Boot script that starts udev, the device manager.", source=SRC_GEN),
    "date": dict(plain="The 'date' command, normally run by scripts (exact purpose in these lines not verified).", source=SRC_INF),
    "shutdown": dict(plain="The shutdown command: a node is being halted or rebooted.", source=SRC_MSG),
    "postfix/postfix-script": dict(plain="Script that starts and stops the Postfix mail system.", source=SRC_GEN),
    "ts_fixup": dict(plain="Helper for the Topspin InfiniBand driver that creates its device entries under /dev.", source=SRC_INF),
    "fstab-sync": dict(plain="Boot-time helper that manages auto-generated mount points.", source=SRC_GEN),
    "rpcidmapd": dict(plain="NFS identity-mapping service (translates user names between machines).", source=SRC_GEN),
    "userhelper": dict(plain="Red Hat helper that lets ordinary users run certain privileged programs.", source=SRC_GEN),
    "postfix/cleanup": dict(plain="Postfix component that processes incoming mail before it is queued.", source=SRC_GEN),
    "modprobe": dict(plain="Loads kernel modules (drivers).", source=SRC_GEN),
    "CROND": dict(plain="The cron daemon (upper-case variant of crond): runs scheduled jobs.", source=SRC_GEN),
})

TEMPLATE_RULES += [
    # ---- syslog artefact -------------------------------------------------------------
    R(r"^\(none\): last message repeated <N> times",
      "Syslog collapsed repeated messages",
      "The logging system replaced several identical messages with one 'last message repeated N times' line. "
      "So the number of lines is lower than the number of real events.", SYS, SRC_GEN),

    # ---- InfiniBand / Lustre / storage -----------------------------------------------
    R(r"^kernel: time\.c: Lost <N> timer tick",
      "Kernel lost timer ticks (not labelled an alert)",
      "The kernel noticed it had lost timer ticks (missed clock interrupts). Not labelled an alert, "
      "unlike the 'Losing some ticks' message of the CPU alert.", TIME),
    R(r"^kernel: LustreError: .*ksocknal_lib_connect_sock\(\)\) Error -<N> connecting",
      "Lustre filesystem: network connection failed",
      "The Lustre parallel filesystem's network layer failed to connect to another node (the error code "
      "and both addresses are in the message).", ST),
    R(r"^kernel: LustreError:",
      "Lustre filesystem error", "Error reported by the Lustre parallel filesystem client or server.", ST),
    R(r"^port_mgr\.x: \[INFO\]: port (up|down)",
      "InfiniBand switch port went up or down",
      "A switch-management process reported an InfiniBand port changing state (port = slot/port).", IB, SRC_INF),
    R(r"^port_mgr\.x: \[CONF\]",
      "InfiniBand switch port configuration change",
      "An administrator command configured an InfiniBand port ('shutdown' or 'no shutdown').", IB, SRC_INF),
    R(r"^cli\.x: \[CONF\]",
      "InfiniBand switch configuration command",
      "A configuration command typed into the switch command line, e.g. saving the running config to startup.", IB, SRC_INF),
    R(r"^ts_fixup: ",
      "Topspin InfiniBand driver helper",
      "A helper that creates the Topspin InfiniBand device entries.", IB, SRC_INF),
    R(r"^kernel: (kjournald starting|EXT<N>-fs: mounted filesystem|EXT<N> FS on )",
      "ext3 filesystem mounted",
      "Lines the kernel prints when an ext3 filesystem is mounted and its journal starts (normal at boot).", ST),

    # ---- Ganglia / DHCP / services ----------------------------------------------------
    R(r"^(/apps/x86_64/system/ganglia-3\.0\.1/sbin/gmetad|/usr/sbin/gmetad): data_thread\(\) got not answer from any",
      "Monitoring server got no answer from a cluster",
      "Ganglia's gmetad could not get data from any source of a monitored cluster (the cluster name is in "
      "the message). Repeats every polling cycle.", SYS),
    R(r"^dhcpd: DHCPDISCOVER from <MAC> via eth<N>: network .*: no free leases",
      "DHCP server had no free addresses",
      "A machine asked the DHCP server for an address, but none were free on that network "
      "(network name in the message).", NET),
    R(r"^dhcpd: DHCPREQUEST for .* unknown lease",
      "DHCP request for an unknown lease",
      "A machine asked to renew an address the DHCP server has no record of.", NET),
    R(r"^dhcpd: DHCP(DISCOVER|OFFER|REQUEST|ACK)",
      "DHCP address negotiation",
      "Normal steps of a machine obtaining an IP address from the DHCP server.", NET),
    R(r"^ntpd: can't open /var/lib/ntp/drift",
      "Time service could not save its drift file",
      "ntpd failed to write its clock-drift file because of a permissions error.", TIME),
    R(r"^anacron: Updated timestamp for job",
      "Periodic job timestamp updated", "anacron recorded that a periodic job (e.g. cron.daily) ran.", SYS),
    R(r"^sysctl: ",
      "Kernel setting applied",
      "A kernel parameter was set (typically at boot); the setting and value are in the message.", BOOT),
    R(r"^RT: ",
      "Ticketing system activity",
      "Messages from what appears to be the Request Tracker ticketing system ('scrips' are its rule-based actions).",
      SYS, SRC_INF),
    R(r"^irqbalance: ", "Interrupt-balancing service started", "The irqbalance service started.", BOOT),
    R(r"^start_udev: ", "Device manager (udev) started", "Boot script started udev.", BOOT),
    R(r"^fstab-sync: ", "Mount-point cleanup at boot", "Auto-generated mount points were removed.", BOOT),
    R(r"^rpcidmapd: ", "NFS identity-mapping service started", "The NFS id-mapping service started.", BOOT),
    R(r"^shutdown: shutting down for system halt",
      "Node shutting down", "A node is being halted.", SYS, SRC_MSG),
    R(r"^postfix/postfix-script: ", "Mail system started or stopped", "The Postfix start/stop script ran.", MAIL),
    R(r"^modprobe: modprobe: Can't locate module",
      "Kernel module not found",
      "The system tried to load a kernel module that is not installed (its name is in the message).", BOOT),

    # ---- kernel boot-time hardware detection (families) -------------------------------
    R(r"^kernel: BIOS-e<N>:",
      "Boot: BIOS memory map entry",
      "A line from the memory map the firmware hands to the kernel at boot (usable or reserved ranges).", BOOT),
    R(r"^kernel: ACPI: ",
      "Boot: ACPI hardware description",
      "The kernel reading hardware descriptions (interrupts, CPUs) from the firmware, mostly at boot.", BOOT),
    R(r"^kernel: IOAPIC\[",
      "Boot: interrupt controller setup", "The kernel configuring an I/O interrupt controller at boot.", BOOT),
    R(r"^kernel: (hub <N>-|uhci_hcd |usb |usbcore)",
      "Boot: USB controller and hub detection", "The kernel detecting USB controllers and hubs.", BOOT),
    R(r"^kernel: PCI: ", "Boot: PCI device setup", "The kernel configuring a PCI device.", BOOT),
    R(r"^kernel: CPU: ", "Boot: CPU feature and cache report", "The kernel reporting CPU features and cache sizes.", BOOT),
    R(r"^kernel: Probing IDE interface", "Boot: IDE interface probe", "The kernel probing for IDE disk interfaces.", BOOT),
    R(r"^kernel: NET: Registered protocol family",
      "Boot: network protocol registered", "A network protocol was registered with the kernel.", BOOT),
    R(r"^kernel: ip_tables:",
      "Boot: firewall module loaded", "The kernel's packet-filter (iptables) module loaded.", BOOT),
    R(r"^kernel: cpu <N> (hot|cold): low",
      "Kernel memory statistics dump",
      "Per-CPU memory page-list statistics, printed as part of a memory report (seen together with "
      "memory-pressure messages).", BOOT, SRC_INF),
]
