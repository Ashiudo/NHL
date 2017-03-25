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
import gzip
import StringIO
import json
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

    def __init__(self, irc):
        if __name__ != "__main__":
            self.__parent = super(NHL, self)
            self.__parent.__init__(irc)
            self.dbLocation = self.registryValue('dbLocation')

    ######################
    # DATABASE FUNCTIONS #
    ######################

    if __name__ == "__main__":
        import supybot.log as log

    def _validteams(self, conf=None, div=None):
        """Returns a list of valid teams for input verification."""

        db_filename = self.dbLocation
        conn = sqlite3.connect(db_filename)
        cursor = conn.cursor()
        if conf and not div:
            cursor.execute("select team from nhl where conf=?", (conf,))
        elif conf and div:
            cursor.execute("select team from nhl where conf=? AND div=?", (conf,div,))
        else:
            cursor.execute("select team from nhl")
        teamlist = []
        for row in cursor.fetchall():
            teamlist.append(str(row[0]))
        cursor.close()
        return teamlist

    def _translateTeam(self, db, column, optteam):
        """Returns a list of valid teams for input verification."""

        db_filename = self.dbLocation
        conn = sqlite3.connect(db_filename)
        cursor = conn.cursor()
        query = "select %s from nfl where %s='%s'" % (db, column, optteam)
        cursor.execute(query)
        row = cursor.fetchone()
        cursor.close()
        return (str(row[0]))

    ######################
    # INTERNAL FUNCTIONS #
    ######################

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
            req.add_header("User-Agent","Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.21 Safari/537.36")
            if __name__ != "__main__" and self.registryValue('useGzip'):
                req.add_header("Accept-Encoding","gzip")
                zhtml = urllib2.urlopen(req)
                if zhtml.info().get('Content-Encoding') == 'gzip':
                    try:
                        zIO = StringIO(zhtml.read())
                        zFile = gzip.GzipFile(fileobj=zIO)
                        html = zFile.read()
                    except Exception, e:
                        html = zhtml.read()
                else:
                    html = zhtml.read()
            else:
                print "fetching " + url
                html = (urllib2.urlopen(req)).read()

            return html
        except Exception, e:
            self.log.error("ERROR fetching: {0} message: {1}".format(url, e))
            return None

    ####################
    # PUBLIC FUNCTIONS #
    ####################

    def nhlteams(self, irc, msg, args, optconf, optdiv):
        """<conf> <div>
        Display a list of NHL teams for input. Optional: use Eastern or Western for conference.
        Optionally, it can also display specific divisions with each conf. Ex: Eastern Northeast
        """

        validconfdiv = {'Eastern':('Atlantic','Northeast','Southeast'),
                        'Western':('Central','Northwest','Pacific')
                       }

        if optconf and not optdiv:
            optconf = optconf.title()
            if optconf not in validconfdiv:
                irc.reply("ERROR: Conference must be one of: {0}".format(validconfdiv.keys()))
                return
            else:
                teams = self._validteams(conf=optconf)
        elif optconf and optdiv:
            optconf,optdiv = optconf.title(),optdiv.title()
            if optconf not in validconfdiv:
                irc.reply("ERROR: Conference must be one of: {0}".format(validconfdiv.keys()))
                return
            if optdiv not in validconfdiv[optconf]:
                irc.reply('ERROR: Division in {0} must be one of: {1}'.format(optconf, validconfdiv[optconf]))
                return
            teams = self._validteams(conf=optconf, div=optdiv)
        else:
            teams = self._validteams()

        irc.reply("Valid teams are: %s" % (string.join([ircutils.bold(item) for item in teams], " | ")))

    nhlteams = wrap(nhlteams, [optional('somethingWithoutSpaces'), optional('somethingWithoutSpaces')])

    def nhldailyleaders(self, irc, msg, args, optposition):
        """
        Display NHL daily leaders.
        """

        url = 'http://www.espn.com/nhl/stats/dailyleaders'

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

    def nhlleaders(self, irc, msg, args, optcategory):
        """[category]
        Display NHL stat leaders for the current season.
        """

        ereply = "Valid categories: \x035P\x03oints \x035G\x03oals \x035A\x03ssists " \
                 + "\x035+\x03/- \x035GAA\x03 \x035SV\x03% \x035W\x03ins \x035Sh\x03utouts"

        if not optcategory:
            irc.reply(ereply)
            return
        #qw(points goals assists plusMinus gaa savePercentage wins shutout);
        statcats = {
            'p($|ts|oint)':'points', 'g($|oal)':'goals',
            'a($|ssist)':'assists', 'plus|\+':'plusMinus',
            'ga+$':'gaa', 's[av]($|\%|ve)':'savePercentage',
            'w($|in)':'wins', 's[oh]':'shutout'
        }

        optcategory = optcategory.lower()
        cat = None
        goalie = False
        for r in statcats.iterkeys():
            reg = re.compile(r)
            m = reg.match(optcategory)
            if m:
                cat = statcats[r]
                exit

        if not cat:
            irc.reply(ereply)
            return


        html = self._fetch('http://www.nhl.com/stats/leaders')
        if not html:
            irc.reply('ERROR: Something broke fetching leaders.')
            return

        matches = re.search(r"LeaderData = (.*?\})\;.*?(\{.*?\})\;", html, re.S)
        js = json.loads(matches.group(2 if cat in {'gaa', 'savePercentage', 'wins', 'shutout'} else 1))

        maxlen = 1
        for p in js[cat][cat][0:5]:
            p['abvName'] = p['firstName'][0] + ". " + p['lastName']
            if len(p['abvName']) > maxlen:
                maxlen = len(p['abvName'])

        stack = ['NHL Top 5 ' + cat]
        i = 1
        try:
            for p in js[cat][cat][0:5]:
                stack.append(("%d. %-*s [%s] \x02%.3g") % (i, maxlen, p['abvName'], p['tricode'], p['value']))
                i+=1
        except Exception:
            stack = ['ERROR: json incomplete']

        for each in stack:
            irc.reply(each)

    nhlleaders = wrap(nhlleaders, [optional('somethingWithoutSpaces')])

#http://www.nhl.com/ice/app?service=page&page=CFStandingsJS&format=full
# http://nlced.cdnak.neulion.com/nhl/config/ced_config.xml
Class = NHL

# http://pastebin.com/Ev0VcDQ3
# http://www.nhl.com/ice/page.htm?id=80955
# roster
# http://sports.yahoo.com/nhl/players?type=lastname&query=A
# http://www.timeonice.com, http://www.behindthenet.ca, http://www.hockeyanalysis.com, and http://www.hockeyanalytics.com, and attempts to improve the user experience with a GWT interface.

if __name__ == "__main__":

    class fake_irc:
        def reply(self, msg):
            print msg

    irc = fake_irc()
    n = NHL(0)

    #     n.function( irc, '', ['parameters'] )
    print n.nhlleaders( irc, '', ['sv'] )

    n.log.setLevel( 100 )  #dont need to hear from our fake supybot anymore


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=250:
