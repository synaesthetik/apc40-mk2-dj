"""Puts Live 11's API on the import path with a stubbed `Live` module.

Import this before anything from the script or from Live.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REFERENCE = os.environ.get('LIVE11_REFERENCE')
if not REFERENCE:
  raise SystemExit('set LIVE11_REFERENCE to a tree prepared by tools/prepare_reference.py')
sys.path[:0] = [ROOT, os.path.join(ROOT, 'tools'), os.path.abspath(REFERENCE)]
import live_stub
live_stub.install()


class FakeEvents(object):
  """ Stands in for a Live object: any attribute set on it, plus the add/remove/has
  listener trio for any event name, which is what the slot machinery checks for """

  def __init__(self, **attributes):
    self.__dict__['_listeners'] = {}
    self.__dict__.update(attributes)

  def __getattr__(self, name):
    for prefix, action in (('add_', 'add'), ('remove_', 'remove')):
      if name.startswith(prefix) and name.endswith('_listener'):
        event = name[len(prefix):-len('_listener')]
        return lambda listener, *a, **k: self._change(action, event, listener)

    if name.endswith('_has_listener'):
      event = name[:-len('_has_listener')]
      return lambda listener: listener in self._listeners.get(event, [])
    raise AttributeError(name)

  def _change(self, action, event, listener):
    listeners = self._listeners.setdefault(event, [])
    if action == 'add':
      listeners.append(listener)
    elif listener in listeners:
      listeners.remove(listener)

  def notify(self, event, *a):
    for listener in list(self._listeners.get(event, [])):
      listener(*a)
