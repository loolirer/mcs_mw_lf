import os
import re
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from pathlib import Path

def parse_mocap_log(file_path):
    shot_data = {}
    nodes_found = set()

    pattern = re.compile(r"\[MainScheduler\]: Received (\d+) blobs from CaptureNode (\d+) \(Shot (\d+)\)")

    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return {}, []

    with open(file_path, 'r') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                blobs = int(match.group(1))
                node_id = int(match.group(2))
                shot_id = int(match.group(3))
                
                nodes_found.add(node_id)
                if shot_id not in shot_data:
                    shot_data[shot_id] = {}

                shot_data[shot_id][node_id] = 1 if blobs == 0 else 0

    return shot_data, sorted(list(nodes_found))

def moving_average(data, window_size=30):
    if len(data) < window_size:
        return np.full(len(data), np.mean(data))
    return np.convolve(data, np.ones(window_size)/window_size, mode='same')

def plot_system_synchrony(shot_data, nodes, t_on_us=5000, window_size=30):
    miss_rate_color = 'black'
    miss_color = '#e74c3c'
    hit_color = '#2ecc71'

    if not shot_data:
        print("No valid data found in the logs.")
        return

    sorted_shots = sorted(shot_data.keys())
    global_miss_binary = []
    num_expected_nodes = len(nodes)

    for shot in sorted_shots:
        node_results = shot_data[shot]
        
        is_global_hit = (len(node_results) == num_expected_nodes) and all(val == 0 for val in node_results.values())
        
        global_miss_binary.append(0 if is_global_hit else 1)

    global_miss_binary = np.array(global_miss_binary)
    miss_rate_ma = moving_average(global_miss_binary, window_size)

    fig, ax = plt.subplots(figsize=(14, 5))

    for idx, shot in enumerate(sorted_shots):
        color = hit_color if global_miss_binary[idx] == 0 else miss_color
        ax.broken_barh([(shot, 1)], (0, 1), facecolors=color, alpha=0.9)

    ax.plot(sorted_shots, miss_rate_ma, color=miss_rate_color, linewidth=1.0, label='System Failure Trend')

    total_shots = len(global_miss_binary)
    total_hits = total_shots - np.sum(global_miss_binary)
    global_hit_rate = (total_hits / total_shots) * 100 if total_shots > 0 else 0

    ax.set_yticks([])
    ax.set_xlabel("Shot Index Timeline", fontsize=12)
    ax.set_ylabel("Miss Rate (%)", fontsize=12)
    ax.set_title("Synchrony Trend Rate Evaluation for ($t_{on}$) =" + f"${t_on_us} \mu s$ \nTotal Hit Rate: {global_hit_rate:.1f}%", fontsize=14)
    ax.set_ylim(-0.05, 1.1)
    custom_lines = [Line2D([0], [0], color=hit_color, lw=8),
                    Line2D([0], [0], color=miss_color, lw=8),
                    Line2D([0], [0], color=miss_rate_color, lw=2)]
    ax.legend(custom_lines, ['Global Hit', 'Global Miss', f'{window_size}-Shot Miss Trend'], 
              loc='upper center', bbox_to_anchor=(0.5, -0.18), ncol=3)

    plt.tight_layout()
    plt.show()

filename = 'outputs/output_4000.txt'
t_on_us = int(Path(filename).stem.split('_')[-1])

data, nodes_list = parse_mocap_log(filename)
plot_system_synchrony(data, nodes_list, t_on_us=t_on_us, window_size=30)