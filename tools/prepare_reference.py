"""Turn a decompiled Live 11 remote-scripts tree into an importable copy.

The published decompilations carry committed merge-conflict markers. Each side
of a conflict is valid Python on its own, so this copies the tree and keeps
whichever side compiles.

  python3 tools/prepare_reference.py <source tree> <destination>
"""
import os
import py_compile
import re
import shutil
import sys
import tempfile

CONFLICT = re.compile(r'^(<<<<<<< |=======$|>>>>>>> )')
FAILED_SECTION = re.compile(r'^(\s*)def (\w+)--- This code section failed: ---')
PARSE_ERROR = re.compile(r'^Parse error at or near')
MODULE_ALIAS_IMPORT = re.compile(r'^(\s*)import ([\w.]+) as (\w+)\s*$')
CLASS_DEF = re.compile(r'^class (\w+)\b', re.M)

# The decompiler garbles some boolean expressions into something that parses but
# means nothing. These are the ones that stop listeners from connecting at all,
# repaired to the only reading the surrounding code allows.
EXPLICIT_FIXUPS = {'ableton/v2/base/event.py': [
                    ('if not (self.is_connected or self.subject_valid)(self._subject) or self._listener is not None:',
                     'if not self.is_connected and self.subject_valid(self._subject) and self._listener is not None:'),
                    ('if not self.is_connected and self.subject_valid(self._subject) or self._listener is not None:',
                     'if self.is_connected:')],
 '_Framework/SubjectSlot.py': [
                    ('if not (self.is_connected or self._subject) != None or self._listener != None:',
                     'if not self.is_connected and self._subject != None and self._listener != None:'),
                    ('if not self.is_connected and self._subject != None or self._listener != None:',
                     'if self.is_connected:')]}

def _split_sides(lines):
  ours, theirs = [], []
  state = 'both'
  for line in lines:
    if line.startswith('<<<<<<< '):
      state = 'ours'
    elif state == 'ours' and line.rstrip('\n') == '=======':
      state = 'theirs'
    elif line.startswith('>>>>>>> '):
      state = 'both'
    elif state == 'both':
      ours.append(line)
      theirs.append(line)
    elif state == 'ours':
      ours.append(line)
    else:
      theirs.append(line)

  return (ours, theirs)


def _compiles(source, name):
  handle, path = tempfile.mkstemp(suffix='.py')
  os.close(handle)
  try:
    with open(path, 'w') as out:
      out.write(source)
    try:
      py_compile.compile(path, cfile=(path + 'c'), doraise=True)
      return True
    except py_compile.PyCompileError:
      return False

  finally:
    os.unlink(path)


def _repair_failed_sections(source):
  """ Stub out methods the decompiler gave up on.

  Those come through as `def name--- This code section failed: ---` followed by
  a disassembly dump. The signature is lost, so the stub takes anything: the
  reference tree is only used to check imports and call signatures, and a stub
  body would raise loudly if anything ever leaned on it.
  """
  source = source.replace('Noneand ', 'None and ')
  lines = source.splitlines(True)
  output = []
  index = 0
  while index < len(lines):
    match = FAILED_SECTION.match(lines[index])
    if not match:
      output.append(lines[index])
      index += 1
      continue
    indent, name = match.group(1), match.group(2)
    output.append('%sdef %s(self, *a, **k):\n' % (indent, name))
    output.append("%s    raise NotImplementedError('decompilation failed')\n" % indent)
    index += 1
    while index < len(lines) and not PARSE_ERROR.match(lines[index]):
      index += 1
    index += 1

  return ''.join(output)


def _provides_name(tree_root, module_path, name):
  """ Whether importing `name` out of `module_path` would work """
  base = os.path.join(tree_root, *module_path.split('.'))
  for candidate in (base + '.py', os.path.join(base, '__init__.py')):
    if not os.path.exists(candidate):
      continue
    with open(candidate, encoding='utf-8', errors='replace') as handle:
      source = handle.read()
    escaped = re.escape(name)
    if re.search(r'^class %s\b|^%s = |^\s*(from|import) .*\b%s\b' % (escaped, escaped, escaped), source, re.M):
      return True

  return False


def _repair_module_class_imports(source, tree_root):
  """ Recover `from pkg.Mod import Mod` from the decompiler's `import pkg.Mod as Mod`.

  Ableton names a module and its main class alike, and the decompiler collapses
  the class import into a module import, so subclassing it raises TypeError.
  """
  output = []
  for line in source.splitlines(True):
    match = MODULE_ALIAS_IMPORT.match(line)
    if match:
      indent, module_path, alias = match.groups()
      used_as_module = re.search(r'\b%s\.\w' % re.escape(alias), source.replace(line, ''))
      if not used_as_module:
        for class_name in (alias, re.sub(r'Base$', '', alias), module_path.rsplit('.', 1)[-1]):
          if _provides_name(tree_root, module_path, class_name):
            line = '%sfrom %s import %s as %s\n' % (indent, module_path, class_name, alias)
            break
    output.append(line)

  return ''.join(output)


