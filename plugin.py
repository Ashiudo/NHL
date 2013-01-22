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
        self.__parent = super(NHL, self)
        self.__parent.__init__(irc)
        self.dbLocation = self.registryValue('dbLocation')

    ######################
    # DATABASE FUNCTIONS #
    ######################

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
            if not self.registryValue('useGzip'):
                req.add_header("User-Agent","Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:17.0) Gecko/17.0 Firefox/17.0")
                html = (urllib2.urlopen(req)).read()
            else:
                req.add_header("User-Agent","Mozilla/5.0 (gzip; X11; Ubuntu; Linux x86_64; rv:17.0) Gecko/17.0 Firefox/17.0")
                req.add_header("Accept-Encoding","gzip")
                zhtml = urllib2.urlopen(req)
                zIO = StringIO.StringIO(zhtml.read())
                zFile = gzip.GzipFile(fileobj=zIO)
                try:
                    html = zFile.read()
                except IOError: #data was not gzipped
                    html = zhtml.read()

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

    def nhlleaders(self, irc, msg, args, optcategory):
        """[category]
        Display NHL stat leaders for the current season.
        """

        ereply = "Valid categories: \x035P\x03oints \x035G\x03oals \x035A\x03ssists " \
                 + "\x035+\x03/- \x035GAA\x03 \x035SV\x03% \x035W\x03ins \x035Sh\x03utouts"

        if not optcategory:
            irc.reply(ereply)
            return

        statcats = {
            'p($|ts|oint)':'points', 'g($|oal)':'goals',
            'a($|ssist)':'assists', 'plus|\+':'plusMins',
            'ga+$':'gaa', 's[av]($|\%|ve)':'savePct',
            'w($|in)':'wins', 's[oh]':'shutouts'
        }

        optcategory = optcategory.lower()
        cat = None
        for r in statcats.iterkeys():
            reg = re.compile(r)
            m = reg.match(optcategory)
            if m:
                cat = statcats[r]
                exit

        if not cat:
            irc.reply(ereply)
            return


        url = self._b64decode('aHR0cDovL2xpdmUubmhsZS5jb20vR2FtZURhdGEvU3RhdHNMZWFkZXJzLmpzb24=')
        html = self._fetch(url)
        if not html:
            irc.reply('ERROR: Something broke fetching leaders.')
            return

        js = json.loads(html)
        if cat in js['goaltending']:
            ld = js['goaltending'][cat]
        elif cat in js['offense']:
            ld = js['offense'][cat]
        else:
            irc.reply('ERROR: json has changed')
            return

        maxlen = 1
        abrevname = re.compile('(.)[^ ]* (.*)')
        for p in ld:
            m = abrevname.match(p['name'])
            p['name'] = m.group(1) + ". " + m.group(2)
            if len(p['name']) >= maxlen:
                maxlen = len(p['name']) + 1

        stack = ['NHL Top 5 ' + cat]
        i = 1
        try:
            for p in ld:
                stack.append(str(i) + ". " + p['name'] + " " * ( maxlen - len(p['name']) ) + "[" + p['team'] + "] " + p['stat'])
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


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=250:
