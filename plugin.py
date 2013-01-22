# -*- coding: utf-8 -*-
###
# Copyright (c) 2013, spline, Ashiudo
# All rights reserved.
###
import urllib2
from BeautifulSoup import BeautifulSoup, NavigableString
import re
import string
import datetime
import time
import sqlite3
import os
from itertools import groupby, izip, count

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

    def _batch(self, iterable, size):
        """http://code.activestate.com/recipes/303279/#c7"""
        c = count()
        for k, g in groupby(iterable, lambda x:c.next()//size):
            yield g

    def _b64decode(self, string):
        """Returns base64 encoded string."""
        import base64
        return base64.b64decode(string)

    def _red(self, string):
        """Returns a red string."""
        return ircutils.mircColor(string, 'red')

    def _yellow(self, string):
        """Returns a yellow string."""
        return ircutils.mircColor(string, 'yellow')

    def _green(self, string):
        """Returns a green string."""
        return ircutils.mircColor(string, 'green')

    def _bold(self, string):
        """Returns a bold string."""
        return ircutils.bold(string)

    def _ul(self, string):
        """Returns an underline string."""
        return ircutils.underline(string)

    def _bu(self, string):
        """Returns a bold/underline string."""
        return ircutils.bold(ircutils.underline(string))

    def _fetch(self, url):
        """HTML Fetch."""
        try:
            req = urllib2.Request(url)
            req.add_header("User-Agent","Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:17.0) Gecko/17.0 Firefox/17.0")
            html = (urllib2.urlopen(req)).read()
            return html
        except Exception, e:
            self.log.error("ERROR fetching: {0} message: {1}".format(url, e))
            return None            

    ####################
    # PUBLIC FUNCTIONS #
    ####################
    
    def nhldailyleaders(self, irc, msg, args, optposition):
        """
        Display NHL daily leaders.
        """
        
        url = self._b64decode('aHR0cDovL2VzcG4uZ28uY29tL25obC9zdGF0cy9kYWlseWxlYWRlcnM=')
        
        html = self._fetch(url)
        if not html:
            irc.reply("Something broke fetching dailyleaders.")
            return
            
        soup = BeautifulSoup(html)
        if not soup.find('table', attrs={'class':'tablehead', 'cellpadding':'3', 'cellspacing':'1'}):
            irc.reply("Something broke on formatting. Contact an owner.")
            return
            
        header = soup.find('h1', attrs={'class':'h2'}).getText()
        table = soup.find('table', attrs={'class':'tablehead', 'cellpadding':'3', 'cellspacing':'1'}) 
        title = table.find('tr', attrs={'class':'stathead'}).getText()
        rows = table.findAll('tr', attrs={'class':re.compile('^(odd|even)row.*?$')})

        if len(rows) < 1:
            irc.reply("No daily leaders found. No games played yet?")
            return

        output = []

        for row in rows:
            tds = row.findAll('td')
            rank = tds[0].getText()
            player = tds[1].getText()
            team = tds[2].getText()
            perf = tds[5].getText()
            output.append("{0}. {1}({2}) - {3}".format(rank,self._bold(player),team,perf))

        # output now.
        irc.reply("{0} :: {1}".format(self._red(header), title))
        for each in output[0:5]:
            irc.reply(each)
    
    nhldailyleaders = wrap(nhldailyleaders, [optional('somethingWithoutSpaces')])

Class = NHL

# http://pastebin.com/Ev0VcDQ3
# http://www.nhl.com/ice/page.htm?id=80955
# roster
# http://sports.yahoo.com/nhl/players?type=lastname&query=A
# http://www.timeonice.com, http://www.behindthenet.ca, http://www.hockeyanalysis.com, and http://www.hockeyanalytics.com, and attempts to improve the user experience with a GWT interface. 


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=250:
