# -*- coding: utf-8 -*-
###
# Copyright (c) 2013, spline, Ashiudo
# All rights reserved.
###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('NHL')

@internationalizeDocstring
class NHL(callbacks.Plugin):
    """Add the help for "@plugin help NHL" here
    This should describe *how* to use this plugin."""
    threaded = True

	# http://www.nhl.com/ice/page.htm?id=80955
# roster
# http://sports.yahoo.com/nhl/players?type=lastname&query=A
# http://www.timeonice.com, http://www.behindthenet.ca, http://www.hockeyanalysis.com, and http://www.hockeyanalytics.com, and attempts to improve the user experience with a GWT interface. 

Class = NHL


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=250:
