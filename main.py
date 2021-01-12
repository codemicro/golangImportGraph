import re
import os
import networkx as nx
import matplotlib.pyplot as plt
import argparse

parser = argparse.ArgumentParser(description="Generate an import graph of the internal import of some Go code")
parser.add_argument('scanDir', metavar='inputDirectory', type=str, help='directory to scan')
parser.add_argument('-o', dest='outputFile', default=None, help='name of the output file')

args = parser.parse_args()
OUTPUT_FILE = args.outputFile
SCAN_DIR = args.scanDir

print("Discovering files...")

files = []
for r, d, f in os.walk(SCAN_DIR):
    for fname in f:
        if '.go' in fname:
            files.append(os.path.join(r, fname))

import_regex = r"import ?\((.*?)\)"
module_regex = r"module ?(.*)"

print("Searching for go.mod...")

try:
    with open(os.path.join(SCAN_DIR, "go.mod"), encoding="utf8") as f:
        r = re.findall(module_regex, f.read(), re.MULTILINE)
        if len(r) != 0:
            BASE_PACKAGE = r[0]
except FileNotFoundError:
    pass
finally:
    if BASE_PACKAGE == "":
        BASE_PACKAGE = input("Input module name: ").strip()

package_regex = re.compile(BASE_PACKAGE.replace(".", "\.") + r"(.*)")

all_packages = []
imports_dict = {}

for fname in files:

    f = open(fname, encoding="utf8")

    fname = fname.replace(SCAN_DIR, "")
    print(f"Scanning file {fname}... ")

    current_package_name = fname.replace(os.path.sep, "/")
    current_package_name = "/".join(current_package_name.split("/")[:-1])

    matches = re.findall(import_regex, f.read(), re.DOTALL)
    if len(matches) == 0:
        # No imports section found
        pass
    else:
        # Extract import block
        import_statements = matches[0].strip().split("\n")
        for index, statement in enumerate(import_statements):
            # Make a list of import statements without quotes
            import_statements[index] = statement.strip().replace("\"", "")

        # internal_import_statements will be a list of packages that the current file imports
        internal_import_statements = []

        # Filter by imports that are from the current project
        for statement in import_statements:
            v = package_regex.findall(statement)
            if len(v) != 0:
                internal_import_statements.append(v[0])

        if current_package_name in imports_dict:
            for s in internal_import_statements:
                imports_dict[current_package_name] = imports_dict[current_package_name] + internal_import_statements
        else:
            imports_dict[current_package_name] = internal_import_statements

    if current_package_name not in all_packages:
        all_packages.append(current_package_name)

    f.close()

print("Generating graph...")
# Generate graph
edge_list = []
for key in imports_dict:
    for ims in imports_dict[key]:
        edge_list.append((key, ims))

red_nodes = []
other_nodes = []
for key in all_packages:
    if "cmd" in key and key not in red_nodes:
        red_nodes.append(key)
    elif key not in other_nodes:
        other_nodes.append(key)

graph = nx.DiGraph() # Directional graph
graph.add_edges_from(edge_list)
pos = nx.kamada_kawai_layout(graph)
nx.draw_networkx_nodes(graph, pos, nodelist=other_nodes)
nx.draw_networkx_nodes(graph, pos, nodelist=red_nodes, node_color="r")
nx.draw_networkx_labels(graph, pos)
nx.draw_networkx_edges(graph, pos, edgelist=graph.edges(), arrows=True, arrowstyle="-|>")
if OUTPUT_FILE is None:
    plt.show()
else:
    print(f"Saving to {OUTPUT_FILE}...")
    plt.savefig(OUTPUT_FILE)
