from .ButtonElement import ButtonElement

class ColorButtonElement(ButtonElement):
  """ RGB clip button.

  Live 11 removed Push's ConfigurableButtonElement, which this was originally
  built on. The stock APC40 MkII script now gets RGB feedback by tagging a
  plain ButtonElement, so we do the same.
  """

  def __init__(self, *a, **k):
    super(ColorButtonElement, self).__init__(*a, **k)
    self.is_rgb = True
    self.num_delayed_messages = 2
