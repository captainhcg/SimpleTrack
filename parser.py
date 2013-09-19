#!/usr/bin/env python
import sys

import traceback
import re
import ast
import os
import os.path
from optparse import OptionParser


class NodeParser(ast.NodeVisitor):

    def __init__(self, file, code_list, function_name="", class_name=""):
        self._file = file
        self.source_code = code_list
        self.source_code_len = len(code_list)-1
        self.lines_depth = [65535] * (self.source_code_len+1)
        self.class_name = class_name
        self.function_name = function_name
        self.terminated = False
        self.start_line = None
        self.end_line = None

    def parse_root(self, f):
        tree = ast.parse(f.read())
        tree.depth = 0
        tree.class_name = ""
        self.visit(tree)

    def generic_visit(self, node):
        if self.terminated:
            return
        self.markLineDepth(node)
        depth = node.depth
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if self.continue_or_not(item, depth):
                        item.depth = depth+1
                        self.lines_depth[item.lineno] = depth
                        item.class_name = node.class_name
                        self.visit(item)
            elif self.continue_or_not(value, depth):
                value.depth = depth+1
                self.lines_depth[value.lineno] = depth
                value.class_name = node.class_name
                self.visit(value)

    def continue_or_not(self, x, depth):
        if not isinstance(x, ast.AST):
            return False
        if not hasattr(x, "lineno"):
            return False
        existing_depth = self.lines_depth[x.lineno]
        if existing_depth != 65535 and depth + 1 < existing_depth:
            return False
        return True

    def visit_ClassDef(self, node):
        if self.terminated:
            return
        node.class_name = node.name
        if self.class_name and not self.function_name and self.class_name == node.name:
            self.start_line = node.lineno
            self.end_line = self.getLastLine(node.lineno, node.depth)
            self.terminated = True
            return
        else:
            self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if self.terminated:
            return
        if not self.function_name:
            return
        if self.class_name and node.class_name != self.class_name:
            return
        if self.function_name == node.name:
            self.start_line = node.lineno
            self.end_line = self.getLastLine(node.lineno, node.depth)
            self.terminated = True
            return

    def getSourceCode(self):
        code = self.source_code[self.start_line: self.end_line+1]
        return "".join(code)

    def getLastLine(self, line_num, depth):
        end_line = line_num
        for idx in xrange(line_num+1, self.source_code_len+1):
            if self.lines_depth[idx] > depth:
                end_line = idx
            else:
                break
        for line in xrange(end_line, line_num, -1):
            if not self.source_code[end_line].strip(" \r\n\t"):
                end_line = line - 1
        return end_line

    def markLineDepth(self, item):
        if hasattr(item, "lineno"):
            self.lines_depth[item.lineno] = item.depth
        if hasattr(item, "body"):
            if not isinstance(item.body, list):
                self.lines_depth[item.body.lineno] = item.depth+1
            else:
                for node in item.body:
                    self.lines_depth[node.lineno] = item.depth+1


def readFile(file_name, function_name="", class_name=""):
    try:
        source_code = [""]
        with open(file_name, "r") as f1:
            for line in f1:
                source_code.append(line)
        with open(file_name, "r") as f2:
            node_parser = NodeParser(f2, source_code, function_name, class_name)
            node_parser.parse_root(f2)
            print node_parser.start_line, node_parser.end_line
            print node_parser.getSourceCode()
    except IOError as e:
        print e
        return {"success": False, "error": "Cannot open %s" % file_name}

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-f", "--function", dest="function_name", default="")
    parser.add_option("-c", "--class", dest="class_name", default="")
    options, args = parser.parse_args()

    # for debug only
    args = ["/home/ec2-user/django/django/forms/fields.py"]
    # options.function_name = "validate"
    options.class_name = "DecimalField"

    if len(args) == 0:
        raise Exception("File name is required!")
    if not options.class_name and not options.function_name:
        raise Exception("Function or Class is required!")

    readFile(file_name=args[0], class_name=options.class_name, function_name=options.function_name)
