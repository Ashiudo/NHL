#!/usr/bin/env python3
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

import urllib.request
from bs4 import BeautifulSoup, NavigableString
import re
import gzip
import json

try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('NHL')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x

_ = PluginInternationalization('NHL')

class NHL(callbacks.Plugin):
    """Get NHL scores and stats ETC."""

    def __init__(self, irc):
        if __name__ != "__main__":
            self.__parent = super(NHL, self)
            self.__parent.__init__(irc)

    if __name__ == "__main__":
        import supybot.log as log

    def _fetch(self, url):
        """HTML Fetch."""
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.21 Safari/537.36')
            if __name__ == "__main__" or self.registryValue('useGzip'):
                print( "fetching " + url )
                req.add_header('Accept-Encoding','gzip')
                zhtml = urllib.request.urlopen(req)
                if zhtml.info().get('Content-Encoding') == 'gzip':
                    try:
                        zFile = gzip.GzipFile(fileobj=zhtml)
                        html = zFile.read()
                    except Exception as e:
                        html = zhtml.read()
                else:
                    html = zhtml.read()
            else:
                html = (urllib.request.urlopen(req)).read()

            return html.decode('utf-8')
        except Exception as e:
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

    if __name__ != "__main__":
        nhlteams = wrap(nhlteams, [optional('somethingWithoutSpaces'), optional('somethingWithoutSpaces')])

    def nhldailyleaders(self, irc, msg, args):
        """
        Display NHL daily leaders.
        """

        url = 'http://www.espn.com/nhl/stats/dailyleaders'

        html = self._fetch(url)
        if not html:
            irc.reply("Something broke fetching dailyleaders.")
            return

        soup = BeautifulSoup(html, "lxml")
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

    if __name__ != "__main__":
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

        for r in list(statcats.keys()):
            reg = re.compile(r)
            m = reg.match(optcategory)
            if m:
                cat = statcats[r]
                exit

        if not cat:
            irc.reply(ereply)
            return

        html = self._fetch('http://www.nhl.com/stats/leaders')
        try:
            matches = re.search( r"LeaderData = (.*?\})\;.*?(\{.*?\})\;", html, re.S )
            js = json.loads(matches.group(2 if cat in {'gaa', 'savePercentage', 'wins', 'shutout'} else 1))
        except Exception:
            irc.reply('ERROR: Something broke fetching leaders.')
            return

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

    if __name__ != "__main__":
        nhlleaders = wrap(nhlleaders, [optional('somethingWithoutSpaces')])

    def nhlstandings(self, irc, msg, args, p):
        """<conf/div> [-p] [season]
        Display NHL standings.
        Optionally pass -p for wildcard
        """

        params = re.search( r"(atl|met|cen|pac|east|west)(?:\S*) *(wc|\-p|wild)? *(\d{4})?$", p.lower() )
        if not params:
            irc.reply('Valid categories: EAST WEST ATL CEN MET PAC [add -p for wildcard] [season]')
            return

        url = "http://statsapi.web.nhl.com/api/v1/standings?expand=standings.record,standings.team,standings.division,standings.conference,team.schedule.next,team.schedule.previous"
        search, wildcard, season = params.group(1, 2, 3)
        if season:
            url += "&season=%s%d" % (season, int( season )+1)
        if wildcard:
            search = 'cen|pac' if re.search( 'west|cen|pac', search ) else 'atl|met'

        try:
            js = json.loads( self._fetch( url ) )
        except Exception:
            irc.reply('ERROR: Something broke fetching standings.')
            return

        tosort, output, ret = [[],[],[]]
        divs = js['records']

        for d in divs:
            if re.search( search,  d['division']['name'] + d['conference']['name'], re.I ):
                tosort.extend( d['teamRecords'] )

        if re.search( 'east|west', search ):
            output = sorted( tosort, key=lambda rank: int(rank['conferenceRank']) );
            ret.append( output[0]['team']['conference']['name'].upper() )
        else:
            if wildcard:
                div1 = list(filter(lambda x:tosort[0]['team']['division']['id'] == x['team']['division']['id'], tosort))
                div2 = list(filter(lambda x:tosort[0]['team']['division']['id'] != x['team']['division']['id'], tosort))
                div1.sort( key=lambda rank: int(rank['divisionRank']) )
                div2.sort( key=lambda rank: int(rank['divisionRank']) )
                output.extend( div1[0:3] )
                output.extend( div2[0:3] )
                div1.extend( div2[3:] )
                div1.sort( key=lambda rank: int(rank['wildCardRank']) )
                output.extend( div1[3:] )
            else:
                output = sorted( tosort, key=lambda rank: int(rank['divisionRank']) )
            ret.append( output[0]['team']['division']['name'].upper() )

        ret[0] = "%-17s GP   W   L  OT  \x02PTS\x02  ROW   GF   GA  DIFF     L10  STRK" % ret[0]
        for o in output:
            diff = o['goalsScored'] - o['goalsAgainst']
            diffcolors = "\x03" + ( "4" if diff < 0 else "3" ) + " %4d\x03"
            if o['team']['locationName'] == 'New York':
                o['team']['locationName'] = "NY " + o['team']['teamName']

            if wildcard:
                rank = o['wildCardRank'] if o['wildCardRank'] != '0' else o['divisionRank']
            else:
                rank = o['divisionRank'] if len(output) < 10 else o['conferenceRank']

            lastten = ""
            for l in o['records']['overallRecords']:
                if l['type'] == 'lastTen':
                    lastten = "%d-%d-%d" % (l['wins'], l['losses'], l['ot'])

            ret.append(
                ("%2s %-14s %2d %3d %3d %3d \x02%4d\x02 %4d %4d %4d " + diffcolors + " %7s %5s") % (
                rank,
                ((o.get('clinchIndicator', "") + '-' ) if o.get('clinchIndicator', "") else "") + o['team']['locationName'],
                o['gamesPlayed'],
                o['leagueRecord']['wins'],
                o['leagueRecord']['losses'],
                o['leagueRecord']['ot'],
                o['points'],
                o['row'],
                o['goalsScored'],
                o['goalsAgainst'],
                diff,
                lastten,
                o['streak']['streakCode']
            ) )
        if wildcard:
            ret.insert( 4, "%-17s %s" % ( output[3]['team']['division']['name'].upper(), ret[0][18:] ) )
            ret.insert( 8, "WILDCARD    " + ret[0][12:] )
            ret[10] = "\x1F" + ret[10]

        for each in ret:
            irc.reply(each)

    if __name__ != "__main__":
        nhlstandings = wrap(nhlstandings, [optional('text')])

Class = NHL

#http://www.nhl.com/ice/app?service=page&page=CFStandingsJS&format=full
# http://nlced.cdnak.neulion.com/nhl/config/ced_config.xml
# http://pastebin.com/Ev0VcDQ3
# http://www.nhl.com/ice/page.htm?id=80955
# roster
# http://sports.yahoo.com/nhl/players?type=lastname&query=A
# http://www.timeonice.com, http://www.behindthenet.ca, http://www.hockeyanalysis.com, and http://www.hockeyanalytics.com, and attempts to improve the user experience with a GWT interface.

if __name__ == "__main__":

    import sys
    class fake_irc:
        def reply(self, msg):
            print( msg )

    irc = fake_irc()
    n = NHL(0)

    #     n.function( irc, '', ['parameters'] )
    print( n.nhlleaders( irc, '', [], ' '.join( sys.argv[1:] ) ) )

    n.log.setLevel( 100 )  #dont need to hear from our fake supybot anymore


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=250:
