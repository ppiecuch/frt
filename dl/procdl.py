#! /usr/bin/python

# procdl.py
#
# FRT - A Godot platform targeting single board computers
# Copyright (c) 2017  Emanuele Fornara
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

import re


def parse_dl(dl, suffix):
    libname = "unnamed"
    head = ""
    symbols = []
    types = []
    includes = []
    f_dl = open(dl, "r")
    for line in f_dl.readlines():
        line = line.replace("\n", "")
        if libname == "unnamed":
            m = re.search(r"^//\s*(.*)\.dl\s*$", line)
            if m:
                libname = m.group(1)
                head += "// " + libname + suffix
                head += " - File generated by procdl.py - DO NOT EDIT\n"
                continue
        m = re.search(r"^.*___(.*)___.*$", line)
        if not m:
            if re.search(r"^#include", line):
                includes.append(line)
            else:
                head += line + "\n"
            continue
        s = m.group(1)
        symbols.append(s)
        ls = libname + "_" + s
        types.append(line.replace("___" + s + "___", "FRT_FN_" + ls))
    f_dl.close()
    return (libname, head, symbols, types, includes)


def build_h(dl, h):
    libname, head, symbols, types, includes = parse_dl(dl, ".gen.h")
    f = open(h, "w")
    f.write(head)

    def out(s=None):
        if s:
            f.write(s)
        f.write("\n")

    out("#ifndef FRT_DL_SKIP")
    for s in includes:
        out(s)
    out()
    for s in types:
        out(s)
    out()
    for s in symbols:
        ls = libname + "_" + s
        out("#define " + s + " frt_fn_" + ls)
    out()
    for s in symbols:
        ls = libname + "_" + s
        out("extern FRT_FN_" + ls + " frt_fn_" + ls + ";")
    out()
    out("#endif")
    out("extern bool frt_load_" + libname + "(const char *filename);")
    f.close()


def build_cpp(dl, cpp):
    libname, head, symbols, types, includes = parse_dl(dl, ".gen.cpp")
    f = open(cpp, "w")
    f.write(head)
    assignments = ""
    for s in symbols:
        ls = libname + "_" + s
        assignments += "FRT_FN_" + ls + " frt_fn_" + ls + " = 0;\n"
    resolutions = ""
    for s in symbols:
        ls = libname + "_" + s
        resolutions += "\tfrt_fn_" + ls + " = (FRT_FN_" + ls + ")"
        resolutions += 'dlsym(lib, "' + s + '");\n'
    f.write(
        """\
#include "%(libname)s.gen.h"

#include <stdio.h>

#include <dlfcn.h>

static void *lib = 0;

%(assignments)s

bool frt_load_%(libname)s(const char *filename) {
	if (lib)
		return true;
	lib = dlopen(filename, RTLD_LAZY);
	if (!lib) {
		fprintf(stderr, "frt: dlopen failed for '%%s'.\\n", filename);
		return false;
	}
%(resolutions)s
	return true;
}
"""
        % {"libname": libname, "assignments": assignments[:-1], "resolutions": resolutions[:-1]}
    )
    f.close()


def build_cpp_action(target, source, env):
    build_cpp(str(source[0]), str(target[0]))


def build_h_action(target, source, env):
    build_h(str(source[0]), str(target[0]))


if __name__ == "__main__":
    import sys

    for s in sys.argv[1:]:
        sys.stdout.write("Processing " + s + "... ")
        build_cpp(s, s.replace(".dl", ".gen.cpp"))
        build_h(s, s.replace(".dl", ".gen.h"))
        sys.stdout.write("done.\n")
