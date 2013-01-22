###
# Copyright (c) 2013, spline, Ashiudo
# All rights reserved.
###

import os
import supybot.conf as conf
import supybot.registry as registry
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('NHL')

def configure(advanced):
    # This will be called by supybot to configure this module.  advanced is
    # a bool that specifies whether the user identified himself as an advanced
    # user or not.  You should effect your configuration by manipulating the
    # registry as appropriate.
    from supybot.questions import expect, anything, something, yn
    conf.registerPlugin('NHL', True)


NHL = conf.registerPlugin('NHL')
conf.registerGlobalValue(NHL, 'dbLocation', registry.String(os.path.abspath(os.path.dirname(__file__))+'/db/nhl.db',"""Absolute path for nhl.db sqlite3 database file location."""))
conf.registerGlobalValue(NHL, 'useGzip', registry.Boolean(False, """Request html to be gzipped before downloaded"""))
# vim:set shiftwidth=4 tabstop=4 expandtab textwidth=250:
