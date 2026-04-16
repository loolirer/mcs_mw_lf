import os
import re
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from scipy.signal import medfilt

max_diff = 5000
EXPECTED_DIGITS = 19

def parse_jitter_log(file_path):
    phys_data = {}
    dev_data = {}
    nodes_found = set()
    pattern_node_shot = re.compile(r"\[CaptureNode (\d+)\] Shot (\d+)")
    pattern_logical = re.compile(r"- Logical Time: (\d+)")
    pattern_physical = re.compile(r"- Physical Time: (\d+)")
    if not os.path.exists(file_path):
        return {}, {}, []
    curr_node, curr_shot, curr_log = None, None, None
    with open(file_path, 'r') as f:
        for line in f:
            if '[MainScheduler]' in line:
                curr_node, curr_shot, curr_log = None, None, None
                continue
            m_ns = pattern_node_shot.search(line)
            if m_ns:
                curr_node, curr_shot = int(m_ns.group(1)), int(m_ns.group(2))
                curr_log = None
                nodes_found.add(curr_node)
                continue
            m_log = pattern_logical.search(line)
            if m_log:
                curr_log = int(m_log.group(1))
                continue
            m_phys = pattern_physical.search(line)
            if m_phys and curr_node is not None and curr_log is not None:
                phys_time = int(m_phys.group(1))
                if len(str(phys_time)) != EXPECTED_DIGITS or len(str(curr_log)) != EXPECTED_DIGITS:
                    curr_node, curr_shot, curr_log = None, None, None
                    continue
                if curr_node not in phys_data:
                    phys_data[curr_node] = {}
                if curr_node not in dev_data:
                    dev_data[curr_node] = {}
                phys_data[curr_node][curr_shot] = phys_time
                dev_data[curr_node][curr_shot] = (phys_time - curr_log) / 1e6
                curr_node, curr_shot, curr_log = None, None, None
    return phys_data, dev_data, sorted(list(nodes_found))

def compute_inter_node_jitter(phys_data, nodes):
    all_shots = set()
    for n in nodes:
        if n in phys_data:
            all_shots.update(phys_data[n].keys())
    jitter_by_shot = {}
    for shot in all_shots:
        timestamps = [phys_data[n][shot] for n in nodes if n in phys_data and shot in phys_data[n]]
        if len(timestamps) < 2:
            continue
        jitter_by_shot[shot] = (max(timestamps) - min(timestamps)) / 1e6
    return jitter_by_shot

def plot_metrics(phys_data, dev_data, nodes, t_on_us):
    if not phys_data:
        print("No data to plot.")
        return

    jitter_by_shot = compute_inter_node_jitter(phys_data, nodes)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=False)
    fig.suptitle(f"Synchronization Metrics  ($t_{{on}}$ = {t_on_us} $\\mu$s)", fontsize=15)

    j_shots = sorted(jitter_by_shot.keys())
    j_vals = [jitter_by_shot[s] for s in j_shots]
    j_vals = medfilt(j_vals, kernel_size=3)
    ax1.plot(j_shots, j_vals, color='steelblue', linewidth=1.2, alpha=0.85, label='$J_k$')
    ax1.set_ylabel("$J_k$ (ms)", fontsize=12)
    ax1.set_xlabel("Shot Index", fontsize=12)
    ax1.set_title("Inter-Node Synchronization Jitter  $J_k = \\max_{i,j}|T^{(i)}_{\\mathrm{phys},k} - T^{(j)}_{\\mathrm{phys},k}|$", fontsize=12)
    ax1.grid(True, linestyle='--', alpha=0.6)
    ax1.legend(loc='upper right')

    for n_id in nodes:
        if n_id in dev_data:
            s_list = sorted(dev_data[n_id].keys())
            v_list = [dev_data[n_id][s] for s in s_list]
            v_list = medfilt(v_list, kernel_size=3)
            ax2.plot(s_list, v_list, linewidth=1.2, alpha=0.8, label=f"Node {n_id}")
    ax2.axhline(0, color='black', linewidth=0.8, linestyle='--')
    ax2.set_ylabel("$\\Delta_k^{(i)}$ (ms)", fontsize=12)
    ax2.set_xlabel("Shot Index", fontsize=12)
    ax2.set_title("Logical-to-Physical Time Deviation  $\\Delta_k^{(i)} = T^{(i)}_{\\mathrm{phys},k} - T^{(i)}_{\\mathrm{log},k}$", fontsize=12)
    ax2.grid(True, linestyle='--', alpha=0.6)
    ax2.legend(loc='upper right', title="Capture Nodes", ncol=len(nodes))

    plt.tight_layout()
    plt.show()

filename = 'outputs/output_10000.txt'
t_on_val = int(Path(filename).stem.split('_')[-1])
phys_data, dev_data, n_list = parse_jitter_log(filename)
plot_metrics(phys_data, dev_data, n_list, t_on_val)