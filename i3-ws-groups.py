#!/bin/python3

import sys, subprocess, argparse
from pathlib import Path


USAGE = """
Usage: i3-ws-groups <command> [<arg>] [--instant]
Manages i3 workspace groups, keeping them in the file ~/.i3-ws-groups.
The file maintains a list of workspace groups with the first being the current

These are the commands used by the program:
    init                    Create basic .i3-ws-groups file with only 'default' group
    current                 Print current group 
    all                     Print all groups
    selector [--instant]    Open rofi to select the group to switch to
    set <group> [--instant] Set group
    ws-switch <workspace>   Switch to workspace.
                            Workspace name in format of order_no:workspace
                            will switch to order_no:<current group>:workspace.
                            Use order_no:const:workspace to switch to order_no:const:workspace
    ws-move <workspace>     Move focused window to workspace.
                            Workspace provided the same as ws-switch

Flags used by some commands:
    --instant               Switch to group before user switches workspace.
                            This flag being absent allows moving windows between groups
"""

GROUPS_FILE = str(Path.home()) + "/.i3-ws-groups"


def exit_i3_groups(status_code, group_file):
    if not group_file.closed:
        group_file.close()

    if status_code != 0:
        print(USAGE)

    exit(status_code)

def get_current_ws():
    i3_msg_proc = subprocess.Popen(["i3-msg", "-t", "get_workspaces"],
            stdout=subprocess.PIPE)
    i3_ws, _ = i3_msg_proc.communicate()
    i3_ws = i3_ws.decode().strip()

    try:
        jq_proc = subprocess.Popen(["jq", ".[] | select(.focused).name"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        current_ws, _ = jq_proc.communicate(input=i3_ws.encode())
        current_ws = current_ws.decode().strip()
    except:
        print("Could not use rofi. Maybe rofi is not installed?", file=sys.stderr)
        return None

    return current_ws[1:-1]

def set_group(group_file, new_group, current_group, instant):
    group_file.seek(0)
    lines = group_file.readlines()

    group_file.close()
    group_file = open(GROUPS_FILE, "w")

    group_file.write(new_group + "\n")
    for line in lines:
        if line != (new_group + "\n"):
            group_file.write(line)
    if instant:
        new_ws = get_current_ws()
        if new_ws == None:
            exit_i3_groups(1, group_file)
        new_ws = new_ws.replace(current_group, new_group)
        subprocess.Popen(["i3-msg", "workspace " + new_ws])

def main():
    argc = len(sys.argv)

    try:
        group_file = open(GROUPS_FILE, "r")
    except:
        print("Could not open i3 group file", file=sys.stderr)
        exit_i3_groups(1, group_file)

    group_file.seek(0)
    current_group = group_file.readline().strip()

    if argc == 1:
        exit_i3_groups(1, group_file)

    elif 1 < argc and argc < 6:
        if sys.argv[1] == "init":
            group_file.close()

            group_file = open(GROUPS_FILE, "w")
            group_file.write("default\n")

        elif sys.argv[1] == "current":
            print(current_group)

        elif sys.argv[1] == "all":
            group_file.seek(0)
            print(group_file.read(), end="")

        elif sys.argv[1] == "ws-switch":
            ws = sys.argv[2]
            if ws.find(":") == -1:
                print("Malformed workspace name. Must be format of <num>:<ws> or <num>:<group>:<ws>", file=sys.stderr)
                exit_i3_groups(1, group_file)
            prefix = ws[:ws.find(":")] + ":"
            ws = ws.removeprefix(prefix)
            if ws.find(":") != -1:
                subprocess.Popen(["i3-msg", "workspace" + prefix + ws])
            else:
                subprocess.Popen(["i3-msg", "workspace" + prefix + current_group + ":" + ws])

        elif sys.argv[1] == "ws-move":
            ws = sys.argv[2]
            if ws.find(":") == -1:
                print("Malformed workspace name. Must be format of <num>:<ws> or <num>:<group>:<ws>", file=sys.stderr)
                exit_i3_groups(1, group_file)
            prefix = ws[:ws.find(":")] + ":"
            ws = ws.removeprefix(prefix)
            if ws.find(":") != -1:
                subprocess.Popen(["i3-msg", "move container to workspace " + prefix + ws])
            else:
                subprocess.Popen(["i3-msg", "move container to workspace " + prefix + current_group + ":" + ws])

        elif sys.argv[1] == "selector":
            group_file.seek(0)
            groups = group_file.read() # get all groups but current
            groups = groups[groups.find('\n') + 1:] # remove first group
            try:
                proc = subprocess.Popen(["rofi", "-dmenu", "-p", "Workspace group"],
                        stdout=subprocess.PIPE, stdin=subprocess.PIPE)
                new_group, _ = proc.communicate(input=groups.encode())
                new_group = new_group.decode().strip()
                if new_group != "":
                    set_group(group_file, new_group, current_group, argc == 3 and sys.argv[2] == "--instant")
            except:
                print("Could not use rofi. Maybe rofi is not installed?", file=sys.stderr)
                exit_i3_groups(1, group_file)

        elif sys.argv[1] == "set":
            set_group(group_file, sys.argv[2], current_group, sys.argv[3] == "--instant")

        else:
            exit_i3_groups(1, group_file)
    else:
        exit_i3_groups(1, group_file)

    exit_i3_groups(0, group_file)


if __name__ == "__main__":
    main()
