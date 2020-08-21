#!/usr/bin/env python

import os
import sys
import csv
import random
import readline

if sys.version_info.major == 2:
    prompt = raw_input
else:
    prompt = input

COMMANDS = ["a", "add", "+",
            "r", "rm", "del", "-",
            "l", "ll",
            "u", "up", "d", "down",
            "t", "top", "b", "bot", "bottom"]

# Exceptions

class ToDoException(Exception):
    pass

class NoSuchProject(ToDoException):
    proj = ""

    def __init__(self, proj):
        self.proj = proj

    def __str__(self):
        if self.proj:
            return "Project `{}' does not exist.".format(self.proj)
        else:
            return "No project specified."

class NoSuchEntry(ToDoException):
    proj = ""
    entry = None

    def __init__(self, proj, entry):
        self.proj = proj
        self.entry = entry

    def __str__(self):
        return "Project `{}' does not have entry #{}.".format(self.proj, self.entry)

class BadIndex(ToDoException):
    v = ""

    def __init__(self, v):
        self.v = v

    def __str__(self):
        return "`{}' is not a valid index.".format(self.v)

class BadSyntax(ToDoException):
    msg = ""

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg

# Utils

def safeIndex(v, proj, entries):
    try:
        idx = int(v) - 1
    except ValueError:
        raise BadIndex(v)
    if idx < 0 or idx >= len(entries):
        raise NoSuchEntry(proj, idx + 1)
    return idx

# Command
            
class Command(object):
    command = ""
    project = ""
    args = []

    def __init__(self):
        self.args = []

    def write(self, out):
        out.write("{} / {} / {}\n".format(self.command, self.project, " ".join(self.args)))
        
class Entry(object):
    project = ""
    key = ""
    description = ""

    def __init__(self, project, key, description):
        self.project = project
        self.key = key
        self.description = description

    def write(self, out):
        out.write("{}\t{}\t{}\n".format(self.project, self.key, self.description))

