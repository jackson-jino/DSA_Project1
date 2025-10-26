import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from collections import defaultdict
import os

# -----------------------
# File paths
# -----------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "../data")
OUTPUT_DIR = os.path.join(BASE_DIR, "../output")

os.makedirs(OUTPUT_DIR, exist_ok=True)

STUDENTS_CSV = os.path.join(DATA_DIR, "students.csv")
CLASSROOMS_CSV = os.path.join(DATA_DIR, "classrooms.csv")
OUTPUT_CSV = os.path.join(OUTPUT_DIR, "seating_plan_proposed.csv")
PDF_OUTPUT = os.path.join(OUTPUT_DIR, "seating_plan_all_classrooms.pdf")

# -----------------------
# Step 1: Load CSV files
# -----------------------
students_df = pd.read_csv(STUDENTS_CSV, dtype=str).fillna("")
classrooms_df = pd.read_csv(CLASSROOMS_CSV, dtype=str).fillna("")

students = students_df.to_dict(orient='records')
classrooms = classrooms_df.to_dict(orient='records')

# -----------------------
# Step 2: User input
# -----------------------
while True:
    try:
        students_per_bench = int(input("Enter number of students per bench: "))
        if students_per_bench <= 0:
            raise ValueError
        break
    except ValueError:
        print("Invalid input. Enter a positive integer.")

# -----------------------
# Step 3: Build conflict graph
# -----------------------
G = nx.Graph()
for s in students:
    G.add_node(s['id'], name=s['name'], dept=s['department'], course=s['course'])

for i, s1 in enumerate(students):
    for j in range(i+1, len(students)):
        s2 = students[j]
        if s1['department'] == s2['department'] or s1['course'] == s2['course']:
            G.add_edge(s1['id'], s2['id'])

# -----------------------
# Step 4: Graph coloring
# -----------------------
def graph_coloring(graph):
    coloring = {}
    degrees = dict(graph.degree())
    nodes = sorted(graph.nodes(), key=lambda x: -degrees[x])

    for node in nodes:
        neighbor_colors = set(coloring.get(n) for n in graph.neighbors(node) if n in coloring)
        color = 0
        while color in neighbor_colors:
            color += 1
        coloring[node] = color
    return coloring

student_color = graph_coloring(G)

# -----------------------
# Step 5: Assign color groups to benches
# -----------------------
benches_list = []
for cls in classrooms:
    for i in range(int(cls['benches'])):
        benches_list.append({'classroom': cls['classroom'], 'bench_no': i+1, 'students': []})

color_groups = defaultdict(list)
for student_id, color in student_color.items():
    color_groups[color].append(student_id)

assignment = []
bench_index = 0
for color, students_ids in color_groups.items():
    for sid in students_ids:
        while len(benches_list[bench_index]['students']) >= students_per_bench:
            bench_index += 1
            if bench_index >= len(benches_list):
                print("Error: Not enough benches for this allocation.")
                exit()
        benches_list[bench_index]['students'].append(sid)
        s = next(stu for stu in students if stu['id'] == sid)
        assignment.append({
            'student_id': sid,
            'name': s['name'],
            'department': s['department'],
            'course': s['course'],
            'classroom': benches_list[bench_index]['classroom'],
            'bench_no': benches_list[bench_index]['bench_no']
        })

# -----------------------
# Step 6: Predictive alert system
# -----------------------
print("\n[INFO] Predictive conflict alerts:")
for bench in benches_list:
    bench_conflicts = 0
    ids = bench['students']
    for i in range(len(ids)):
        for j in range(i+1, len(ids)):
            if G.has_edge(ids[i], ids[j]):
                bench_conflicts += 1
    if bench_conflicts > 0:
        print(f"[ALERT] {bench['classroom']} Bench {bench['bench_no']} has {bench_conflicts} potential conflicts.")

# -----------------------
# Step 7: Save assignment CSV
# -----------------------
df_out = pd.DataFrame(assignment)
df_out.to_csv(OUTPUT_CSV, index=False)
print(f"\n[INFO] Seating plan saved as {OUTPUT_CSV}")

# -----------------------
# Step 8: Visualization to single PDF
# -----------------------
departments = list(set([s['department'] for s in students]))
dept_colors = {dept: plt.cm.tab20(i % 20) for i, dept in enumerate(departments)}

with PdfPages(PDF_OUTPUT) as pdf:
    for cls in classrooms:
        cls_name = cls['classroom']
        cls_benches = [b for b in benches_list if b['classroom'] == cls_name]
        fig, ax = plt.subplots(figsize=(10, len(cls_benches)))
        for i, bench in enumerate(cls_benches):
            for j, sid in enumerate(bench['students']):
                s = next(stu for stu in students if stu['id'] == sid)
                rect = plt.Rectangle((j, -i), 1, 1, color=dept_colors[s['department']], alpha=0.8)
                ax.add_patch(rect)
                label = f"{s['name']}\nID:{s['id']}\nDept:{s['department']}\nCourse:{s['course']}"
                ax.text(j + 0.5, -i + 0.5, label, ha='center', va='center', fontsize=6)
        ax.set_xlim(0, max(len(b['students']) for b in cls_benches) + 1)
        ax.set_ylim(-len(cls_benches), 1)
        ax.set_title(f"Classroom: {cls_name}")
        ax.axis('off')
        pdf.savefig(fig)
        plt.close(fig)

print(f"[INFO] Seating plan PDF saved to {PDF_OUTPUT}")