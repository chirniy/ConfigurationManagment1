import os
import shlex
import socket
import getpass
import signal
import re
import sys
import argparse

def build_prompt() -> str:
    user = getpass.getuser()
    host = socket.gethostname().split('.')[0]
    cwd = os.getcwd()
    home = os.path.expanduser('~')
    if cwd == home:
        display_cwd = '~'
    elif cwd.startswith(home + os.sep):
        display_cwd = '~' + cwd[len(home):]
    else:
        display_cwd = cwd
    return f"{user}@{host}:{display_cwd}$ "

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
    try:
        expanded = expand_vars_preserving_quotes(line, env)
        tokens = shlex.split(expanded)
        return tokens
    except ValueError as e:
        raise ValueError(f"Синтаксическая ошибка в вводе: {e}")

def handle_command(tokens):
    if not tokens:
        return True
    cmd = tokens[0]
    args = tokens[1:]
    if cmd == 'exit':
        print("exit")
        return False
    elif cmd == 'ls':
        print(f"[stub] ls called with {len(args)} arg(s): {args}")
    elif cmd == 'cd':
        print(f"[stub] cd called with {len(args)} arg(s): {args}")
    else:
        print(f"Команда не найдена: {cmd}")
    return True

def on_sigint(signum, frame):
    print("\n(Для выхода наберите 'exit')")

def run_interactive(env):
    print("Эмулятор оболочки — Этап 2 (Конфигурация). Для выхода: exit")
    while True:
        try:
            line = input(build_prompt())
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
        if not handle_command(tokens):
            break

def run_script(path, env):
    try:
        with open(path, 'r') as f:
            for raw_line in f:
                line = raw_line.rstrip('\n')
                if not line.strip():
                    continue
                print(build_prompt() + line)
                try:
                    tokens = parse_command(line, env)
                except ValueError as e:
                    print(f"Ошибка: {e}")
                    continue
                if not handle_command(tokens):
                    break
    except Exception as e:
        print(f"Ошибка при выполнении скрипта {path}: {e}")

def main():
    signal.signal(signal.SIGINT, on_sigint)
    parser = argparse.ArgumentParser(description="Эмулятор оболочки — Этап 2. Конфигурация")
    parser.add_argument("--vfs", type=str, help="Путь к физическому расположению VFS", required=False)
    parser.add_argument("--script", type=str, help="Путь к стартовому скрипту", required=False)
    args = parser.parse_args()
    env = dict(os.environ)
    print("[DEBUG] Параметры запуска:")
    print(f"  VFS path: {args.vfs}")
    print(f"  Script path: {args.script}")
    if args.script:
        run_script(args.script, env)
    else:
        run_interactive(env)

if __name__ == '__main__':
    main()