class Manager(object):
    projfile = "todo.txt"
    projects = []
    projentries = {}

    _save = False                # Set to True if entries are modified
    _tododir = ""
    _debug = False
    _color = True

    def __init__(self, projfile):
        self.projfile = projfile
        self._tododir = os.path.split(projfile)[0]

    def write(self, s):
        sys.stdout.write(s)

    def red(self, s):
        if self._color:
            self.write('\x1b[31;1m' + s + '\x1b[m')
        else:
            self.write(s)

    def yellow(self, s):
        if self._color:
            self.write('\x1b[33;1m' + s + '\x1b[m')
        else:
            self.write(s)

    def loadProjects(self):
        self.projects = []
        self.projentries = {}
        if os.path.isfile(self.projfile):
            with open(self.projfile, "r") as f:
                c = csv.reader(f, delimiter='\t')
                for line in c:
                    proj = line[0]
                    if proj not in self.projects:
                        self.projects.append(proj)
                        self.projentries[proj] = []
                    e = Entry(line[0], line[1], line[2])
                    self.projentries[proj].append(e)
        self.projects.sort()

    def saveProjects(self):
        with open(self.projfile, "w") as out:
            for proj in self.projects:
                for e in self.projentries[proj]:
                    e.write(out)

    def getEntries(self, project):
        if project in self.projects:
            return self.projentries[project]
        else:
            raise NoSuchProject(project)

    def parseCommand(self, args):
        """Parse the command line `args' and return a Command object."""
        cmd = Command()
        for a in args:
            # Special case: +PROJ => + PROJ
            if len(a) > 1 and a[0] in "+-":
                cmd.command = a[0]
                cmd.project = a[1:]
            elif a in COMMANDS and not cmd.command:
                cmd.command = a
            elif a in self.projects and not cmd.project:
                cmd.project = a
            else:
                cmd.args.append(a)

        # Special case: no command => l
        if not cmd.command:
            if cmd.project:
                cmd.command = "ll"
            else:
                cmd.command = "l"
        # Special case: + with a non-existing project
        elif cmd.command == "+" and not cmd.project:
            cmd.project = cmd.args[0]
            cmd.args = cmd.args[1:]
        return cmd
                
    def showProjectEntries(self, p):
        self.yellow(p + "\n")
        i = 1
        for e in self.projentries[p]:
            sys.stdout.write("  {}. {}\n".format(i, e.description))
            i += 1
        sys.stdout.write("\n")

    def listProjects(self, cmd, short=True):
        wanted = self.projects
        if cmd.project:
            args = [cmd.project] + cmd.args
            wanted = [ w for w in args if w in self.projects ]

        for p in wanted:
            if short:
                sys.stdout.write("{} ({})\n".format(p, len(self.projentries[p])))
            else:
                self.showProjectEntries(p)

    def showProject(self, proj):
        if proj in self.projects:
            self.showProjectEntries(proj)
        else:
            self.red("Error: no project called `{}'.\n".format(proj))

    def addEntry(self, cmd):
        """Add entry `description' to project `proj'. The project is created if it does not exist."""
        proj = cmd.project
        description = " ".join(cmd.args)
        key = str(random.random())[2:]
        e = Entry(proj, key, description)
        if proj not in self.projects:
            self.projects.append(proj)
            self.projentries[proj] = []
        self.projentries[proj].append(e)
        self._save = True

    def deleteEntry(self, cmd):
        if not cmd.args:
            raise BadSyntax("Entry index missing.")
        if cmd.project:
            entries = self.getEntries(cmd.project)
            fromidx = safeIndex(cmd.args[0], cmd.project, entries)
            e = entries[fromidx]
            entries.remove(e)
            sys.stdout.write("Removed from project {}:\n  {}\n".format(cmd.project, e.description))
            self._save = True
        else:
            raise NoSuchProject('')

    def raiseEntry(self, cmd, top=False):
        if not cmd.args:
            raise BadSyntax("Entry index missing.")
        if cmd.project:
            entries = self.getEntries(cmd.project)
            fromidx = safeIndex(cmd.args[0], cmd.project, entries)
            if len(cmd.args) > 1:
                toidx = safeIndex(cmd.args[1], cmd.project, entries)
            elif top:
                toidx = 0
            else:
                toidx = max(fromidx - 1, 0)
            e = entries[fromidx]
            entries.remove(e)
            entries[toidx:toidx] = [e]
            self.showProjectEntries(cmd.project)
            self._save = True
        else:
            raise NoSuchProject('')

    def lowerEntry(self, cmd, bottom=False):
        if not cmd.args:
            raise BadSyntax("Entry index missing.")
        if cmd.project:
            entries = self.getEntries(cmd.project)
            fromidx = safeIndex(cmd.args[0], cmd.project, entries)
            if len(cmd.args) > 1:
                toidx = safeIndex(cmd.args[1], cmd.project, entries)
            elif bottom:
                toidx = len(entries) - 1
            else:
                toidx = min(fromidx + 1, len(entries) - 1)
            e = entries[fromidx]
            entries.remove(e)
            entries[toidx:toidx] = [e]
            self.showProjectEntries(cmd.project)
            self._save = True
        else:
            raise NoSuchProject('')

    def main(self, args):
        self.loadProjects()
        cmd = self.parseCommand(args)
        if self._debug:
            cmd.write(sys.stdout)
        
        if cmd.command == "l":
            self.listProjects(cmd)
        elif cmd.command == "ll":
            self.listProjects(cmd, short=False)
        elif cmd.command in ["a", "+", "add"]:
            self.addEntry(cmd)
        elif cmd.command in ["rm", "del", "-"]:
            self.deleteEntry(cmd)
        elif cmd.command in ["u", "up"]:
            self.raiseEntry(cmd)
        elif cmd.command in ["d", "down"]:
            self.lowerEntry(cmd)
        elif cmd.command in ["t", "top"]:
            self.raiseEntry(cmd, top=True)
        elif cmd.command in ["b", "bot", "bottom"]:
            self.lowerEntry(cmd, bottom=True)
            
        if self._save:
            self.saveProjects()

    def mainLoop(self):
        while True:
            try:
                cmdline = prompt("=> ")
            except EOFError:
                sys.stdout.write("\n")
                break
            if not cmdline:
                continue
            words = cmdline.split()
            if words[0] in 'qQ':
                break
            try:
                self.main(words)
            except ToDoException as e:
                self.red("ERROR: " + str(e) + "\n")

if __name__ == "__main__":
    prog = sys.argv[0]
    args = sys.argv[1:]
    projfile = os.getenv("TODOFILE") or os.path.split(prog)[0] + "todo.txt"
    M = Manager(projfile)
    M.editor = os.getenv("EDITOR") or "nano"
    if "-i" in args:
        M.mainLoop()
    else:
        try:
            M.main(sys.argv[1:])
        except ToDoException as e:
            M.red("ERROR: " + str(e) + "\n")
            sys.exit(1)