def _repair_dropped_stars(source):
  """ Put back the star the decompiler dropped from varargs forwarding.

  `(super(X, self).__init__)(a, name=name, **k)` was `(*a, name=name, **k)`,
  and without the star the positional tuple lands in the first parameter.
  """
  output = []
  for line in source.splitlines(True):
    if '**k' in line:
      line = re.sub(r'\)\((a|args), ', r')(*\1, ', line)
    output.append(line)

  return ''.join(output)


def _module_exists(tree_root, dotted):
  parts = dotted.split('.')
  base = os.path.join(tree_root, *parts)
  return os.path.exists(base + '.py') or os.path.isdir(base)


def _repair_truncated_imports(source, tree_root, package):
  """ Put back the package prefix the decompiler dropped.

  Some modules come out with `from control_surface.foo import Bar` where the
  original said `from ..foo import Bar`, so the leading packages are searched
  for one that makes the path resolve.
  """
  output = []
  ancestors = []
  parts = package.split('.') if package else []
  for count in range(len(parts), -1, -1):
    ancestors.append('.'.join(parts[:count]))
  for line in source.splitlines(True):
    match = re.match(r'^(\s*)from ([\w.]+) import (.+)$', line)
    if match and not match.group(2).startswith('.'):
      indent, dotted, names = match.groups()
      if not _module_exists(tree_root, dotted) and dotted.split('.')[0] not in sys.builtin_module_names:
        for ancestor in ancestors:
          candidate = '%s.%s' % (ancestor, dotted) if ancestor else dotted
          if _module_exists(tree_root, candidate):
            line = '%sfrom %s import %s\n' % (indent, candidate, names)
            break

    output.append(line)

  return ''.join(output)


def resolve(path, tree_root=None, package=''):
  with open(path, encoding='utf-8', errors='replace') as handle:
    lines = handle.readlines()
  if any(CONFLICT.match(line) for line in lines):
    ours, theirs = _split_sides(lines)
    candidates = [''.join(ours), ''.join(theirs)]
  else:
    candidates = [''.join(lines)]
  repaired = [_repair_failed_sections(candidate) for candidate in candidates]
  chosen = repaired[0]
  for candidate in candidates + repaired:
    if _compiles(candidate, path):
      chosen = candidate
      break

  if tree_root:
    chosen = _repair_dropped_stars(chosen)
    chosen = _repair_module_class_imports(chosen, tree_root)
    chosen = _repair_truncated_imports(chosen, tree_root, package)
  return chosen


def main(source, destination):
  if os.path.exists(destination):
    shutil.rmtree(destination)
  conflicted = 0
  broken = []
  for root, dirs, files in os.walk(source):
    if '.git' in dirs:
      dirs.remove('.git')
    target_root = os.path.join(destination, os.path.relpath(root, source))
    os.makedirs(target_root, exist_ok=True)
    for name in files:
      if not name.endswith('.py'):
        continue
      source_path = os.path.join(root, name)
      target_path = os.path.join(target_root, name)
      package = os.path.relpath(root, source).replace(os.sep, '.')
      package = '' if package == '.' else package
      resolved = resolve(source_path, tree_root=source, package=package)
      relative = os.path.relpath(target_path, destination)
      for old, new in EXPLICIT_FIXUPS.get(relative.replace(os.sep, '/'), []):
        if old not in resolved:
          print('fixup no longer applies in %s: %s' % (relative, old))
        resolved = resolved.replace(old, new)
      with open(target_path, 'w') as out:
        out.write(resolved)
      if not _compiles(resolved, target_path):
        broken.append(os.path.relpath(target_path, destination))
      with open(source_path, encoding='utf-8', errors='replace') as handle:
        if any(CONFLICT.match(line) for line in handle):
          conflicted += 1

  print('prepared %s (conflicts resolved in %d files)' % (destination, conflicted))
  if broken:
    print('%d file(s) still do not compile:' % len(broken))
    for name in sorted(broken)[:20]:
      print('  ' + name)
  return 0


if __name__ == '__main__':
  if len(sys.argv) != 3:
    print(__doc__)
    raise SystemExit(2)
  raise SystemExit(main(sys.argv[1], sys.argv[2]))
