"""A permissive stand-in for Live's built-in `Live` module.

Live only exists inside Ableton's embedded interpreter, so importing any remote
script outside Live fails at `import Live`. This builds a module tree that
answers any attribute access, returning classes for capitalised names (so
`isinstance` and subclassing work) and callables otherwise.
"""
import sys
import types

class _Stub(types.ModuleType):

  def __init__(self, name):
    super(_Stub, self).__init__(name)
    self.__dict__['_children'] = {}

  def __getattr__(self, name):
    if name.startswith('__'):
      raise AttributeError(name)
    children = self.__dict__['_children']
    if name not in children:
      qualified = '%s.%s' % (self.__name__, name)
      if name[:1].isupper():
        children[name] = _StubClass(qualified)
      else:
        children[name] = _StubValue(qualified)
      sys.modules[qualified] = children[name] if isinstance(children[name], _Stub) else self
    return children[name]


class _StubClassMeta(type):

  def __getattr__(cls, name):
    if name.startswith('__'):
      raise AttributeError(name)
    value = _StubClass('%s.%s' % (cls.__name__, name)) if name[:1].isupper() else _StubValue('%s.%s' % (cls.__name__, name))
    setattr(cls, name, value)
    return value


def _StubClass(name):
  return _StubClassMeta(str(name.split('.')[-1]), (object,), {'_qualified_name': name})


class _StubValue(object):

  def __init__(self, name):
    self._name = name

  def __call__(self, *a, **k):
    return _StubValue('%s()' % self._name)

  def __getattr__(self, name):
    if name.startswith('__'):
      raise AttributeError(name)
    return _StubValue('%s.%s' % (self._name, name))

  def __int__(self):
    return 0

  def __iter__(self):
    # One element, because import-time code such as pushbase's scale list
    # indexes the first entry of what Live hands back
    return iter((_StubValue('%s[0]' % self._name),))

  def __len__(self):
    return 1

  def __getitem__(self, key):
    return _StubValue('%s[%r]' % (self._name, key))

  def __repr__(self):
    return '<LiveStub %s>' % self._name


def install():
  """ Register the stub as `Live` plus the submodules scripts import directly """
  root = _Stub('Live')
  sys.modules['Live'] = root
  for submodule in ('Application', 'Base', 'Clip', 'ClipSlot', 'Device', 'DeviceParameter',
   'MidiMap', 'Song', 'Track', 'Browser', 'Chain', 'DrumPad', 'Scene'):
    module = _Stub('Live.%s' % submodule)
    sys.modules['Live.%s' % submodule] = module
    root.__dict__['_children'][submodule] = module
    root.__dict__[submodule] = module
  return root
