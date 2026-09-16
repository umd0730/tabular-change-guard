# Security and data handling

The tool has no network client and never evaluates CSV cells. It reads inputs
once and reports hashes of those exact bytes. Runtime input files are never
included in this repository. Do not point shell output redirection at an input.

Formula-like value detection is a heuristic, not a security boundary. Column
names, positions, counts and file hashes are exposed in reports. Do not share
them when those metadata are sensitive. Use untrusted files within normal OS
resource limits; the default per-file byte limit is 10 MiB.

For a security report, use GitHub's private vulnerability reporting if enabled.
Otherwise open an issue asking for a private channel, without exploit details,
credentials or private data. Never upload real customer data as a reproducer.

The latest 0.1.x release is the supported line. No response-time commitment is
made. Do not describe this project as independently security-audited.
