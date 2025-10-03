import os
import shlex
import socket
import getpass
import signal
import re

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
        return
    cmd = tokens[0]
    args = tokens[1:]
    if cmd == 'exit':
        print("exit")
        raise SystemExit(0)
    elif cmd == 'ls':
        print(f"[stub] ls called with {len(args)} arg(s): {args}")
    elif cmd == 'cd':
        print(f"[stub] cd called with {len(args)} arg(s): {args}")
    else:
        print(f"Команда не найдена: {cmd}")

def on_sigint(signum, frame):
    print("\n(Для выхода наберите 'exit')")

def main():
    signal.signal(signal.SIGINT, on_sigint)
    env = dict(os.environ)
    prompt = build_prompt()
    print("Эмулятор оболочки — Этап 1 (REPL). Введите команды. Для выхода: exit")
    try:
        while True:
            try:
                prompt = build_prompt()
                line = input(prompt)
            except EOFError:
                print()
                break
            line_stripped = line.strip()
            if not line_stripped:
                continue
            try:
                tokens = parse_command(line, env)
            except ValueError as e:
                print(f"Ошибка: {e}")
                continue
            try:
                handle_command(tokens)
            except SystemExit:
                break
            except Exception as e:
                print(f"Внутренняя ошибка при выполнении команды: {e}")
    except KeyboardInterrupt:
        print("\nПрерывание. Завершение.")
    print("Bye.")

if __name__ == '__main__':
    main()