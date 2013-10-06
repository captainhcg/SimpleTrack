#!/usr/bin/env python
import os
import commands
import time
from optparse import OptionParser
from parser import NodeParser


def execute(cmd, seperator=None):
    """execute command"""
    # return a list if seperator is provided
    # otherwise return a string
    cmd_status, cmd_output = commands.getstatusoutput(cmd)
    if cmd_status % 256 != 0:
        raise Exception("%s: signal: %s" (cmd_output, cmd_status))
    else:
        if seperator is None:
            return cmd_output
        else:
            return cmd_output.split(seperator)


def compare_versions(file, v1, v2, start_line, end_line):
    """compare code sections"""
    # file: relative path to git repo
    # v1 and v2: commit, hash
    # start_line, end_line: denote the code section in v1 
    cmd = "git diff %s %s %s | grep -o '@@ [-+]\w*,\w*' | grep -o '\w*,\w*'" % (v1, v2, file)
    for pair in execute(cmd, '\n'):
        if not pair:
            continue
        change = pair.split(",")
        altered_start_line = int(change[0])
        altered_end_line = int(change[1]) + altered_start_line
        if (start_line-altered_end_line)*(end_line-altered_start_line) <= 0:
            # the code section in v1 is changed in v2
            return True
    return False


def get_history(revisions, file_name, class_name="", function_name=""):
    """get a list of code sections that given code section is changed"""
    current_code = None
    last_revision = None
    codes = []
    start_time = time.time()
    terminated = False
    for r in revisions:
        # time out in 3 seconds
        if time.time() - start_time > 3.0:
            terminated = True
            break
        if last_revision is None:
            last_revision = r
            current_code = Code(r, class_name=class_name, function_name=function_name)
        else:
            changed = compare_versions(file_name, current_code.revision.hash, r.hash, current_code.start_line or 1, current_code.end_line or 65535)
            if changed:
                this_code = Code(r, class_name=class_name, function_name=function_name)
                if this_code.get_source_code() != current_code.get_source_code():
                    codes.append(Code(last_revision, class_name=class_name, function_name=function_name))
                    current_code = this_code
            last_revision = r
        if len(codes) >= 20:
            terminated = True
            break
    if not terminated and last_revision:
        if (codes and last_revision.hash != codes[-1].revision.hash) or not codes:
            codes.append(Code(last_revision, class_name=class_name, function_name=function_name))

    return codes


def get_code_revisions(project_path, file_name, class_name="", function_name=""):
    """get the revision list of given file"""
    os.chdir(project_path)
    revisions = []
    cmd = """git rev-list --abbrev-commit --date="short" --pretty=format:"date %ad%nauthor %an%nsubject %s%n" HEAD """ + file_name
    revs_data = execute(cmd, "\n")
    revs_list = []
    data = {}
    for line in revs_data:
        if not line:
            r = Revision(hash=data['commit'], file_name=file_name)
            for k, v in data.items():
                setattr(r, k, v)
            revs_list.append(r)
            data = {}
        else:
            info = line.split(" ", 1)
            data[info[0]] = info[1]
    return get_history(revs_list, file_name, class_name=class_name, function_name=function_name)


class Revision(object):
    """revision of file"""
    def __init__(self, hash="", file_name=""):
        self.hash = hash
        self.file_name = file_name
        self.author = ""
        self.date = ""
        self.subject = ""

    @property
    def code(self):
        if not hasattr(self, "_code"):
            try:
                self._code = execute('git show %s:%s' % (self.hash, self.file_name))
            except Exception as e:
                print e
                self._code = None
        return self._code

    def as_dict(self):
        return {
            "author": self.author,
            "date": self.date,
            "subject": self.subject,
            "hash": self.commit
        }


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

    def as_dict(self):
        return {
            "hash": self.revision.hash,
            "code": self.get_source_code(),
            "start_line": self.start_line, 
            "end_line": self.end_line,
        }

    def parse_code(self):
        assert self.revision, "No revision provided"
        try:
            np = NodeParser(self.revision.code, self.class_name, self.function_name)
            self.start_line = np.start_line
            self.end_line = np.end_line
            self.source_code_list = np.source_code_list
        except SyntaxError:
            self.start_line = 0
            self.end_line = 0
            self.source_code_list = []
 
    def get_source_code(self):
        if not hasattr(self, "_code"):
            if not self.start_line or not self.end_line:
                self._code = None
            else:
                code = self.source_code_list[self.start_line: self.end_line+1]
                self._code = "".join(code)
        return self._code


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-r", "--rootpath", dest="root_path", default=".")
    parser.add_option("-f", "--function", dest="function_name", default="")
    parser.add_option("-c", "--class", dest="class_name", default="")

    options, args = parser.parse_args()

    root_path = '/Users/che/Documents/drchrono-web/'
    # for debug only
    args = ["chronometer/models_base.py"]
    file_name = args[0]
    # options.function_name = "validate"
    class_name = options.class_name = ""
    function_name = options.function_name = "getAllAppointmentsinTimeRange"
    get_code_revisions(root_path, file_name, class_name, function_name)

    if len(args) == 0:
        raise Exception("File name is required!")
    if not options.class_name and not options.function_name:
        raise Exception("Function or Class is required!")

    # readFile(file_name=args[0], class_name=options.class_name, function_name=options.function_name)
