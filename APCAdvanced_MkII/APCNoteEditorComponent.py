from pushbase.note_editor_component import NoteEditorComponent, is_triplet_quantization, most_significant_note
from .APCMessenger import APCMessenger

VELOCITY_COLORS = ((127, 'Full'),
 (94, 'High'),
 (62, 'Medium'),
 (31, 'Low'),
 (0, 'Empty'))

def color_for_note(note):
  if note.mute:
    return 'Muted'
  for threshold, color in VELOCITY_COLORS:
    if note.velocity >= threshold:
      return color
  return 'Empty'


class APCNoteEditorComponent(NoteEditorComponent, APCMessenger):
  """ Customized to show five velocity steps rather than Live's three,
  and to lay out triplets across the APC's four-wide step grid
  """

  def _determine_color(self, notes):
    return color_for_note(most_significant_note(notes))

  def _visible_steps(self):
    """ Patched to support four-wide """
    first_time = self.page_length * self._page_index
    step_length = self._get_step_length()
    steps_per_row = self._get_width()
    indices = list(range(self._get_step_count()))
    if is_triplet_quantization(self._triplet_factor):
      triplet_steps = steps_per_row * 3 // 4
      indices = [ k for k in indices if k % steps_per_row < triplet_steps ]
    return [ (self._time_step(first_time + k * step_length), index) for k, index in enumerate(indices) ]
