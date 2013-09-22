#!/usr/bin/env python
import traceback
import ast
from optparse import OptionParser
import StringIO


class NodeParser(ast.NodeVisitor):

    def __init__(self, source_code="", class_name="", function_name=""):
        self.source_code = source_code
        # insert a blank line in order to avoid index +1/-1 operation
        code_list = [""]
        fake_file = StringIO.StringIO(source_code)
        for line in fake_file:
            code_list.append(line)
        self.source_code_list = code_list
        self.source_code_lines = len(code_list)-1
        self.lines_depth = [65535] * (self.source_code_lines+1)
        self.class_name = class_name
        self.function_name = function_name
        self.terminated = False
        self.start_line = None
        self.end_line = None
        self.parse_root()

    def parse_root(self):
        tree = ast.parse(self.source_code)
        tree.depth = 0
        tree.class_name = ""
        self.visit(tree)

    def generic_visit(self, node):
        if self.terminated:
            return
        self.mark_line_depth(node)
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
            self.end_line = self.get_last_line(node.lineno, node.depth)
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
            self.end_line = self.get_last_line(node.lineno, node.depth)
            self.terminated = True
            return

    def get_source_code(self):
        if not self.start_line or not self.end_line:
            return None
        code = self.source_code_list[self.start_line: self.end_line+1]
        return "".join(code)

    def get_last_line(self, line_num, depth):
        end_line = line_num
        for idx in xrange(line_num+1, self.source_code_lines+1):
            if self.lines_depth[idx] > depth:
                end_line = idx
            else:
                break
        for line in xrange(end_line, line_num, -1):
            if not self.source_code_list[end_line].strip(" \r\n\t"):
                end_line = line - 1
        return end_line

    def mark_line_depth(self, item):
        if hasattr(item, "lineno"):
            self.lines_depth[item.lineno] = item.depth
        if hasattr(item, "body"):
            if not isinstance(item.body, list):
                self.lines_depth[item.body.lineno] = item.depth+1
            else:
                for node in item.body:
                    self.lines_depth[node.lineno] = item.depth+1


def read_file(file_name, class_name="", function_name=""):
    try:
        with open(file_name, "r") as f:
            node_parser = NodeParser(f.read(), class_name, function_name)
            node_parser.parse_root()
        print node_parser.get_source_code()
        return node_parser
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
    options.function_name = ""
    options.class_name = "IPAddressField"

    if len(args) == 0:
        raise Exception("File name is required!")
    if not options.class_name and not options.function_name:
        raise Exception("Function or Class is required!")

    read_file(file_name=args[0], function_name=options.function_name, class_name=options.class_name)
