# SDN-Based Access Control System

> **Course:** Computer Networks — UE24CS252B  
> **Stack:** Python 3 · POX3 Controller · Mininet · OpenFlow 1.0 · Open vSwitch

---

## Problem Statement

In traditional networks, access control is enforced at each device independently, making policy management complex and error-prone. This project implements a **Software-Defined Networking (SDN) approach** to centralize access control: only whitelisted hosts are allowed to communicate across the network, while all unauthorized hosts are silently dropped at the dataplane level.

**Core objectives:**
- Maintain a whitelist of authorized MAC addresses at the controller
- Dynamically install allow/deny flow rules on the switch upon first packet arrival
- Block unauthorized hosts without manual per-device configuration
- Verify correct access control through ping and throughput tests
- Perform regression tests to confirm policy consistency across the session

---

## Network Topology

```
    h1          h2          h3          h4
(10.0.0.1)  (10.0.0.2)  (10.0.0.3)  (10.0.0.4)
    |           |           |           |
    +-----+-----+-----------+-----------+
          |
        [ s1 ]   ← OVS Switch (OpenFlow 1.0)
          |
    [ POX3 Controller ]
      127.0.0.1:6633
```

| Host | IP Address | MAC Address       | Status          |
|------|------------|-------------------|-----------------|
| h1   | 10.0.0.1   | 00:00:00:00:00:01 | ✅ Whitelisted  |
| h2   | 10.0.0.2   | 00:00:00:00:00:02 | ✅ Whitelisted  |
| h3   | 10.0.0.3   | 00:00:00:00:00:03 | ✅ Whitelisted  |
| h4   | 10.0.0.4   | 00:00:00:00:00:04 | ❌ Unauthorized |

---

## Project Structure

```
.
├── access_control.py   # POX3 controller — whitelist enforcement + MAC learning
└── topology.py         # Mininet topology — hosts, switch, links, test scenarios
```

---

## Prerequisites

Make sure the following are installed on your machine (Ubuntu/Debian recommended):

