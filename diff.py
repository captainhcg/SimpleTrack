#!/usr/bin/env python
import os
import sys
import re
import commands
from optparse import OptionParser
from parser import NodeParser
import difflib


def execute(cmd, seperator=None):
    cmd_status, cmd_output = commands.getstatusoutput(cmd)
    if cmd_status != 0:
        raise Exception(cmd_output)
    else:
        if seperator is None:
            return cmd_output
        else:
            return cmd_output.split(seperator)


def get_revisions(file_name):
    """get the revision list of given file"""
    revs = execute('git rev-list HEAD %s' % file_name, "\n")
    return revs


def compare_versions(v1, v2, start_line, end_line):
    pattern = re.compile("^@@ [+-](?P<start_line>\d+),(?P<length>\d+) [+-]\d+,\d+ @@?")
    for l in difflib.unified_diff(v1.split("\n"), v2.split("\n")):
        if l.startswith("@@") and l.endswith("@@\n"):
            m = pattern.match(l)
            if m:
                altered_start_line = int(m.group('start_line'))
                altered_end_line = int(m.group('length'))
                if (start_line-altered_start_line)*(end_line-altered_end_line) < 0:
                    return True
    return False


def get_history(revisions, file_name, class_name="", function_name=""):
    """get a list of code sections that given code section is changed"""
    last_version = None
    codes = []
    for r in revisions:
        if last_version is None:
            last_version = Code(r, class_name=class_name, function_name=function_name)
            codes.append(last_version)
        else:
            changed = compare_versions(last_version.revision.code, r.code, last_version.start_line, last_version.end_line)
            if changed:
                last_version = Code(r, class_name=class_name, function_name=function_name)
                codes.append(last_version)
    return codes


def get_code_revisions(project_path, file_name, class_name="", function_name=""):
    os.chdir(project_path)
    revisions = []
    for rev in get_revisions(file_name):
        revisions.append(Revision(commit=rev, file_name=file_name))

    return get_history(revisions, file_name, class_name=options.class_name, function_name="clean")


class Revision(object):
    """revision of file"""
    def __init__(self, commit="", file_name=""):
        self.commit = commit
        self.file_name = file_name

    @property
    def code(self):
        if not hasattr(self, "_code"):
            self._code = execute('git show %s:%s' % (self.commit, self.file_name))
        return self._code


class Code(object):
    """Code section (function/class)"""
    def __init__(self, revision, class_name="", function_name=""):
        self.revision = revision
        self.class_name = class_name
        self.function_name = function_name
        self.start_line = None
        self.end_line = None
        if self.revision:
            self.parse_code()

    def parse_code(self):
        assert self.revision, "No revision provided"
        np = NodeParser(self.revision.code, self.class_name, self.function_name)
        self.start_line = np.start_line
        self.end_line = np.end_line
        self.source_code_list = np.source_code_list

    def get_source_code(self):
        if not self.start_line or not self.end_line:
            return None
        code = self.source_code_list[self.start_line: self.end_line+1]
        return "".join(code)

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-r", "--rootpath", dest="root_path", default=".")
    parser.add_option("-f", "--function", dest="function_name", default="")
    parser.add_option("-c", "--class", dest="class_name", default="")

    options, args = parser.parse_args()

    root_path = '/home/ec2-user/django'
    # for debug only
    args = ["django/forms/fields.py"]
    file_name = args[0]
    # options.function_name = "validate"
    class_name = options.class_name = "MultiValueField"
    function_name = options.function_name

    print len(get_code_revisions(root_path, file_name, class_name="MultiValueField", function_name="clean"))

    if len(args) == 0:
        raise Exception("File name is required!")
    if not options.class_name and not options.function_name:
        raise Exception("Function or Class is required!")

    # readFile(file_name=args[0], class_name=options.class_name, function_name=options.function_name)
