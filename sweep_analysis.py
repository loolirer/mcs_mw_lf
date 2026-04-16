import re
import os
import glob
import matplotlib.pyplot as plt
import numpy as np

def parse_sweep_results(directory):
    sweep_stats = {}
    
    log_pattern = re.compile(r"\[MainScheduler\]: Received (\d+) blobs from CaptureNode (\d+) \(Shot (\d+)\)")
    
    file_paths = glob.glob(os.path.join(directory, "output_*.txt"))
    
    if not file_paths:
        print(f"No files found in {directory}. Check your path!")
        return None

    for path in file_paths:
        filename = os.path.basename(path)
        t_on_match = re.search(r"output_(\d+)\.txt", filename)
        if not t_on_match:
            continue
        
        t_on_val = int(t_on_match.group(1))
        
        shot_data = {}
        nodes_seen = set()
        
        with open(path, 'r') as f:
            for line in f:
                match = log_pattern.search(line)
                if match:
                    blobs = int(match.group(1))
                    node_id = int(match.group(2))
                    shot_id = int(match.group(3))
                    
                    nodes_seen.add(node_id)
                    if shot_id not in shot_data:
                        shot_data[shot_id] = {}
                    shot_data[shot_id][node_id] = blobs
        
        if not shot_data:
            continue
            
        num_nodes = len(nodes_seen)
        total_shots = len(shot_data)
        global_hits = 0
        
        for shot_id, nodes in shot_data.items():
            if len(nodes) == num_nodes and all(count > 0 for count in nodes.values()):
                global_hits += 1
        
        hit_rate = (global_hits / total_shots) * 100
        sweep_stats[t_on_val] = hit_rate

    return sweep_stats

def plot_sweep_graph(sweep_stats):
    if not sweep_stats:
        return

    miss_color = '#e74c3c'
    hit_color = '#2ecc71'

    sorted_t = sorted(sweep_stats.keys())
    hit_rates = [sweep_stats[t] for t in sorted_t]
    miss_rates = [100 - hr for hr in hit_rates]
    
    fig, ax = plt.subplots(figsize=(12, 7))
    bar_width = (sorted_t[1] - sorted_t[0]) * 0.8 if len(sorted_t) > 1 else 400
    bars_hits = ax.bar(sorted_t, hit_rates, color=hit_color, edgecolor='white', 
                       width=bar_width, label='Global Hit')
    bars_misses = ax.bar(sorted_t, miss_rates, bottom=hit_rates, color=miss_color, 
                         edgecolor='white', width=bar_width, label='Global Miss')

    ax.set_xlabel('LED On-Time ($t_{on}$) [$\mu s$]', fontsize=12)
    ax.set_ylabel('Hit-Miss Rates (%)', fontsize=12)
    ax.set_title('Synchrony Quality Time Sweep', fontsize=14, pad=20)
    ax.set_xticks(sorted_t)
    ax.set_xticklabels(sorted_t, rotation=45)
    ax.set_ylim(0, 105)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=2)
    
    for i, hr in enumerate(hit_rates):
        ax.text(sorted_t[i], hr/2 if hr > 10 else hr + 5, f"{hr:.1f}%", 
                ha='center', va='center', color='white' if hr > 10 else 'white', 
                fontweight='bold', fontsize=9)

    plt.tight_layout()
    plt.show()

results = parse_sweep_results('outputs')
plot_sweep_graph(results)