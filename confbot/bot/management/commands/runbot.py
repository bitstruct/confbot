#! /usr/bin/env python
#
# Conference Bot
#
# Rob Emanuele <rje@bitstruct.com>

"""A bot for use during conferences

This is a bot useful during conferences to post needs and perform
conference centric irc operations.

The known commands are:

    stats -- Prints some channel information.

"""
import sys, os
print sys.path

from django.core.management.base import BaseCommand, CommandError
import irc.bot
import irc.strings
import logging
import exceptions
from irc.client import ip_numstr_to_quad, ip_quad_to_numstr
import confbot.assist as assist

class ConfBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, server, port=6667, password=None):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channel = channel
        self.auth_reqs = {}
        self.password = password
        self.desired_nick = nickname
        self.identified = False

    def on_nicknameinuse(self, c, e):
        print("Aux Nick")
        c.nick(c.get_nickname() + "_")
        print("Ghosting")
        c.privmsg("NickServ", "GHOST %s %s"%(self.desired_nick, self.password))
        print("Going to primary nick " + self.desired_nick)
        c.nick(self.desired_nick)
        c.privmsg("NickServ", "IDENTIFY %s"%(self.password))
        self.identified = True

    def on_welcome(self, c, e):
        if not self.identified:
            c.privmsg("NickServ", "IDENTIFY %s"%(self.password))
        c.join(self.channel)

    def on_privmsg(self, c, e):
        self.do_command(e, e.arguments[0])

    def on_pubmsg(self, c, e):
        a = e.arguments[0].split(":", 1)
        if len(a) > 1 and irc.strings.lower(a[0]) == irc.strings.lower(self.connection.get_nickname()):
            self.do_command(e, a[1].strip())
        return

    def do_command_not_understood(self, nick, c, e, cmd_array):
        c.notice(nick, "Not understood: " + ' '.join([str(x) for x in cmd_array]))

    def do_command(self, e, cmdstr):
        nick = e.source.nick
        c = self.connection
        try:
            cmd_array = cmdstr.split(" ", 1)
            method = getattr(self, "do_command_" + cmd_array[0].replace('-','_'), self.do_command_not_understood)
            method(nick, c, e, cmd_array)
        except Exception as ex:
            fname = os.path.split(sys.exc_traceback.tb_frame.f_code.co_filename)[1]
            c.notice(nick, "%s -> %s : %u"%(str(type(ex)), fname, sys.exc_traceback.tb_lineno))

    def do_command_stats(self, nick, c, e, cmd_array):
        for chname, chobj in self.channels.items():
            c.notice(nick, "--- Channel statistics ---")
            c.notice(nick, "Channel: " + chname)
            users = chobj.users()
            users.sort()
            c.notice(nick, "Users: " + ", ".join(users))
            opers = chobj.opers()
            opers.sort()
            c.notice(nick, "Opers: " + ", ".join(opers))
            voiced = chobj.voiced()
            voiced.sort()
            c.notice(nick, "Voiced: " + ", ".join(voiced))

    def do_command_needs(self, nick, c, e, cmd_array):
        c.notice(nick, "--- Needs ---")
        try:
            for need in assist.models.Need.objects.all():
                c.notice(nick, str(need.pk) + " " + need.nick + " - " + need.need)
        except assist.models.Need.DoesNotExist:
            c.notice(nick, "No needs yet.")

    def do_command_need(self, nick, c, e, cmd_array):
        if cmd_array[1] is not None:
            need = assist.models.Need(nick=nick, need=cmd_array[1])
            need.save()
            c.notice(nick, "Need %u listed: %s"%(need.pk, cmd_array[1]))
        else:
            c.notice(nick, "need requires a string parameter to list")

    def do_command_need_remove(self, nick, c, e, cmd_array):
        if len(cmd_array) == 2:
            try:
                need = assist.models.Need.objects.get(pk=int(cmd_array[1]), nick=nick)
                need.delete()
                c.notice(nick, "Need %u deleted"%(int(cmd_array[1])))
            except Exception:
                c.notice(nick, "Need %u not found for nick %s"%(int(cmd_array[1]), nick))
        else:
            c.notice(nick, "need-remove requires an index number to remove")

    def do_command_help(self, nick, c, e, cmd_array):
        c.notice(nick, "--- Help ---")
        c.notice(nick, "needs = list the needs showing need_index nick_requesting need_text")
        c.notice(nick, "need = add a need, example \"%s: need I need help with Python\""%(c.get_nickname()))
        c.notice(nick, "need-remove = remove one of your needs by index number, example \"%s: need-remove 6\""%(c.get_nickname()))
        c.notice(nick, "about = aboout this bot")

    def do_command_about(self, nick, c, e, cmd_array):
        c.notice(nick, "--- About ---")
        c.notice(nick, "confbot, and IRC bot to assist with conference collaboration")
        c.notice(nick, "Source: http://github.com/bitstruct/confbot")
        c.notice(nick, "Developer: BitStruct, LLC  http://www.bitstruct.com")


def start_confbot(*args):
    if len(args) != 3 and len(args) != 4:
        print "Parameters: <server[:port]> <channel> <nickname> [nickserv pass]"
        print args
        return 1

    logging.basicConfig(level=logging.DEBUG)
    s = args[0].split(":", 1)
    server = s[0]
    if len(s) == 2:
        try:
            port = int(s[0])
        except ValueError:
            print "Error: Erroneous port."
            return 1
    else:
        port = 6667
    channel = args[1]
    nickname = args[2]
    password = None
    if (len(args) > 3):
        password = args[3]

    bot = ConfBot(channel, nickname, server, port, password)
    bot.start()


class Command(BaseCommand):
    help = "Usage: confbot.py <server[:port]> <channel> <nickname> [nickserv pass]"

    def handle(self, *args, **options):
        start_confbot(*args)

def main():
    import sys
    start_confbot(sys.argv[1:])

if __name__ == "__main__":
    main()
