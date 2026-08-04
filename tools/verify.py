"""Check the script against Live 11's own remote-script sources.

Ableton's API only exists inside Live, so this stubs the `Live` module, puts a
prepared copy of Live 11's MIDI Remote Scripts on the path and then:

  1. imports the package, which resolves every import for real
  2. checks every `super(...).method()` call exists on the base classes
  3. checks the keywords passed to base constructors are accepted
  4. checks every `self._attribute` read comes from us or from a base class

  python3 tools/verify.py --reference <prepared Live 11 tree> [--package APCAdvanced_MkII]

Live 11 ships bytecode only, so the reference tree comes from a decompilation
run through tools/prepare_reference.py.
"""
import argparse
import ast
import importlib
import inspect
import os
import sys
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

class Finding(object):

  def __init__(self, path, line, message):
    self.path = path
    self.line = line
    self.message = message

  def __str__(self):
    return '%s:%d %s' % (self.path, self.line, self.message)


def _iter_classes(tree):
  for node in ast.walk(tree):
    if isinstance(node, ast.ClassDef):
      yield node


def _self_assignments(class_node):
  names = set()
  for node in ast.walk(class_node):
    if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
      if isinstance(node.value, ast.Name) and node.value.id == 'self':
        names.add(node.attr)
  for node in class_node.body:
    if isinstance(node, ast.Assign):
      for target in node.targets:
        if isinstance(target, ast.Name):
          names.add(target.id)
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
      names.add(node.name)
  return names


def _base_self_assignments(cls):
  """ Attributes the class or any base sets on self, read out of their sources.

  dir() covers methods and the accessors the event metaclasses generate, and the
  source scan covers plain instance attributes assigned in __init__.
  """
  names = set(dir(cls))
  for base in inspect.getmro(cls)[1:]:
    names.update(dir(base))
    try:
      source = inspect.getsource(base)
    except (OSError, TypeError):
      continue
    try:
      tree = ast.parse(textwrap.dedent(source))
    except SyntaxError:
      continue
    for node in _iter_classes(tree):
      names.update(_self_assignments(node))

  return names


def _super_calls(class_node):
  """ (line, method name, keyword names) for each super(...).method(...) call """
  for node in ast.walk(class_node):
    if not isinstance(node, ast.Call):
      continue
    func = node.func
    if not isinstance(func, ast.Attribute):
      continue
    value = func.value
    if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == 'super'):
      continue
    keywords = [k.arg for k in node.keywords if k.arg]
    yield (node.lineno, func.attr, keywords)


def _accepts_keyword(cls, method, keyword):
  """ Whether the cooperative call chain names this keyword anywhere.

  A base that only takes **k is not enough: it forwards on, and the chain ends
  at object.__init__, which rejects anything it was not told about.
  """
  for base in inspect.getmro(cls)[1:]:
    function = vars(base).get(method)
    if function is None:
      continue
    try:
      signature = inspect.signature(function)
    except (TypeError, ValueError):
      return True
    if keyword in signature.parameters:
      return True

  return False


def _resolve_after(cls, name):
  """ Look the name up the way super() would, skipping cls itself """
  for base in inspect.getmro(cls)[1:]:
    if name in vars(base):
      return vars(base)[name]

  return None


def check_package(package_name, package_dir):
  findings = []
  module_prefix = package_name + '.'
  for filename in sorted(os.listdir(package_dir)):
    if not filename.endswith('.py'):
      continue
    module_name = package_name if filename == '__init__.py' else module_prefix + filename[:-3]
    module = importlib.import_module(module_name)
    path = os.path.join(package_dir, filename)
    with open(path) as handle:
      tree = ast.parse(handle.read(), filename=filename)
    for class_node in _iter_classes(tree):
      cls = getattr(module, class_node.name, None)
      if not inspect.isclass(cls):
        continue
      known = _self_assignments(class_node) | _base_self_assignments(cls)
      for line, method, keywords in _super_calls(class_node):
        target = _resolve_after(cls, method)
        if target is None:
          findings.append(Finding(filename, line, '%s: base classes have no %s()' % (class_node.name, method)))
          continue
        for keyword in keywords:
          if not _accepts_keyword(cls, method, keyword):
            findings.append(Finding(filename, line, '%s: %s() does not accept %s=' % (
             class_node.name, method, keyword)))

      for node in ast.walk(class_node):
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load):
          if isinstance(node.value, ast.Name) and node.value.id == 'self':
            if node.attr not in known:
              findings.append(Finding(filename, node.lineno, '%s: self.%s is not defined here or in any base class' % (
               class_node.name, node.attr)))

  return findings


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument('--reference', required=True, help='prepared Live 11 MIDI Remote Scripts tree')
  parser.add_argument('--package', default='APCAdvanced_MkII')
  arguments = parser.parse_args()
  sys.path.insert(0, HERE)
  sys.path.insert(0, os.path.abspath(arguments.reference))
  sys.path.insert(0, ROOT)
  import live_stub
  live_stub.install()
  package = importlib.import_module(arguments.package)
  print('imported %s from %s' % (arguments.package, os.path.dirname(package.__file__)))
  findings = check_package(arguments.package, os.path.join(ROOT, arguments.package))
  for finding in findings:
    print('  %s' % finding)
  print('%d finding(s)' % len(findings))
  return 1 if findings else 0


if __name__ == '__main__':
  raise SystemExit(main())