- **Python 3.x** (required by both POX3 and Mininet)
- **Mininet** — `sudo apt-get install mininet`
- **Open vSwitch** — `sudo apt-get install openvswitch-switch`
- **POX3 Controller** — clone from [https://github.com/noxrepo/pox](https://github.com/noxrepo/pox) (use the `dart` branch, which supports Python 3)
- **iperf** — `sudo apt-get install iperf`

---

## Setup & Execution Steps

### Step 1 — Clone POX3 and place the controller

```bash
git clone https://github.com/noxrepo/pox.git
cd pox
git checkout dart        # dart branch supports Python 3
```

Copy `access_control.py` into the `ext/` directory inside your POX folder:

```bash
cp /path/to/access_control.py ext/access_control.py
```

### Step 2 — Start the POX3 Controller (Terminal 1)

From inside the POX root directory:

```bash
python3 pox.py access_control
```

You should see:

```
INFO:access_control:Access control + MAC-learning running. Whitelist: {'00:00:00:00:00:01', '00:00:00:00:00:02', '00:00:00:00:00:03'}
```

> **Keep this terminal running.** POX3 listens on `127.0.0.1:6633` for incoming switch connections.

### Step 3 — Launch the Mininet Topology (Terminal 2)

In a new terminal, from the directory containing `topology.py`:

```bash
sudo python3 topology.py
```

The script will:
1. Spin up the virtual network (4 hosts + 1 switch)
2. Connect the switch to the POX3 controller
3. Wait 3 seconds for the OpenFlow handshake to complete
4. Automatically run all test scenarios
5. Drop into the Mininet CLI for interactive use

### Step 4 — Interactive CLI (Optional)

Once the automated tests finish, you'll land in the Mininet CLI:

```
mininet>
```

You can run manual tests here, for example:

```bash
mininet> h1 ping h2                    # should succeed
mininet> h4 ping h1                    # should fail (100% packet loss)
mininet> h1 iperf -c h3               # throughput test between whitelisted hosts
mininet> sh ovs-ofctl dump-flows s1    # inspect flow table
mininet> exit                          # shut down the network
```

---

## Expected Output

### Test Scenario 1 — Allowed Communication (h1 → h2)

```
--- Test Scenario 1: Allowed communication (h1 → h2) ---
PING 10.0.0.2 (10.0.0.2) 56(84) bytes of data.
64 bytes from 10.0.0.2: icmp_seq=1 ttl=64 time=X ms
64 bytes from 10.0.0.2: icmp_seq=2 ttl=64 time=X ms
64 bytes from 10.0.0.2: icmp_seq=3 ttl=64 time=X ms

--- 10.0.0.2 ping statistics ---
3 packets transmitted, 3 received, 0% packet loss
```

POX3 controller log:
```
INFO:access_control:Switch 00-00-00-00-00-00-00-01 connected
INFO:access_control:FLOOD    00:00:00:00:00:01 → ff:ff:ff:ff:ff:ff  (dst unknown)
INFO:access_control:FORWARD  00:00:00:00:00:01 → 00:00:00:00:00:02  via port 2
```

**Screenshot:**

![Test Scenario 1 - Allowed Communication](screenshots/scenario1_allowed.png)

---

### Test Scenario 2 — Unauthorized Access (h4 → h1)

```
--- Test Scenario 2: Unauthorized access (h4 → h1) ---
PING 10.0.0.1 (10.0.0.1) 56(84) bytes of data.

--- 10.0.0.1 ping statistics ---
3 packets transmitted, 0 received, 100% packet loss, time XXXX ms
(Expect 100% packet loss — h4 is not whitelisted)
```

POX3 controller log:
```
INFO:access_control:BLOCKED  src=00:00:00:00:00:04 (not whitelisted) — installing drop flow
```

**Screenshot:**

![Test Scenario 2 - Unauthorized Access Blocked](screenshots/scenario2_blocked.png)

---

### Test Scenario 3 — iperf Throughput (h1 → h3)

```
--- Test Scenario 3: iperf throughput between whitelisted hosts (h1 → h3) ---
------------------------------------------------------------
Client connecting to 10.0.0.3, TCP port 5001
TCP window size: 85.3 KByte (default)
------------------------------------------------------------
[  3] local 10.0.0.1 port XXXXX connected with 10.0.0.3 port 5001
[ ID] Interval       Transfer     Bandwidth
[  3]  0.0- 5.0 sec  5.62 MBytes  9.43 Mbits/sec
```

> Bandwidth is capped near **10 Mbits/sec** as set by the `bw=10` link parameter.

**Screenshot:**

![Test Scenario 3 - iperf Throughput](screenshots/scenario3_iperf.png)

---

### Regression Test — Re-run h1 → h2 ping

```
--- Regression Test: Re-run h1 → h2 ping to confirm policy consistency ---
3 packets transmitted, 3 received, 0% packet loss
```

Confirms that previously installed forwarding flows remain valid and the whitelist policy is consistently enforced throughout the session.

**Screenshot:**

![Regression Test - Policy Consistency](screenshots/regression_test.png)

---

### Flow Table Dump (switch s1)

```
--- Flow table dump (switch s1) ---
```

**Screenshot:**

![Flow Table Dump](screenshots/flow_table_dump.png)

---

## Flow Tables

After all test scenarios run, `ovs-ofctl dump-flows s1` produces entries of the following form:

### Drop Flow — Unauthorized Host (h4)

| Field        | Value                      |
|--------------|----------------------------|
| Priority     | 10                         |
| Match        | `dl_src=00:00:00:00:00:04` |
| Hard Timeout | 60 s                       |
| Actions      | *(none — drop)*            |

```
cookie=0x0, duration=Xs, table=0, n_packets=3, n_bytes=294,
hard_timeout=60, priority=10,dl_src=00:00:00:00:00:04 actions=drop
```

---

### Forwarding Flow — Whitelisted Host-to-Host (e.g., h1 → h2)

| Field        | Value                                                            |
|--------------|------------------------------------------------------------------|
| Priority     | 5                                                                |
| Match        | `in_port=1, dl_src=00:00:00:00:00:01, dl_dst=00:00:00:00:00:02` |
| Idle Timeout | 30 s                                                             |
| Hard Timeout | 120 s                                                            |
| Actions      | `output:2`                                                       |

```
cookie=0x0, duration=Xs, table=0, n_packets=N, n_bytes=N,
idle_timeout=30, hard_timeout=120, priority=5,
in_port=1,dl_src=00:00:00:00:00:01,dl_dst=00:00:00:00:00:02
actions=output:2
```

---

### Summary of Flow Table Entries

| Rule Type       | Priority | Match Fields                  | Action     | Idle T/O | Hard T/O |
|-----------------|----------|-------------------------------|------------|----------|----------|
| Drop (h4)       | 10       | `dl_src=00:00:00:00:00:04`    | DROP       | —        | 60 s     |
| Forward (h1→h2) | 5        | `in_port=1, src=:01, dst=:02` | `output:2` | 30 s     | 120 s    |
| Forward (h1→h3) | 5        | `in_port=1, src=:01, dst=:03` | `output:3` | 30 s     | 120 s    |
| Forward (h2→h1) | 5        | `in_port=2, src=:02, dst=:01` | `output:1` | 30 s     | 120 s    |

> Forwarding flows are installed lazily — only after the destination MAC has been learned via MAC learning. Initial packets to unknown destinations are flooded.

---

## How It Works

```
PacketIn received by POX3
          │
          ▼
Is src_mac in WHITELIST?
     │              │
    NO             YES
     │              │
     ▼              ▼
Install drop    Learn src_mac → in_port
flow (prio 10)        │
Return          Is dst_mac known?
                │              │
               YES             NO
                │              │
                ▼              ▼
          Install forward   Flood packet
          flow (prio 5)     (ARP / first packet)
          Send packet out
```

---

## Notes

- **POX3** (`dart` branch) is used here, which runs entirely on **Python 3**. Do not use the legacy `master` branch (Python 2 only).
- POX3 speaks **OpenFlow 1.0** only. Do not set `protocols='OpenFlow13'` on the switch.
- Drop flows have a `hard_timeout` of 60 s, after which h4's next packet will be re-evaluated by the controller (and dropped again).
- Forwarding flows expire after 30 s idle or 120 s hard timeout, keeping the flow table fresh.
- The `bw=10` link parameter caps each link at 10 Mbits/sec, which is why iperf reports ~9.4 Mbits/sec.
