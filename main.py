import os
import shlex
import socket
import getpass
import signal
import re
import argparse
import csv
import base64
import platform

class VFSNode:
    def __init__(self, name, node_type="dir", mode="755", content=b""):
        self.name = name
        self.type = node_type
        self.mode = mode
        self.content = content
        self.children = {}

    def add_child(self, node):
        self.children[node.name] = node

class VFS:
    def __init__(self):
        self.root = VFSNode("/")
        self.cwd = self.root
        self.cwd_path = "/"

    def load_from_csv(self, path):
        with open(path, newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                self._add_path(row["path"], row["type"], row.get("mode", "755"), row.get("content", ""))

    def _add_path(self, path, node_type, mode, content):
        parts = [p for p in path.strip("/").split("/") if p]
        current = self.root
        for i, part in enumerate(parts):
            if part not in current.children:
                if i == len(parts) - 1:
                    if node_type == "file":
                        data = base64.b64decode(content) if content else b""
                        current.add_child(VFSNode(part, "file", mode, data))
                    else:
                        current.add_child(VFSNode(part, "dir", mode))
                else:
                    current.add_child(VFSNode(part, "dir"))
            current = current.children[part]

    def ensure_default(self):
        if not self.root.children:
            self._add_path("home/user/docs", "dir", "755", "")
            self._add_path("home/user/docs/readme.txt", "file", "644", base64.b64encode(b"Hello from VFS").decode())
            self._add_path("var/log/system.log", "file", "644", base64.b64encode(b"System initialized").decode())

    def ls(self):
        if self.cwd.type != "dir":
            return []
        return list(self.cwd.children.keys())

    def cd(self, path):
        if path == "/":
            self.cwd = self.root
            self.cwd_path = "/"
            return True
        parts = [p for p in path.strip("/").split("/") if p]
        if path.startswith("/"):
            current = self.root
            new_path = "/"
        else:
            current = self.cwd
            new_path = self.cwd_path
        for part in parts:
            if part == "..":
                if current != self.root:
                    current = self.root
                    new_path = "/"
            elif part in current.children and current.children[part].type == "dir":
                current = current.children[part]
                new_path = os.path.join(new_path, part)
            else:
                return False
        self.cwd = current
        self.cwd_path = new_path if new_path != "" else "/"
        return True

def build_prompt(vfs: VFS) -> str:
    user = getpass.getuser()
    host = socket.gethostname().split('.')[0]
    return f"{user}@{host}:{vfs.cwd_path}$ "

var_pattern = re.compile(r'\$([A-Za-z_][A-Za-z0-9_]*)|\$\{([A-Za-z_][A-Za-z0-9_]*)\}')

def expand_vars_preserving_quotes(s: str, env: dict) -> str:
    out_chars = []
    i = 0
    n = len(s)
    in_single = False
    in_double = False
    while i < n:
        c = s[i]
        if c == "'" and not in_double:
            in_single = not in_single
            out_chars.append(c)
            i += 1
            continue
        if c == '"' and not in_single:
            in_double = not in_double
            out_chars.append(c)
            i += 1
            continue
        if c == '\\':
            if i + 1 < n:
                out_chars.append(s[i+1])
                i += 2
            else:
                i += 1
            continue
        if c == '$' and not in_single:
            if i+1 < n and s[i+1] == '{':
                j = i+2
                varname = []
                while j < n and re.match(r'[A-Za-z0-9_]', s[j]):
                    varname.append(s[j]); j += 1
                if j < n and s[j] == '}':
                    name = ''.join(varname)
                    val = env.get(name, '')
                    out_chars.append(val)
                    i = j + 1
                    continue
                else:
                    out_chars.append('$')
                    i += 1
                    continue
            else:
                j = i+1
                varname = []
                while j < n and re.match(r'[A-Za-z0-9_]', s[j]):
                    varname.append(s[j]); j += 1
                if varname:
                    name = ''.join(varname)
                    val = env.get(name, '')
                    out_chars.append(val)
                    i = j
                    continue
                else:
                    out_chars.append('$')
                    i += 1
                    continue
        else:
            out_chars.append(c)
            i += 1
    return ''.join(out_chars)

def parse_command(line: str, env: dict):
    expanded = expand_vars_preserving_quotes(line, env)
    return shlex.split(expanded)

def handle_command(tokens, vfs: VFS):
    if not tokens:
        return True
    cmd = tokens[0]
    args = tokens[1:]
    if cmd == 'exit':
        print("exit")
        return False
    elif cmd == 'ls':
        items = vfs.ls()
        print(" ".join(items))
    elif cmd == 'cd':
        target = args[0] if args else "/"
        if not vfs.cd(target):
            print(f"cd: {target}: Нет такого каталога")
    elif cmd == 'echo':
        print(" ".join(args))
    elif cmd == 'head':
        if not args:
            print("head: требуется имя файла")
        else:
            fname = args[0]
            if fname in vfs.cwd.children and vfs.cwd.children[fname].type == 'file':
                content = vfs.cwd.children[fname].content.decode(errors='ignore')
                lines = content.splitlines()[:10]
                print('\n'.join(lines))
            else:
                print(f"head: {fname}: Нет такого файла")
    elif cmd == 'whoami':
        print(getpass.getuser())
    elif cmd == 'uname':
        print(platform.system())
    else:
        print(f"Команда не найдена: {cmd}")
    return True

def on_sigint(signum, frame):
    print("\n(Для выхода наберите 'exit')")

def run_interactive(env, vfs: VFS):
    print("Эмулятор оболочки — Этап 4 (Основные команды). Для выхода: exit")
    while True:
        try:
            line = input(build_prompt(vfs))
        except EOFError:
            print()
            break
        if not line.strip():
            continue
        try:
            tokens = parse_command(line, env)
        except ValueError as e:
            print(f"Ошибка: {e}")
            continue
        if not handle_command(tokens, vfs):
            break

def run_script(path, env, vfs: VFS):
    try:
        with open(path, 'r') as f:
            for raw_line in f:
                line = raw_line.rstrip('\n')
                if not line.strip():
                    continue
                print(build_prompt(vfs) + line)
                try:
                    tokens = parse_command(line, env)
                except ValueError as e:
                    print(f"Ошибка: {e}")
                    continue
                if not handle_command(tokens, vfs):
                    break
    except Exception as e:
        print(f"Ошибка при выполнении скрипта {path}: {e}")

def main():
    signal.signal(signal.SIGINT, on_sigint)
    parser = argparse.ArgumentParser(description="Эмулятор оболочки — Этап 4. Основные команды")
    parser.add_argument("--vfs", type=str, help="Путь к CSV-файлу VFS", required=False)
    parser.add_argument("--script", type=str, help="Путь к стартовому скрипту", required=False)
    args = parser.parse_args()
    env = dict(os.environ)
    vfs = VFS()
    if args.vfs:
        try:
            vfs.load_from_csv(args.vfs)
        except Exception as e:
            print(f"[WARN] Ошибка загрузки VFS из {args.vfs}: {e}. Используется дефолтная VFS.")
            vfs.ensure_default()
    else:
        vfs.ensure_default()
    print("[DEBUG] Параметры запуска:")
    print(f"  VFS path: {args.vfs}")
    print(f"  Script path: {args.script}")
    if args.script:
        run_script(args.script, env, vfs)
    else:
        run_interactive(env, vfs)

if __name__ == '__main__':
    main()