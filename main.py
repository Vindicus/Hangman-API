#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
from google.appengine.api import mail, app_identity
from google.appengine.ext import ndb
from api import HangmanAPI
from utils import get_by_urlsafe

from models import User, Game


class SendReminderEmail(webapp2.RequestHandler):
    def get(self):
        """Send a reminder email to each User with an email who has
        games in progress. Body includes a count of active games and their
        urlsafe keys
        Called every hour using a cron job"""
        app_id = app_identity.get_application_id()
        users = User.query(User.email != None)

        for user in users:
            games = Game.query(ndb.OR(Game.player1 == user.key,
                               Game.player2 == user.key)).\
                               filter(Game.game_over == False)
            # performs the total count results
            if games.count() >= 1:
                subject = 'This is a reminder!'
                body = 'Hello {}, you have a total of {} games in progress.\
                        Their' \
                       ' url safe keys are: {}'.\
                    format(user.name,
                           games.count(),
                           ', '.join(game.key.urlsafe() for game in games))
                # This will send test emails, the arguments to send_mail are:
                # from, to, subject, body
                mail.send_mail('noreply@{}.appspotmail.com'.format(app_id),
                               user.email,
                               subject,
                               body)


class UpdateAverageMovesRemaining(webapp2.RequestHandler):
    def post(self):
        """Update game listing announcement in memcache."""
        HangmanAPI._cache_average_attempts()
        self.response.set_status(204)

app = webapp2.WSGIApplication([
    ('/crons/send_reminder', SendReminderEmail),
    ('/tasks/cache_average_attempts', UpdateAverageMovesRemaining),
], debug=True)
