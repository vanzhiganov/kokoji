Supported Platforms
===================

Koji requires Python 3.6 or newer on all components. Currently this
involves all active Fedoras and RHEL/CentOS 8+.

+-----------+-----+-----+---------+-------+-----+-----+
| Component | Hub | Web | Builder | Utils | Lib | CLI |
+===========+=====+=====+=========+=======+=====+=====+
| Python    | 3.6 | 3.6 | 3.6     | 3.6   | 3.6 | 3.6 |
+-----------+-----+-----+---------+-------+-----+-----+

For database we're supporting RHEL/CentOS 8+. So, it means that
postgresl 10 is still supported, anyway we encourage using at
least PG 12 (``dnf module enable postgresql:12``).  At least some
indices are set up in more efficient way with newer PG
capabilities.
