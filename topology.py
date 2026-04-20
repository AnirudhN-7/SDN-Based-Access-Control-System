"""
SDN-Based Access Control System — Mininet Topology
Course: COMPUTER NETWORKS - UE24CS252B

Topology
--------
        h1  h2  h3  h4
         \  |  /   /
          [ s1 ]
              |
          (POX controller on 127.0.0.1:6633)

Hosts:
  h1 → 10.0.0.1  MAC 00:00:00:00:00:01  ← WHITELISTED
  h2 → 10.0.0.2  MAC 00:00:00:00:00:02  ← WHITELISTED
  h3 → 10.0.0.3  MAC 00:00:00:00:00:03  ← WHITELISTED
  h4 → 10.0.0.4  MAC 00:00:00:00:00:04  ← UNAUTHORIZED (blocked)

Run:
  Terminal 1:  python pox.py        (from your POX directory)
  Terminal 2:  sudo python3 topology.py
"""

import time
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink


def build_network():
    # NOTE: Do NOT pass controller= here; we add it manually below.
    net = Mininet(switch=OVSSwitch,
                  link=TCLink,
                  autoSetMacs=False)

    info('*** Adding remote controller (POX on 127.0.0.1:6633)\n')
    c0 = net.addController('c0',
                            controller=RemoteController,
                            ip='127.0.0.1',
                            port=6633)

    info('*** Adding switch\n')
    # IMPORTANT: POX speaks OpenFlow 1.0 — do NOT set protocols='OpenFlow13'
    s1 = net.addSwitch('s1')

    info('*** Adding hosts\n')
    h1 = net.addHost('h1', ip='10.0.0.1/24', mac='00:00:00:00:00:01')
    h2 = net.addHost('h2', ip='10.0.0.2/24', mac='00:00:00:00:00:02')
    h3 = net.addHost('h3', ip='10.0.0.3/24', mac='00:00:00:00:00:03')
    h4 = net.addHost('h4', ip='10.0.0.4/24', mac='00:00:00:00:00:04')  # unauthorized

    info('*** Adding links\n')
    net.addLink(h1, s1, bw=10)
    net.addLink(h2, s1, bw=10)
    net.addLink(h3, s1, bw=10)
    net.addLink(h4, s1, bw=10)

    info('*** Starting network\n')
    net.build()
    c0.start()
    s1.start([c0])

    # Give the POX controller time to connect and handshake with the switch
    info('*** Waiting for POX controller to connect (3 s)...\n')
    time.sleep(3)

    info('\n=== SDN Access Control Topology Ready ===\n')
    info('Whitelisted hosts : h1, h2, h3\n')
    info('Unauthorized host : h4 (will be blocked by controller)\n\n')

    info('--- Test Scenario 1: Allowed communication (h1 → h2) ---\n')
    result = h1.cmd('ping -c 3 -W 2 10.0.0.2')
    info(result)

    info('--- Test Scenario 2: Unauthorized access (h4 → h1) ---\n')
    result = h4.cmd('ping -c 3 -W 2 10.0.0.1')
    info(result)
    info('(Expect 100% packet loss — h4 is not whitelisted)\n\n')

    info('--- Test Scenario 3: iperf throughput between whitelisted hosts (h1 → h3) ---\n')
    h3.cmd('iperf -s -D')          # run iperf server as a daemon
    time.sleep(1)
    result = h1.cmd('iperf -c 10.0.0.3 -t 5')
    info(result)

    info('--- Regression Test: Re-run h1 → h2 ping to confirm policy consistency ---\n')
    result = h1.cmd('ping -c 3 -W 2 10.0.0.2')
    info(result)

    info('--- Flow table dump (switch s1) ---\n')
    # OpenFlow 1.0 — no -O flag needed (default for OVS)
    info(s1.cmd('ovs-ofctl dump-flows s1'))

    info('\n*** Launching Mininet CLI (type "exit" to quit) ***\n')
    CLI(net)

    info('*** Stopping network\n')
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    build_network()
