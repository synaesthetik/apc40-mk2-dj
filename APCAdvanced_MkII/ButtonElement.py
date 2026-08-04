from _Framework.ButtonElement import ButtonElement

class ButtonElement(ButtonElement):
  """ Extended ButtonElement that exposes the correct API for
  Various Push-specific tools """

  def set_on_off_values(self, on_value, off_value):
    """ We don't actually care, but the script does want to set these.
    If the button doesn't support 'em, no change is necessary """
    pass

  def reset(self):
    """ Live 11's reset_state puts back the default channel and identifier, and
    also clears the script suppression the drum pads switch on while
    sequencing, which plain reset() leaves in place """
    self.reset_state()
    super(ButtonElement, self).reset()
