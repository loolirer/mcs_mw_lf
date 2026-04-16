import os
import re
import yaml
import subprocess
import shutil
import argparse

def get_arp_table():
    """
    Retrieves the ARP table from the system.
    Returns a list of tuples: (ip_address, mac_address)
    """
    if not shutil.which("arp"):
        print("Warning: 'arp' command not found. IPs cannot be resolved automatically.")
        return []

    try:
        arp_output = subprocess.check_output(["arp", "-a"], text=True)
    except subprocess.CalledProcessError:
        print("Warning: Failed to execute 'arp -a'.")
        return []

    ip_mac_pattern = re.compile(
        r"\(([\d.]+)\)\s+at\s+([0-9a-f:]{17}|[0-9a-f-]{17})", re.IGNORECASE
    )

    arp_entries = ip_mac_pattern.findall(arp_output)
    return [(ip, mac.upper().replace("-", ":")) for ip, mac in arp_entries]

def get_mac_mapping(mac_list):
    """
    Maps a list of target MAC addresses to their current IP addresses.
    """
    target_macs = [mac.upper() for mac in mac_list]
    arp_entries = get_arp_table()

    mac_to_ip = {}
    
    for target_mac in target_macs:
        for ip, arp_mac in arp_entries:
            if target_mac == arp_mac:
                mac_to_ip[target_mac] = ip
                break 

    return mac_to_ip

def compose_lf_c(nodes, filename: str = "src/MotionTrackingArena.lf", local_rti: bool = False):
    rti_node = next((node for node in nodes if node.get('reactor_type') == 'RTI'), None)

    blinker_nodes = [node for node in nodes if node.get('reactor_type') == 'Blinker']
    worker_nodes  = [node for node in nodes if node.get('reactor_type') == 'Capture Node']

    node_count = len(worker_nodes)

    rti_at_clause = ""
    scheduler_at_clause = ""

    if rti_node:
        rti_host = rti_node.get('hostname', 'localhost')
        rti_user = rti_node.get('user', 'root')
        rti_max_cycles = rti_node.get('max_cycles', 3000)
        rti_capture_rate = rti_node.get('capture_rate', 30)
        print(f"RTI Host found: {rti_host} (User: {rti_user})")
        
        rti_at_clause = f" at {rti_user}@{rti_host}.local"
        scheduler_at_clause = f" at {rti_user}@{rti_host}.local"
    
        if local_rti:
            print("CLI Flag detected: RTI will be local (omitting 'at' clause for Reactor and Scheduler).")
            rti_at_clause = "" 
            scheduler_at_clause = ""

    else:
        raise ValueError("No RTI Host found in config.")
    
    blink_import = '\nimport Blink from "Blink.lf"' if blinker_nodes else ""

    # Begin constructing LF code
    lf_code = f"""target C {{
    coordination: centralized,
    clock-sync: on
    # If PTP is on, clock-sync: off
}}

import CaptureNode from "CaptureNode.lf"
import MainScheduler from "MainScheduler.lf"{blink_import}

federated reactor MotionTrackingArena (
    node_count: int = {node_count}
){rti_at_clause} {{  
    S = new MainScheduler(
        node_count=node_count,
        capture_period={int(1e6//rti_capture_rate)} usec,
        max_cycles={rti_max_cycles}
    ){scheduler_at_clause};
"""
    
    node_instantiations = []
    
    # Iterate ONLY over the worker nodes (excluding RTI host)
    for i, node in enumerate(worker_nodes):
        node_index = f"N{i}"
        mac = node.get('mac_address', '')
        ip = node.get('ip_address', '127.0.0.1')
        user = node.get('user', 'root')
        hostname = node.get('hostname', 'localhost')
        
        at_clause = ""
        # Only add 'at' if it is a remote node (not localhost)
        if ip != "127.0.0.1":
            at_clause = f" at {user}@{hostname}"

        instantiation = f"""
    {node_index} = new CaptureNode(
        index={i},
        mac_address="{mac}"
    ){at_clause};"""
        
        node_instantiations.append(instantiation)
        
    lf_code += "\n".join(node_instantiations)

    # Blink reactor instantiations
    for i, node in enumerate(blinker_nodes):
        gpio_pin = node.get('gpio_pin', 18)
        t_on_us  = node.get('t_on_us', 5000)
        user     = node.get('user', 'root')
        hostname = node.get('hostname', 'localhost')
        ip       = node.get('ip_address', '127.0.0.1')
        at_clause = f" at {user}@{hostname}" if ip != "127.0.0.1" else ""
        lf_code += f"""
    \nB{i} = new Blink(
        gpio_pin={gpio_pin},
        t_on={t_on_us} usec
    ){at_clause};"""

    lf_code += "\n\n"

    # Create connections based on the filtered node_count
    trigger_connections = []
    offset = 0
    for i, node in enumerate(blinker_nodes):
        trigger_connections.append(f"    S.capture_trigger -> B{i}.blink_trigger;")
        offset = node.get('t_on_us', 5000)//2
    for i in range(node_count):
        node_index = f"N{i}"
        trigger_connections.append(f"    S.capture_trigger -> {node_index}.capture_trigger after {offset} usec;")
        
    lf_code += "\n".join(trigger_connections)
    
    output_ports = [f"N{i}.data_out" for i in range(node_count)]
    output_list_str = ",\n    ".join(output_ports)
    
    lf_code += f"""
    
    {output_list_str} 
    -> S.data_in;
}}"""

    # Save file
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "w") as f:
            f.write(lf_code)
        print(f"\nSuccessfully generated {filename} for {node_count} worker nodes.")
    except IOError as e:
        print(f"Error saving file: {e}")

if __name__ == "__main__":
    # --- ARGUMENT PARSING ---
    parser = argparse.ArgumentParser(description="Generate Lingua Franca federated reactor.")
    parser.add_argument(
        "--local-rti", 
        action="store_true", 
        help="If set, omits the 'at user@host' clause for the main reactor and scheduler."
    )
    args = parser.parse_args()
    # ------------------------

    try:
        with open("lf_config.yaml", "r") as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        print("Error: lf_config.yaml not found.")
        exit(1)

    nodes = config.get("clients", [])
    
    if not nodes:
        print("No clients found in yaml.")
        exit()

    mac_list = [n.get("mac_address") for n in nodes if n.get("mac_address")]
    mac_to_ip = get_mac_mapping(mac_list)

    for node in nodes:
        mac = node.get("mac_address")
        if mac and mac in mac_to_ip:
            node['ip_address'] = mac_to_ip[mac]
        else:
            print(f"Warning: Could not resolve IP for {mac}. Defaulting to 127.0.0.1")
            node['ip_address'] = "127.0.0.1"

    # Pass the CLI argument to the function
    compose_lf_c(nodes, local_rti=args.local_rti)