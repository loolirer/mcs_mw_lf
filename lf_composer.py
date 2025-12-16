import os
import re
import yaml
import subprocess

def get_arp_table():
    arp_output = subprocess.check_output(["arp", "-a"], text=True)

    # Regex for parsing IP and MAC addresses
    ip_mac_pattern = re.compile(
        r"\(([\d.]+)\)\s+at\s+([0-9a-f:]{17}|[0-9a-f-]{17})", re.IGNORECASE
    )

    arp_entries = ip_mac_pattern.findall(arp_output)
    return [(ip, mac.upper().replace("-", ":")) for ip, mac in arp_entries]

def get_mac_mapping(mac_list):
    mac_list = [mac.upper() for mac in mac_list]
    arp_entries = get_arp_table()

    mac_to_ip, ip_to_mac = {}, {}
    for mac in mac_list:
        for ip, arp_mac in arp_entries:
            if mac == arp_mac:
                mac_to_ip[mac] = ip
                ip_to_mac[ip] = mac
                break  # Found the IP, no need to check further

    return mac_to_ip, ip_to_mac

def compose_lf(nodes, filename: str = "src/MotionTrackingArena.lf"):
    node_count = len(nodes)
    lf_code = f"""target Python {{
    coordination: decentralized,
    clock-sync: on
    # If PTP is on, clock-sync: off
}}

import CaptureNode from "CaptureNode.lf"
import MainScheduler from "MainScheduler.lf"

federated reactor MotionTrackingArena (
    node_count={node_count}
) {{  
    S = new MainScheduler(
        node_count=node_count,
        capture_rate=1 sec
    );
"""
    
    node_instantiations = []
    
    for i, node in enumerate(nodes):
        node_index = f"N{i}"
        instantiation = f"""
    {node_index} = new CaptureNode(
        index={i},
        mac_address="{node.mac_address}"
    ) at linguafranca@{node.ip_address};"""
        
        node_instantiations.append(instantiation)
        
    lf_code += "\n".join(node_instantiations)

    lf_code += "\n\n"
    trigger_connections = []
    
    for i in range(node_count):
        node_index = f"N{i}"
        trigger_connections.append(f"    S.capture_trigger -> {node_index}.capture_trigger;")
        
    lf_code += "\n".join(trigger_connections)
    
    output_ports = [f"N{i}.data_out" for i in range(node_count)]
    output_list_str = ",\n    ".join(output_ports)
    lf_code += f"""
    
    {output_list_str} 
    -> S.data_in;
}}"""
    try:
        with open(filename, "w") as f:
            f.write(lf_code)
        print(f"\nSuccessfully generated {filename} for {node_count} nodes.")
        print(f"File saved to: {os.path.abspath(filename)}")
    except IOError as e:
        print(f"Error saving file: {e}")

class CaptureNode:
    def __init__(
        self, 
        mac_address="", 
        ip_address=""
    ):
        self.mac_address = mac_address
        self.ip_address = ip_address

if __name__ == "__main__":
    with open("lf_config.yaml", "r") as file:
        client_configs = yaml.safe_load(file)

    mac_list = [client["mac_address"] for client in client_configs.get("clients", [])]
    mac_to_ip, _ = get_mac_mapping(mac_list)

    nodes = []
    for mac in mac_list:
        try:
            ip = mac_to_ip[mac]

        except:
            ip = "192.168.0.100"


        nodes.append(
            CaptureNode(
                mac_address=mac,
                ip_address=ip
            )
        )

    compose_lf(nodes)