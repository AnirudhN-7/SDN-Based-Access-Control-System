"""
SDN-Based Access Control System — POX Controller
Course: COMPUTER NETWORKS - UE24CS252B

Run from your POX root directory:
    python pox.py access_control   (if saved as pox/ext/access_control.py)
  OR simply:
    python pox.py                  (if this file is named pox.py and placed in the pox root)

What this controller does:
  1. On every PacketIn, check the SOURCE MAC against the whitelist.
  2. If the source is NOT whitelisted → drop and install a drop-flow so future
     packets from that MAC are dropped in the dataplane without hitting the controller.
  3. If the source IS whitelisted → learn src_mac→in_port, then:
       a. If we already know the destination port → install a unicast forwarding
          flow and send the current packet out that port.
       b. Otherwise → flood (normal L2 learning-switch behaviour).
"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpid_to_str

log = core.getLogger()

WHITELIST = {
    "00:00:00:00:00:01",
    "00:00:00:00:00:02",
    "00:00:00:00:00:03",
}

# Per-switch MAC → port table  {dpid: {mac_str: port}}
mac_to_port = {}


def _handle_ConnectionUp(event):
    dpid = dpid_to_str(event.dpid)
    mac_to_port[dpid] = {}
    log.info("Switch %s connected", dpid)


def _handle_PacketIn(event):
    packet   = event.parsed
    dpid     = dpid_to_str(event.dpid)
    in_port  = event.port
    src_mac  = str(packet.src)
    dst_mac  = str(packet.dst)

    # ------------------------------------------------------------------ #
    # 1. Whitelist check on SOURCE MAC                                     #
    # ------------------------------------------------------------------ #
    if src_mac not in WHITELIST:
        log.info("BLOCKED  src=%s (not whitelisted) — installing drop flow", src_mac)
        # Install a drop flow so the dataplane handles future packets silently
        msg = of.ofp_flow_mod()
        msg.match.dl_src = packet.src          # match on source MAC
        msg.hard_timeout = 60                  # re-evaluate after 60 s
        msg.priority     = 10                  # higher than default forwarding flows
        # No actions → drop
        event.connection.send(msg)
        return

    # ------------------------------------------------------------------ #
    # 2. MAC learning                                                      #
    # ------------------------------------------------------------------ #
    table = mac_to_port.setdefault(dpid, {})
    table[src_mac] = in_port

    # ------------------------------------------------------------------ #
    # 3. Forwarding decision                                               #
    # ------------------------------------------------------------------ #
    if dst_mac in table:
        out_port = table[dst_mac]
        log.info("FORWARD  %s → %s  via port %s", src_mac, dst_mac, out_port)

        # Install a flow so future packets take the fast path
        msg = of.ofp_flow_mod()
        msg.match        = of.ofp_match.from_packet(packet, in_port)
        msg.idle_timeout = 30
        msg.hard_timeout = 120
        msg.priority     = 5
        msg.data         = event.ofp          # buffer the current packet
        msg.in_port      = in_port
        msg.actions.append(of.ofp_action_output(port=out_port))
        event.connection.send(msg)

    else:
        # Destination unknown → flood (ARP, first packet, etc.)
        log.info("FLOOD    %s → %s  (dst unknown)", src_mac, dst_mac)
        msg = of.ofp_packet_out()
        msg.data    = event.ofp
        msg.in_port = in_port
        msg.actions.append(of.ofp_action_output(port=of.OFPP_FLOOD))
        event.connection.send(msg)


def launch():
    core.openflow.addListenerByName("ConnectionUp", _handle_ConnectionUp)
    core.openflow.addListenerByName("PacketIn",     _handle_PacketIn)
    log.info("Access control + MAC-learning running. Whitelist: %s", WHITELIST)
