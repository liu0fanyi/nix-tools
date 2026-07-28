"""Small helpers shared by isolated deployment tests."""


def replace_key(text: str, section: str, key: str, value: str) -> str:
    lines = text.splitlines()
    current = ""
    for index, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped[1:-1]
        elif current == section and stripped.startswith(f"{key} ="):
            lines[index] = f"{key} = {value}"
            return "\n".join(lines) + "\n"
    raise RuntimeError(f"unable to replace [{section}].{key} in instance config")
