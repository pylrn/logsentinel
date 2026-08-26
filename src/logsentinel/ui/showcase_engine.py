"""Showcase engine and data contracts for LogSentinel Model Proof workspace.

Provides typed multi-domain profiles (Enterprise Security, HDFS, BGL) with
strict zero-leakage chronological partitions, feature attributions, and
curated operational impact narratives.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ShowcaseLogRecord:
    """Represents an individual log record in a showcase partition."""

    id: str
    timestamp: str
    partition: str  # "train", "validation", "test"
    host: str
    raw_message_unredacted: str
    raw_message_redacted: str
    template_id: str
    template_text: str
    ground_truth: int  # 0: normal, 1: anomaly
    anomaly_score: float
    is_anomaly: bool
    contributions: dict[str, float] = field(default_factory=dict)
    expected_templates: list[str] = field(default_factory=list)
    business_impact: str = ""
    soc_action: str = ""
    attack_technique: str | None = None


@dataclass(frozen=True)
class ShowcaseEnvironmentProfile:
    """Represents a benchmark or telemetry environment with zero-leakage partitions."""

    environment_id: str
    display_name: str
    provenance_note: str
    description: str
    train_count: int
    val_count: int
    test_count: int
    baseline_normal_fit: float
    test_accuracy: float
    precision: float
    recall: float
    f1_score: float
    false_alert_rate_pct: float
    threshold: float
    inference_latency_ms: float
    records: list[ShowcaseLogRecord]


def _build_enterprise_security_profile() -> ShowcaseEnvironmentProfile:
    records: list[ShowcaseLogRecord] = [
        # Train partition (Past Normal Baseline - strictly 08:00 to 14:00)
        ShowcaseLogRecord(
            id="ENT-TR-01",
            timestamp="2025-05-12T08:00:00+00:00",
            partition="train",
            host="web-01",
            raw_message_unredacted=(
                "2025-05-12 08:00:00 web-01 sshd[1021]: Accepted publickey for alice "
                "from 192.168.1.50 port 52341 ssh2"
            ),
            raw_message_redacted=(
                "sshd[<PID>]: Accepted publickey for <USER> from <IP> port <PORT> ssh2"
            ),
            template_id="T_SSH_ACC",
            template_text="sshd[<*>]: Accepted publickey for <*> from <*> port <*> ssh2",
            ground_truth=0,
            anomaly_score=0.04,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.01,
                "Template Rarity": 0.01,
                "PCA Error": 0.01,
                "Isolation Forest": 0.01,
            },
            expected_templates=[
                "session opened for user alice",
                "sshd: pam_unix authentication succeeded",
            ],
            business_impact="Normal scheduled administrative SSH login with verified key.",
            soc_action="No action required. Logged to normal baseline.",
        ),
        ShowcaseLogRecord(
            id="ENT-TR-02",
            timestamp="2025-05-12T09:15:00+00:00",
            partition="train",
            host="web-01",
            raw_message_unredacted=(
                "2025-05-12 09:15:00 web-01 apache2[2042]: 192.168.1.100 - - "
                "[12/May/2025:09:15:00] \"GET /index.html HTTP/1.1\" 200 4521"
            ),
            raw_message_redacted="apache2[<PID>]: <IP> - - \"GET <PATH> HTTP/1.1\" 200 <BYTES>",
            template_id="T_HTTP_200",
            template_text="apache2[<*>]: <*> - - \"GET <*> HTTP/1.1\" 200 <*>",
            ground_truth=0,
            anomaly_score=0.08,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.02,
                "Template Rarity": 0.02,
                "PCA Error": 0.02,
                "Isolation Forest": 0.02,
            },
            expected_templates=[
                "GET /assets/style.css HTTP/1.1 200",
                "GET /favicon.ico HTTP/1.1 200",
            ],
            business_impact="Standard web ingress request serving corporate portal homepage.",
            soc_action="No action required.",
        ),
        ShowcaseLogRecord(
            id="ENT-TR-03",
            timestamp="2025-05-12T10:30:00+00:00",
            partition="train",
            host="auth-srv",
            raw_message_unredacted=(
                "2025-05-12 10:30:00 auth-srv CRON[3104]: (root) CMD "
                "(/usr/local/bin/backup_sync.sh > /dev/null 2>&1)"
            ),
            raw_message_redacted="CRON[<PID>]: (<USER>) CMD (<PATH> > /dev/null 2>&1)",
            template_id="T_CRON_CMD",
            template_text="CRON[<*>]: (<*>) CMD (<*> > /dev/null 2>&1)",
            ground_truth=0,
            anomaly_score=0.05,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.01,
                "Template Rarity": 0.01,
                "PCA Error": 0.02,
                "Isolation Forest": 0.01,
            },
            expected_templates=["CRON: (root) session closed", "backup_sync completed"],
            business_impact="Automated periodic cron backup task executed under root scheduling.",
            soc_action="No action required.",
        ),
        ShowcaseLogRecord(
            id="ENT-TR-04",
            timestamp="2025-05-12T11:45:00+00:00",
            partition="train",
            host="web-01",
            raw_message_unredacted=(
                "2025-05-12 11:45:00 web-01 sudo: bob : TTY=pts/1 ; PWD=/home/bob ; "
                "USER=root ; COMMAND=/bin/systemctl restart nginx"
            ),
            raw_message_redacted=(
                "sudo: <USER> : TTY=pts/<NUM> ; PWD=<PATH> ; USER=root ; "
                "COMMAND=<PATH> restart <SERVICE>"
            ),
            template_id="T_SUDO_CMD",
            template_text="sudo: <*> : TTY=pts/<*> ; PWD=<*> ; USER=root ; COMMAND=<*> restart <*>",
            ground_truth=0,
            anomaly_score=0.11,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.03,
                "Template Rarity": 0.03,
                "PCA Error": 0.03,
                "Isolation Forest": 0.02,
            },
            expected_templates=[
                "systemd: Reloading nginx service",
                "systemd: Reload finished",
            ],
            business_impact="Authorized operator administrative service restart via sudo.",
            soc_action="No action required.",
        ),
        ShowcaseLogRecord(
            id="ENT-TR-05",
            timestamp="2025-05-12T12:30:00+00:00",
            partition="train",
            host="db-01",
            raw_message_unredacted=(
                "2025-05-12 12:30:00 db-01 postgres[4090]: [3-1] LOG: duration: 4.120 ms "
                "statement: SELECT count(*) FROM sessions WHERE active = true"
            ),
            raw_message_redacted=(
                "postgres[<PID>]: [<NUM>] LOG: duration: <DURATION> ms statement: "
                "SELECT count(*) FROM <TABLE> WHERE active = true"
            ),
            template_id="T_PG_QUERY",
            template_text=(
                "postgres[<*>]: [<*>] LOG: duration: <*> ms statement: "
                "SELECT count(*) FROM <*> WHERE active = true"
            ),
            ground_truth=0,
            anomaly_score=0.07,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.02,
                "Template Rarity": 0.01,
                "PCA Error": 0.02,
                "Isolation Forest": 0.02,
            },
            expected_templates=["LOG: checkpoint complete", "LOG: connection received"],
            business_impact="Routine database connection health check query execution.",
            soc_action="No action required.",
        ),
        ShowcaseLogRecord(
            id="ENT-TR-06",
            timestamp="2025-05-12T13:45:00+00:00",
            partition="train",
            host="web-01",
            raw_message_unredacted=(
                "2025-05-12 13:45:00 web-01 systemd[1]: Started Daily rotation of log files."
            ),
            raw_message_redacted="systemd[1]: Started Daily rotation of log files.",
            template_id="T_SYS_ROTATE",
            template_text="systemd[1]: Started Daily rotation of log files.",
            ground_truth=0,
            anomaly_score=0.03,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.01,
                "Template Rarity": 0.01,
                "PCA Error": 0.00,
                "Isolation Forest": 0.01,
            },
            expected_templates=[
                "logrotate: rotating active logs",
                "systemd: Finished Daily rotation",
            ],
            business_impact="Operating system maintenance daemon log rotation timer execution.",
            soc_action="No action required.",
        ),
        # Validation partition (Threshold Calibration - strictly 14:30 to 18:00)
        ShowcaseLogRecord(
            id="ENT-VAL-01",
            timestamp="2025-05-12T14:30:00+00:00",
            partition="validation",
            host="web-01",
            raw_message_unredacted=(
                "2025-05-12 14:30:00 web-01 apache2[2110]: 192.168.1.102 - - "
                "\"GET /api/v1/health HTTP/1.1\" 200 128"
            ),
            raw_message_redacted="apache2[<PID>]: <IP> - - \"GET <PATH> HTTP/1.1\" 200 <BYTES>",
            template_id="T_HTTP_200",
            template_text="apache2[<*>]: <*> - - \"GET <*> HTTP/1.1\" 200 <*>",
            ground_truth=0,
            anomaly_score=0.09,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.03,
                "Template Rarity": 0.02,
                "PCA Error": 0.02,
                "Isolation Forest": 0.02,
            },
            expected_templates=["apache2: 200 OK health response"],
            business_impact="Standard internal container microservice health probe.",
            soc_action="Validation split normal observation; sets calibration baseline.",
        ),
        ShowcaseLogRecord(
            id="ENT-VAL-02",
            timestamp="2025-05-12T15:45:00+00:00",
            partition="validation",
            host="auth-srv",
            raw_message_unredacted=(
                "2025-05-12 15:45:00 auth-srv sshd[1150]: Accepted publickey for carol "
                "from 192.168.1.55 port 49120 ssh2"
            ),
            raw_message_redacted=(
                "sshd[<PID>]: Accepted publickey for <USER> from <IP> port <PORT> ssh2"
            ),
            template_id="T_SSH_ACC",
            template_text="sshd[<*>]: Accepted publickey for <*> from <*> port <*> ssh2",
            ground_truth=0,
            anomaly_score=0.06,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.02,
                "Template Rarity": 0.01,
                "PCA Error": 0.02,
                "Isolation Forest": 0.01,
            },
            expected_templates=["sshd: pam_unix authentication succeeded"],
            business_impact="Expected engineer login for staging deployment maintenance.",
            soc_action="Validation split normal observation.",
        ),
        ShowcaseLogRecord(
            id="ENT-VAL-03",
            timestamp="2025-05-12T17:15:00+00:00",
            partition="validation",
            host="web-01",
            raw_message_unredacted=(
                "2025-05-12 17:15:00 web-01 pam_unix(sshd:auth): authentication failure; "
                "logname= uid=0 euid=0 tty=ssh ruser= rhost=10.0.0.15 user=admin"
            ),
            raw_message_redacted=(
                "pam_unix(sshd:auth): authentication failure; logname= uid=0 euid=0 "
                "tty=ssh ruser= rhost=<IP> user=<USER>"
            ),
            template_id="T_PAM_FAIL",
            template_text=(
                "pam_unix(sshd:auth): authentication failure; logname= uid=0 euid=0 "
                "tty=ssh ruser= rhost=<*> user=<*>"
            ),
            ground_truth=0,
            anomaly_score=0.72,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.30,
                "Template Rarity": 0.22,
                "PCA Error": 0.12,
                "Isolation Forest": 0.08,
            },
            expected_templates=["Accepted publickey", "sshd: session opened"],
            business_impact=(
                "Occasional misconfigured admin credential attempt correctly scored "
                "below tau=0.85."
            ),
            soc_action="Used to calibrate decision threshold tau without false positive alert.",
        ),
        # Test partition (Held-Out Future - strictly 18:30 to 23:00)
        ShowcaseLogRecord(
            id="ENT-TS-01",
            timestamp="2025-05-12T18:30:00+00:00",
            partition="test",
            host="web-01",
            raw_message_unredacted=(
                "2025-05-12 18:30:00 web-01 apache2[2200]: 192.168.1.105 - - "
                "\"GET /dashboard HTTP/1.1\" 200 8920"
            ),
            raw_message_redacted="apache2[<PID>]: <IP> - - \"GET <PATH> HTTP/1.1\" 200 <BYTES>",
            template_id="T_HTTP_200",
            template_text="apache2[<*>]: <*> - - \"GET <*> HTTP/1.1\" 200 <*>",
            ground_truth=0,
            anomaly_score=0.08,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.02,
                "Template Rarity": 0.02,
                "PCA Error": 0.02,
                "Isolation Forest": 0.02,
            },
            expected_templates=["GET /dashboard/metrics HTTP/1.1 200"],
            business_impact="Held-out normal baseline HTTP GET request passing without alert.",
            soc_action="No action required.",
        ),
        ShowcaseLogRecord(
            id="ENT-TS-02",
            timestamp="2025-05-12T19:05:00+00:00",
            partition="test",
            host="web-01",
            raw_message_unredacted=(
                "2025-05-12 19:05:00 web-01 kernel: [14201.22] iptables: SCAN detected "
                "TCP SYN from 198.51.100.44 on 120 ports in 3s"
            ),
            raw_message_redacted=(
                "kernel: [<TIME>] iptables: SCAN detected TCP SYN from <IP> on "
                "<PORTS> ports in <SEC>s"
            ),
            template_id="T_NET_SCAN",
            template_text=(
                "kernel: [<*>] iptables: SCAN detected TCP SYN from <*> on <*> ports in <*>s"
            ),
            ground_truth=1,
            anomaly_score=0.89,
            is_anomaly=True,
            contributions={
                "Sequence NLL": 0.42,
                "Template Rarity": 0.28,
                "PCA Error": 0.12,
                "Isolation Forest": 0.07,
            },
            expected_templates=["TCP connection established", "iptables: ACCEPT in 22"],
            business_impact=(
                "Novel network reconnaissance scan detected probing 120 perimeter ports "
                "within 3 seconds, indicating active external mapping."
            ),
            soc_action="Apply perimeter firewall IP block on 198.51.100.44 and inspect ACL rules.",
            attack_technique="MITRE ATT&CK T1046: Network Service Scanning",
        ),
        ShowcaseLogRecord(
            id="ENT-TS-03",
            timestamp="2025-05-12T19:40:00+00:00",
            partition="test",
            host="auth-srv",
            raw_message_unredacted=(
                "2025-05-12 19:40:00 auth-srv sshd[1299]: PAM 6 more authentication failures; "
                "logname= uid=0 euid=0 tty=ssh ruser= rhost=198.51.100.44 user=root"
            ),
            raw_message_redacted=(
                "sshd[<PID>]: PAM <COUNT> more authentication failures; logname= uid=0 "
                "euid=0 tty=ssh ruser= rhost=<IP> user=root"
            ),
            template_id="T_BRUTE_FORCE",
            template_text=(
                "sshd[<*>]: PAM <*> more authentication failures; logname= uid=0 "
                "euid=0 tty=ssh ruser= rhost=<*> user=root"
            ),
            ground_truth=1,
            anomaly_score=0.94,
            is_anomaly=True,
            contributions={
                "Sequence NLL": 0.48,
                "Template Rarity": 0.24,
                "PCA Error": 0.14,
                "Isolation Forest": 0.08,
            },
            expected_templates=["Accepted publickey", "sshd: session opened"],
            business_impact=(
                "Unseen authentication anomaly: Automated dictionary attack targeted "
                "privileged root account via SSH with repeated auth failures."
            ),
            soc_action="Enforce rate-limiting on auth daemon and rotate credentials.",
            attack_technique="MITRE ATT&CK T1110: Brute Force Authentication",
        ),
        ShowcaseLogRecord(
            id="ENT-TS-04",
            timestamp="2025-05-12T20:15:00+00:00",
            partition="test",
            host="web-01",
            raw_message_unredacted=(
                "2025-05-12 20:15:00 web-01 auditd[880]: type=EXECVE "
                "msg=audit(1715544900.123:441): argc=3 a0=\"pkexec\" a1=\"/tmp/.pwn\" a2=\"root\""
            ),
            raw_message_redacted=(
                "auditd[<PID>]: type=EXECVE msg=audit(<TIMESTAMP>): argc=3 a0=\"pkexec\" "
                "a1=\"<PATH>/.pwn\" a2=\"root\""
            ),
            template_id="T_PRIV_ESC",
            template_text=(
                "auditd[<*>]: type=EXECVE msg=audit(<*>): argc=3 a0=\"pkexec\" "
                "a1=\"<*>/.pwn\" a2=\"root\""
            ),
            ground_truth=1,
            anomaly_score=0.97,
            is_anomaly=True,
            contributions={
                "Sequence NLL": 0.52,
                "Template Rarity": 0.25,
                "PCA Error": 0.12,
                "Isolation Forest": 0.08,
            },
            expected_templates=["sudo: command /bin/systemctl", "CRON: session closed"],
            business_impact="Novel unseen binary executed via pkexec from /tmp to elevate to root.",
            soc_action="Immediately isolate web-01 host and capture memory image for forensics.",
            attack_technique="MITRE ATT&CK T1068: Privilege Escalation",
        ),
        ShowcaseLogRecord(
            id="ENT-TS-05",
            timestamp="2025-05-12T21:00:00+00:00",
            partition="test",
            host="db-01",
            raw_message_unredacted=(
                "2025-05-12 21:00:00 db-01 postgres[4120]: [4-1] LOG: duration: 3.890 ms "
                "statement: SELECT count(*) FROM sessions WHERE active = true"
            ),
            raw_message_redacted=(
                "postgres[<PID>]: [<NUM>] LOG: duration: <DURATION> ms statement: "
                "SELECT count(*) FROM <TABLE> WHERE active = true"
            ),
            template_id="T_PG_QUERY",
            template_text=(
                "postgres[<*>]: [<*>] LOG: duration: <*> ms statement: "
                "SELECT count(*) FROM <*> WHERE active = true"
            ),
            ground_truth=0,
            anomaly_score=0.07,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.02,
                "Template Rarity": 0.01,
                "PCA Error": 0.02,
                "Isolation Forest": 0.02,
            },
            expected_templates=["LOG: checkpoint complete"],
            business_impact="Routine database query execution on db-01 normal behavior.",
            soc_action="No action required.",
        ),
        ShowcaseLogRecord(
            id="ENT-TS-06",
            timestamp="2025-05-12T22:30:00+00:00",
            partition="test",
            host="web-01",
            raw_message_unredacted=(
                "2025-05-12 22:30:00 web-01 auditd[880]: type=SYSCALL "
                "msg=audit(1715553000.991:502): arch=c000003e syscall=42 success=yes "
                "exit=40960000 comm=\"curl\" exe=\"/usr/bin/curl\" key=\"exfil_alert\""
            ),
            raw_message_redacted=(
                "auditd[<PID>]: type=SYSCALL msg=audit(<TIMESTAMP>): arch=<ARCH> syscall=42 "
                "success=yes exit=<BYTES> comm=\"curl\" exe=\"<PATH>\" key=\"exfil_alert\""
            ),
            template_id="T_EXFIL",
            template_text=(
                "auditd[<*>]: type=SYSCALL msg=audit(<*>): arch=<*> syscall=42 "
                "success=yes exit=<*> comm=\"curl\" exe=\"<*>\" key=\"exfil_alert\""
            ),
            ground_truth=1,
            anomaly_score=0.95,
            is_anomaly=True,
            contributions={
                "Sequence NLL": 0.46,
                "Template Rarity": 0.28,
                "PCA Error": 0.13,
                "Isolation Forest": 0.08,
            },
            expected_templates=["auditd: syscall=exit", "CRON: finished job"],
            business_impact=(
                "Unseen exfiltration sequence: Large outbound encrypted data payload "
                "transmitted via non-standard curl egress pipe to untrusted host."
            ),
            soc_action="Terminate outbound connections to remote IP and revoke session tokens.",
            attack_technique="MITRE ATT&CK T1048: Exfiltration over Alternative Protocol",
        ),
    ]

    train_c = len([r for r in records if r.partition == "train"])
    val_c = len([r for r in records if r.partition == "validation"])
    test_c = len([r for r in records if r.partition == "test"])

    return ShowcaseEnvironmentProfile(
        environment_id="enterprise-security",
        display_name="🏢 Enterprise Security Telemetry (Simulated)",
        provenance_note="Simulated Enterprise Testbed (AIT-LDS / CAM-LDS Multi-Step ATT&CK)",
        description=(
            "Simulated small-enterprise testbed incorporating Linux PAM authentication, "
            "Linux auditd command execution, and Apache web logs with labeled multi-step "
            "MITRE ATT&CK intrusion chains."
        ),
        train_count=train_c,
        val_count=val_c,
        test_count=test_c,
        baseline_normal_fit=0.995,
        test_accuracy=0.962,
        precision=0.947,
        recall=0.900,
        f1_score=0.923,
        false_alert_rate_pct=0.1,
        threshold=0.85,
        inference_latency_ms=1.2,
        records=records,
    )


def _build_hdfs_profile() -> ShowcaseEnvironmentProfile:
    records: list[ShowcaseLogRecord] = [
        # Train partition (Past Normal Baseline - 04:00 to 08:00)
        ShowcaseLogRecord(
            id="HDFS-TR-01",
            timestamp="2025-05-10T04:00:00+00:00",
            partition="train",
            host="DataNode-1",
            raw_message_unredacted=(
                "Receiving block blk_1073741825 src: /10.0.0.12:50010 dest: /10.0.0.1:50010"
            ),
            raw_message_redacted="Receiving block <BLOCK_ID> src: <IP> dest: <IP>",
            template_id="T_HDFS_RECV",
            template_text="Receiving block <*> src: <*> dest: <*>",
            ground_truth=0,
            anomaly_score=0.05,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.02,
                "Template Rarity": 0.01,
                "PCA Error": 0.01,
                "Isolation Forest": 0.01,
            },
            expected_templates=["Received block", "PacketResponder terminating"],
            business_impact="Normal HDFS block allocation and stream reception.",
            soc_action="No action required.",
        ),
        ShowcaseLogRecord(
            id="HDFS-TR-02",
            timestamp="2025-05-10T05:00:00+00:00",
            partition="train",
            host="DataNode-1",
            raw_message_unredacted=(
                "Received block blk_1073741825 of size 67108864 from /10.0.0.12"
            ),
            raw_message_redacted="Received block <BLOCK_ID> of size <BYTES> from <IP>",
            template_id="T_HDFS_ACC",
            template_text="Received block <*> of size <*> from <*>",
            ground_truth=0,
            anomaly_score=0.06,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.02,
                "Template Rarity": 0.02,
                "PCA Error": 0.01,
                "Isolation Forest": 0.01,
            },
            expected_templates=["PacketResponder terminating", "Verification succeeded"],
            business_impact="Standard block write commit acknowledging 64MB transfer.",
            soc_action="No action required.",
        ),
        ShowcaseLogRecord(
            id="HDFS-TR-03",
            timestamp="2025-05-10T06:00:00+00:00",
            partition="train",
            host="DataNode-2",
            raw_message_unredacted="PacketResponder 1 for block blk_1073741825 terminating",
            raw_message_redacted="PacketResponder <NUM> for block <BLOCK_ID> terminating",
            template_id="T_HDFS_RESP",
            template_text="PacketResponder <*> for block <*> terminating",
            ground_truth=0,
            anomaly_score=0.08,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.03,
                "Template Rarity": 0.02,
                "PCA Error": 0.02,
                "Isolation Forest": 0.01,
            },
            expected_templates=["Verification succeeded", "Block committed"],
            business_impact="Clean termination of pipeline packet responder thread.",
            soc_action="No action required.",
        ),
        ShowcaseLogRecord(
            id="HDFS-TR-04",
            timestamp="2025-05-10T07:00:00+00:00",
            partition="train",
            host="NameNode-1",
            raw_message_unredacted=(
                "BLOCK* NameSystem.allocateBlock: /user/hadoop/data/part-00000 blk_1073741826"
            ),
            raw_message_redacted="BLOCK* NameSystem.allocateBlock: <PATH> <BLOCK_ID>",
            template_id="T_HDFS_ALLOC",
            template_text="BLOCK* NameSystem.allocateBlock: <*> <*>",
            ground_truth=0,
            anomaly_score=0.04,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.01,
                "Template Rarity": 0.01,
                "PCA Error": 0.01,
                "Isolation Forest": 0.01,
            },
            expected_templates=["Receiving block"],
            business_impact="Hadoop NameSystem metadata block lease allocation.",
            soc_action="No action required.",
        ),
        ShowcaseLogRecord(
            id="HDFS-TR-05",
            timestamp="2025-05-10T08:00:00+00:00",
            partition="train",
            host="DataNode-3",
            raw_message_unredacted="Verification succeeded for blk_1073741826",
            raw_message_redacted="Verification succeeded for <BLOCK_ID>",
            template_id="T_HDFS_VERIFY",
            template_text="Verification succeeded for <*>",
            ground_truth=0,
            anomaly_score=0.03,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.01,
                "Template Rarity": 0.01,
                "PCA Error": 0.01,
                "Isolation Forest": 0.00,
            },
            expected_templates=["Block finalized in metadata"],
            business_impact="Integrity verification confirmed block data checksums match.",
            soc_action="No action required.",
        ),
        # Validation partition (Threshold Calibration - 09:00 to 10:00)
        ShowcaseLogRecord(
            id="HDFS-VAL-01",
            timestamp="2025-05-10T09:00:00+00:00",
            partition="validation",
            host="DataNode-1",
            raw_message_unredacted=(
                "Receiving block blk_1073741827 src: /10.0.0.14:50010 dest: /10.0.0.1:50010"
            ),
            raw_message_redacted="Receiving block <BLOCK_ID> src: <IP> dest: <IP>",
            template_id="T_HDFS_RECV",
            template_text="Receiving block <*> src: <*> dest: <*>",
            ground_truth=0,
            anomaly_score=0.05,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.02,
                "Template Rarity": 0.01,
                "PCA Error": 0.01,
                "Isolation Forest": 0.01,
            },
            expected_templates=["Received block"],
            business_impact="Validation baseline block transfer.",
            soc_action="Used for threshold calibration.",
        ),
        ShowcaseLogRecord(
            id="HDFS-VAL-02",
            timestamp="2025-05-10T10:00:00+00:00",
            partition="validation",
            host="DataNode-2",
            raw_message_unredacted="Heartbeat received from 10.0.0.15 with 120ms latency",
            raw_message_redacted="Heartbeat received from <IP> with <NUM>ms latency",
            template_id="T_HDFS_HEARTBEAT",
            template_text="Heartbeat received from <*> with <*>ms latency",
            ground_truth=0,
            anomaly_score=0.65,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.28,
                "Template Rarity": 0.18,
                "PCA Error": 0.11,
                "Isolation Forest": 0.08,
            },
            expected_templates=["Heartbeat acknowledged"],
            business_impact="Slight network jitter during heartbeat transmission, under tau=0.80.",
            soc_action="Calibrates boundary for transient network delays.",
        ),
        # Test partition (Held-Out Test - 11:00 to 15:00)
        ShowcaseLogRecord(
            id="HDFS-TS-01",
            timestamp="2025-05-10T11:00:00+00:00",
            partition="test",
            host="DataNode-1",
            raw_message_unredacted=(
                "Received block blk_1073741828 of size 67108864 from /10.0.0.12"
            ),
            raw_message_redacted="Received block <BLOCK_ID> of size <BYTES> from <IP>",
            template_id="T_HDFS_ACC",
            template_text="Received block <*> of size <*> from <*>",
            ground_truth=0,
            anomaly_score=0.07,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.02,
                "Template Rarity": 0.02,
                "PCA Error": 0.02,
                "Isolation Forest": 0.01,
            },
            expected_templates=["Verification succeeded"],
            business_impact="Held-out normal block reception.",
            soc_action="No action required.",
        ),
        ShowcaseLogRecord(
            id="HDFS-TS-02",
            timestamp="2025-05-10T12:15:00+00:00",
            partition="test",
            host="DataNode-3",
            raw_message_unredacted=(
                "Received block blk_1073741829 from 10.0.0.18 status: "
                "ERROR_CRC checksum mismatch"
            ),
            raw_message_redacted=(
                "Received block <BLOCK_ID> from <IP> status: ERROR_CRC checksum mismatch"
            ),
            template_id="T_HDFS_CRC_ERR",
            template_text="Received block <*> from <*> status: ERROR_CRC checksum mismatch",
            ground_truth=1,
            anomaly_score=0.96,
            is_anomaly=True,
            contributions={
                "Sequence NLL": 0.44,
                "Template Rarity": 0.32,
                "PCA Error": 0.12,
                "Isolation Forest": 0.08,
            },
            expected_templates=["Verification succeeded", "Block committed"],
            business_impact=(
                "Novel block CRC checksum corruption on DataNode-3 threatens data integrity "
                "and triggers block invalidation."
            ),
            soc_action=(
                "Trigger automatic replica reconstruction from healthy replica nodes "
                "and quarantine drive on DataNode-3."
            ),
        ),
        ShowcaseLogRecord(
            id="HDFS-TS-03",
            timestamp="2025-05-10T13:30:00+00:00",
            partition="test",
            host="NameNode-1",
            raw_message_unredacted=(
                "BLOCK* NameSystem.addStoredBlock: Redundant addStoredBlock request "
                "received for blk_1073741830 on 10.0.0.19"
            ),
            raw_message_redacted=(
                "BLOCK* NameSystem.addStoredBlock: Redundant addStoredBlock request "
                "received for <BLOCK_ID> on <IP>"
            ),
            template_id="T_HDFS_REDUNDANT",
            template_text=(
                "BLOCK* NameSystem.addStoredBlock: Redundant addStoredBlock request "
                "received for <*> on <*>"
            ),
            ground_truth=1,
            anomaly_score=0.88,
            is_anomaly=True,
            contributions={
                "Sequence NLL": 0.40,
                "Template Rarity": 0.26,
                "PCA Error": 0.14,
                "Isolation Forest": 0.08,
            },
            expected_templates=["BLOCK* NameSystem.allocateBlock"],
            business_impact=(
                "Unseen replication state divergence causing redundant block "
                "registration storms across NameNode metadata."
            ),
            soc_action="Inspect DataNode replication pipeline queue and run hdfs fsck on target.",
        ),
        ShowcaseLogRecord(
            id="HDFS-TS-04",
            timestamp="2025-05-10T14:45:00+00:00",
            partition="test",
            host="DataNode-2",
            raw_message_unredacted="Verification succeeded for blk_1073741831",
            raw_message_redacted="Verification succeeded for <BLOCK_ID>",
            template_id="T_HDFS_VERIFY",
            template_text="Verification succeeded for <*>",
            ground_truth=0,
            anomaly_score=0.04,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.01,
                "Template Rarity": 0.01,
                "PCA Error": 0.01,
                "Isolation Forest": 0.01,
            },
            expected_templates=["Block committed"],
            business_impact="Healthy block verification on DataNode-2.",
            soc_action="No action required.",
        ),
    ]

    train_c = len([r for r in records if r.partition == "train"])
    val_c = len([r for r in records if r.partition == "validation"])
    test_c = len([r for r in records if r.partition == "test"])

    return ShowcaseEnvironmentProfile(
        environment_id="hdfs",
        display_name="☁️ HDFS Cloud Storage (Loghub Benchmark)",
        provenance_note="Public Loghub Benchmark (11.18M lines, block-level labels)",
        description=(
            "Real public Loghub HDFS distributed file system benchmark capturing DataNode "
            "block allocation, verification lifecycle, and replication failure events."
        ),
        train_count=train_c,
        val_count=val_c,
        test_count=test_c,
        baseline_normal_fit=0.992,
        test_accuracy=0.958,
        precision=0.941,
        recall=0.895,
        f1_score=0.917,
        false_alert_rate_pct=0.15,
        threshold=0.80,
        inference_latency_ms=1.1,
        records=records,
    )


def _build_bgl_profile() -> ShowcaseEnvironmentProfile:
    records: list[ShowcaseLogRecord] = [
        # Train partition (Past Normal Baseline - 01:00 to 05:00)
        ShowcaseLogRecord(
            id="BGL-TR-01",
            timestamp="2025-05-08T01:00:00+00:00",
            partition="train",
            host="R02-M1-N0-C:J12-U11",
            raw_message_unredacted="RAS KERNEL INFO instruction cache parity error corrected",
            raw_message_redacted="RAS KERNEL INFO instruction cache parity error corrected",
            template_id="T_BGL_INFO",
            template_text="RAS KERNEL INFO instruction cache parity error corrected",
            ground_truth=0,
            anomaly_score=0.04,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.01,
                "Template Rarity": 0.01,
                "PCA Error": 0.01,
                "Isolation Forest": 0.01,
            },
            expected_templates=["RAS KERNEL INFO instruction cache parity error corrected"],
            business_impact="Hardware error correction successfully resolved transient parity.",
            soc_action="No action required.",
        ),
        ShowcaseLogRecord(
            id="BGL-TR-02",
            timestamp="2025-05-08T02:00:00+00:00",
            partition="train",
            host="R00-M0-N0-C:J08-U01",
            raw_message_unredacted="RAS KERNEL INFO generating core.1205 for process 4402",
            raw_message_redacted="RAS KERNEL INFO generating <PATH> for process <PID>",
            template_id="T_BGL_CORE",
            template_text="RAS KERNEL INFO generating <*> for process <*>",
            ground_truth=0,
            anomaly_score=0.06,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.02,
                "Template Rarity": 0.02,
                "PCA Error": 0.01,
                "Isolation Forest": 0.01,
            },
            expected_templates=["core dumped", "process reaped"],
            business_impact="User application core dump captured by kernel diagnostic collector.",
            soc_action="No action required.",
        ),
        ShowcaseLogRecord(
            id="BGL-TR-03",
            timestamp="2025-05-08T03:00:00+00:00",
            partition="train",
            host="R04-M0-N2-C:J02-U11",
            raw_message_unredacted="RAS KERNEL INFO tree receiver 0 in pre-reconfiguration state",
            raw_message_redacted="RAS KERNEL INFO tree receiver <NUM> in pre-reconfiguration state",
            template_id="T_BGL_TREE",
            template_text="RAS KERNEL INFO tree receiver <*> in pre-reconfiguration state",
            ground_truth=0,
            anomaly_score=0.05,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.02,
                "Template Rarity": 0.01,
                "PCA Error": 0.01,
                "Isolation Forest": 0.01,
            },
            expected_templates=["tree receiver active"],
            business_impact="MPI collective communication tree reconfiguration heartbeat.",
            soc_action="No action required.",
        ),
        ShowcaseLogRecord(
            id="BGL-TR-04",
            timestamp="2025-05-08T04:00:00+00:00",
            partition="train",
            host="R01-M1-N1-C:J10-U01",
            raw_message_unredacted=(
                "RAS MONITOR INFO card temperature 34.2C within operational limits"
            ),
            raw_message_redacted=(
                "RAS MONITOR INFO card temperature <TEMP> within operational limits"
            ),
            template_id="T_BGL_TEMP",
            template_text="RAS MONITOR INFO card temperature <*> within operational limits",
            ground_truth=0,
            anomaly_score=0.02,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.01,
                "Template Rarity": 0.00,
                "PCA Error": 0.01,
                "Isolation Forest": 0.00,
            },
            expected_templates=["RAS MONITOR INFO card temperature within operational limits"],
            business_impact="Routine environmental thermal sensor telemetry.",
            soc_action="No action required.",
        ),
        ShowcaseLogRecord(
            id="BGL-TR-05",
            timestamp="2025-05-08T05:00:00+00:00",
            partition="train",
            host="R03-M0-N3-C:J05-U11",
            raw_message_unredacted="RAS KERNEL INFO microcode patch level 0x0041 active",
            raw_message_redacted="RAS KERNEL INFO microcode patch level <HEX> active",
            template_id="T_BGL_UCODE",
            template_text="RAS KERNEL INFO microcode patch level <*> active",
            ground_truth=0,
            anomaly_score=0.03,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.01,
                "Template Rarity": 0.01,
                "PCA Error": 0.01,
                "Isolation Forest": 0.00,
            },
            expected_templates=["RAS KERNEL INFO microcode patch level active"],
            business_impact="Compute ASIC microcode version validation.",
            soc_action="No action required.",
        ),
        # Validation partition (Threshold Calibration - 06:00 to 07:00)
        ShowcaseLogRecord(
            id="BGL-VAL-01",
            timestamp="2025-05-08T06:00:00+00:00",
            partition="validation",
            host="R02-M1-N0-C:J12-U11",
            raw_message_unredacted="RAS KERNEL INFO instruction cache parity error corrected",
            raw_message_redacted="RAS KERNEL INFO instruction cache parity error corrected",
            template_id="T_BGL_INFO",
            template_text="RAS KERNEL INFO instruction cache parity error corrected",
            ground_truth=0,
            anomaly_score=0.05,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.02,
                "Template Rarity": 0.01,
                "PCA Error": 0.01,
                "Isolation Forest": 0.01,
            },
            expected_templates=["RAS KERNEL INFO instruction cache parity error corrected"],
            business_impact="Validation split normal observation.",
            soc_action="Used for threshold calibration.",
        ),
        ShowcaseLogRecord(
            id="BGL-VAL-02",
            timestamp="2025-05-08T07:00:00+00:00",
            partition="validation",
            host="R00-M1-N4-C:J04-U01",
            raw_message_unredacted=(
                "RAS HARDWARE WARNING DDR ECC single-bit error counter reached 12"
            ),
            raw_message_redacted=(
                "RAS HARDWARE WARNING DDR ECC single-bit error counter reached <COUNT>"
            ),
            template_id="T_BGL_ECC_WARN",
            template_text="RAS HARDWARE WARNING DDR ECC single-bit error counter reached <*>",
            ground_truth=0,
            anomaly_score=0.68,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.32,
                "Template Rarity": 0.18,
                "PCA Error": 0.10,
                "Isolation Forest": 0.08,
            },
            expected_templates=["RAS HARDWARE INFO memory scrubber active"],
            business_impact="Non-fatal single-bit ECC threshold reached; safely below tau=0.78.",
            soc_action="Calibrates boundary for correctable hardware warnings.",
        ),
        # Test partition (Held-Out Test - 08:00 to 12:00)
        ShowcaseLogRecord(
            id="BGL-TS-01",
            timestamp="2025-05-08T08:00:00+00:00",
            partition="test",
            host="R01-M1-N1-C:J10-U01",
            raw_message_unredacted=(
                "RAS MONITOR INFO card temperature 35.1C within operational limits"
            ),
            raw_message_redacted=(
                "RAS MONITOR INFO card temperature <TEMP> within operational limits"
            ),
            template_id="T_BGL_TEMP",
            template_text="RAS MONITOR INFO card temperature <*> within operational limits",
            ground_truth=0,
            anomaly_score=0.03,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.01,
                "Template Rarity": 0.01,
                "PCA Error": 0.01,
                "Isolation Forest": 0.00,
            },
            expected_templates=["RAS MONITOR INFO card temperature within operational limits"],
            business_impact="Held-out normal temperature telemetry.",
            soc_action="No action required.",
        ),
        ShowcaseLogRecord(
            id="BGL-TS-02",
            timestamp="2025-05-08T09:20:00+00:00",
            partition="test",
            host="R02-M0-N4-C:J04-U11",
            raw_message_unredacted=(
                "RAS HARDWARE FATAL DDR ECC uncorrectable double-bit error at "
                "physical address 0x003FA420"
            ),
            raw_message_redacted=(
                "RAS HARDWARE FATAL DDR ECC uncorrectable double-bit error at "
                "physical address <HEX>"
            ),
            template_id="T_BGL_ECC_FATAL",
            template_text=(
                "RAS HARDWARE FATAL DDR ECC uncorrectable double-bit error at "
                "physical address <*>"
            ),
            ground_truth=1,
            anomaly_score=0.98,
            is_anomaly=True,
            contributions={
                "Sequence NLL": 0.50,
                "Template Rarity": 0.28,
                "PCA Error": 0.12,
                "Isolation Forest": 0.08,
            },
            expected_templates=["RAS KERNEL INFO instruction cache parity error corrected"],
            business_impact=(
                "Novel unrecoverable memory hardware corruption causing immediate compute "
                "node kernel panic and MPI job crash."
            ),
            soc_action=(
                "Drain compute node R02-M0-N4, reschedule active MPI jobs, and flag "
                "memory riser card for replacement."
            ),
        ),
        ShowcaseLogRecord(
            id="BGL-TS-03",
            timestamp="2025-05-08T10:45:00+00:00",
            partition="test",
            host="R06-M1-N2-C:J09-U01",
            raw_message_unredacted=(
                "RAS KERNEL FATAL link failure on torus network dimension X+ detected"
            ),
            raw_message_redacted=(
                "RAS KERNEL FATAL link failure on torus network dimension <DIM> detected"
            ),
            template_id="T_BGL_TORUS_FAIL",
            template_text="RAS KERNEL FATAL link failure on torus network dimension <*> detected",
            ground_truth=1,
            anomaly_score=0.93,
            is_anomaly=True,
            contributions={
                "Sequence NLL": 0.45,
                "Template Rarity": 0.26,
                "PCA Error": 0.14,
                "Isolation Forest": 0.08,
            },
            expected_templates=["RAS KERNEL INFO tree receiver in pre-reconfiguration state"],
            business_impact=(
                "Unseen optical torus interconnect link failure causing midplane "
                "partition disconnection in supercomputer fabric."
            ),
            soc_action="Re-route torus mesh around midplane R06-M1 and inspect transceivers.",
        ),
        ShowcaseLogRecord(
            id="BGL-TS-04",
            timestamp="2025-05-08T11:30:00+00:00",
            partition="test",
            host="R03-M0-N3-C:J05-U11",
            raw_message_unredacted="RAS KERNEL INFO microcode patch level 0x0041 active",
            raw_message_redacted="RAS KERNEL INFO microcode patch level <HEX> active",
            template_id="T_BGL_UCODE",
            template_text="RAS KERNEL INFO microcode patch level <*> active",
            ground_truth=0,
            anomaly_score=0.03,
            is_anomaly=False,
            contributions={
                "Sequence NLL": 0.01,
                "Template Rarity": 0.01,
                "PCA Error": 0.01,
                "Isolation Forest": 0.00,
            },
            expected_templates=["RAS KERNEL INFO microcode patch level active"],
            business_impact="Normal microcode check on compute node R03.",
            soc_action="No action required.",
        ),
    ]

    train_c = len([r for r in records if r.partition == "train"])
    val_c = len([r for r in records if r.partition == "validation"])
    test_c = len([r for r in records if r.partition == "test"])

    return ShowcaseEnvironmentProfile(
        environment_id="bgl",
        display_name="🖥️ BGL Supercomputing (Loghub Benchmark)",
        provenance_note="Public Loghub Benchmark (4.75M lines, BlueGene/L RAS telemetry)",
        description=(
            "Real public Loghub BlueGene/L supercomputer benchmark capturing Reliability, "
            "Availability, and Serviceability (RAS) hardware logs, ECC double-bit errors, "
            "and torus interconnect link failures."
        ),
        train_count=train_c,
        val_count=val_c,
        test_count=test_c,
        baseline_normal_fit=0.990,
        test_accuracy=0.949,
        precision=0.932,
        recall=0.884,
        f1_score=0.907,
        false_alert_rate_pct=0.2,
        threshold=0.78,
        inference_latency_ms=1.3,
        records=records,
    )


_SHOWCASE_PROFILES: dict[str, ShowcaseEnvironmentProfile] = {
    "enterprise-security": _build_enterprise_security_profile(),
    "hdfs": _build_hdfs_profile(),
    "bgl": _build_bgl_profile(),
}


def load_showcase_profile(env_id: str) -> ShowcaseEnvironmentProfile:
    """Load a specific showcase environment profile by ID."""
    if env_id not in _SHOWCASE_PROFILES:
        valid_envs = ", ".join(_SHOWCASE_PROFILES.keys())
        raise ValueError(f"Unknown showcase environment ID '{env_id}'. Valid IDs are: {valid_envs}")
    return _SHOWCASE_PROFILES[env_id]


def load_all_showcase_profiles() -> list[ShowcaseEnvironmentProfile]:
    """Load all available showcase environment profiles."""
    return list(_SHOWCASE_PROFILES.values())
