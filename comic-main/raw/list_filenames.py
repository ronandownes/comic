import os

script_dir = os.path.dirname(os.path.abspath(__file__))
folder_name = os.path.basename(script_dir)
output_file = os.path.join(script_dir, f"{folder_name}_filenames.txt")

filenames = sorted(os.listdir(script_dir))

with open(output_file, "w") as f:
    for name in filenames:
        f.write(name + "\n")

print(f"Wrote {len(filenames)} filenames to {output_file}")
