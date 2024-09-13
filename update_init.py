import os
import sys


def update_init_py(target_dir):
    init_file = os.path.join(target_dir, "__init__.py")

    # Skip if directory does not exist
    if not os.path.exists(target_dir):
        print(f"Skipping non-existent folder: {target_dir}")
        return

    # Get all Python files in the directory (excluding __init__.py)
    py_files = [
        f for f in os.listdir(target_dir) if f.endswith(".py") and f != "__init__.py"
    ]

    # Prepare import statements
    import_lines = []
    for py_file in py_files:
        module_name = py_file.replace(".py", "")
        import_lines.append(f"from .{module_name} import *")

    # Write to __init__.py
    with open(init_file, "w") as init_f:
        init_f.write("\n".join(import_lines) + "\n")

    print(f"Successfully updated {init_file}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python update_init.py <folder_path>")
        sys.exit(1)

    folder = sys.argv[1]
    update_init_py(folder)
