import yaml
# sudo pip install pyyaml
import re
import random
import smtplib
import datetime
import pytz
import time
import socket
import sys
import getopt
import os
import io

help_message = '''
To use, fill out config.yml with your own participants. You can also specify
DONT-PAIR so that people don't get assigned their significant other.

To send by email, you'll also need to specify your mail server settings.
An example is provided for routing mail through gmail.

For more information, see README.
'''

REQRD = (
    'SMTP_SERVER',
    'SMTP_PORT',
    'USERNAME',
    'PASSWORD',
    'TIMEZONE',
    'PARTICIPANTS',
    'DONT-PAIR',
    'FROM',
    'SUBJECT',
    'MESSAGE',
)

HEADER = """Date: {date}
Content-Type: text/plain; charset="utf-8"
Message-Id: {message_id}
From: {frm}
To: {to}
Subject: {subject}

"""

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.yml')

class Person:
    def __init__(self, name, email, invalid_matches):
        self.name = name
        self.email = email
        self.invalid_matches = invalid_matches

    def __str__(self):
        return "%s <%s>" % (self.name, self.email)

class Pair:
    def __init__(self, giver, receiver):
        self.giver = giver
        self.receiver = receiver

    def __str__(self):
        return "%s ---> %s" % (self.giver.name, self.receiver.name)

def parse_yaml(yaml_path=CONFIG_PATH):
    return yaml.load(io.open(yaml_path, encoding='utf-8'))

def choose_receiver(giver, receivers):
    choice = random.choice(receivers)
    if choice.name in giver.invalid_matches or giver.name == choice.name:
        if len(receivers) is 1:
            raise Exception('Only one receiver left, try again')
        return choose_receiver(giver, receivers)
    else:
        return choice

def create_pairs(g, r):
    givers = g[:]
    receivers = r[:]
    pairs = []
    for giver in givers:
        try:
            receiver = choose_receiver(giver, receivers)
            receivers.remove(receiver)
            pairs.append(Pair(giver, receiver))
        except:
            return create_pairs(g, r)
    return pairs


class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg


def main(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        try:
            opts, args = getopt.getopt(argv[1:], "shc", ["send", "txt", "help"])
        except getopt.error as msg:
            raise Usage(msg)

        # option processing
        send = False
        txt = False
        for option, value in opts:
            if option in ("-s", "--send"):
                send = True
            if option in ("-t", "--txt"):
                txt = True
            if option in ("-h", "--help"):
                raise Usage(help_message)

        config = parse_yaml()
        for key in REQRD:
            if key not in config.keys():
                raise Exception(
                    'Required parameter %s not in yaml config file!' % (key,))

        participants = config['PARTICIPANTS']
        dont_pair = config['DONT-PAIR']
        if len(participants) < 2:
            raise Exception('Not enough participants specified.')

        givers = []
        for person in participants:
            # only try to find email addresses when --send option is active (to allow lists without them)
            if send:
                try:
                    name, email = re.match(r'([^<]*)<([^>]*)>', person).groups()
                except:
                    raise Exception('E-Mail address cannot be read for all users. Check formatting.')
            else:
                name = re.match(r'([^<]*)', person).groups()[0]
                email = []
            name = name.strip()
            invalid_matches = []
            for pair in dont_pair:
                names = [n.strip() for n in pair.split(',')]
                if name in names:
                    # is part of this pair
                    for member in names:
                        if name != member:
                            invalid_matches.append(member)
            person = Person(name, email, invalid_matches)
            givers.append(person)

        receivers = givers[:]
        pairs = create_pairs(givers, receivers)

        if txt:
            folder = "pairs"
            if not os.path.exists(folder):
        	    os.mkdir(folder)
            for the_file in os.listdir(folder):         # Clear directory
                file_path = os.path.join(folder, the_file)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                except Exception as e:
                    print (e)
            for pair in pairs:
                f = open("pairs/Santee of " + pair.giver.name + '.txt','w')
                f.write(config['MESSAGE'].format(santa=pair.giver.name, santee=pair.receiver.name))
                f.close()

        if not (send or txt):
            print( """Test pairings:\n\n%s\n\nTo send out emails with new pairings,
call with the --send argument:\n\t$ python secret_santa.py --send\n
To generate txt files to distribute manually call with the --text argument:\n\t$ python secret_santa.py --txt\n""" % ("\n".join([str(p) for p in pairs])))

        if send:
            print( "Initialising SMTP connection" )
            server = smtplib.SMTP(config['SMTP_SERVER'], config['SMTP_PORT'])
            print( "Connected to SMTP server" )
            if config['SMTP_PORT'] != 25:
                server.starttls()
            print( "Logging in as <%s> to send mail" % config['USERNAME'] )
            server.login(config['USERNAME'], config['PASSWORD'])
        for idx, pair in enumerate(pairs):
            print( "Processing pair %d of %d" % (idx + 1, len(pairs)) )
            zone = pytz.timezone(config['TIMEZONE'])
            now = zone.localize(datetime.datetime.now())
            date = now.strftime('%a, %d %b %Y %T %Z') # Sun, 21 Dec 2008 06:25:23 +0000
            message_id = '<%s@%s>' % (str(time.time())+str(random.random()), socket.gethostname())
            frm = config['FROM']
            to = pair.giver.email
            subject = config['SUBJECT'].format(santa=pair.giver.name, santee=pair.receiver.name)
            body = (HEADER+config['MESSAGE']).format(
                date=date,
                message_id=message_id,
                frm=frm,
                to=to,
                subject=subject,
                santa=pair.giver.name,
                santee=pair.receiver.name,
            )
            if send:
                result = server.sendmail(frm, [to], body.encode('UTF-8'))
                print("Emailed %s <%s>" % (pair.giver.name, to))

        if send:
            server.quit()

    except Usage as err:
        print( sys.stderr, sys.argv[0].split("/")[-1] + ": " + str(err.msg))
        print( sys.stderr, "\t for help use --help")
        return 2


if __name__ == "__main__":
    sys.exit(main())
