"""models.py - This file contains the class definitions for the Datastore
entities used by the Game. Because these classes are also regular Python
classes they can include methods (such as 'to_form' and 'new_game')."""

import random
from datetime import date
from protorpc import messages
from google.appengine.ext import ndb


class User(ndb.Model):
    """User profile"""

    name = ndb.StringProperty(required=True)
    email = ndb.StringProperty(required=True)
    game_wins = ndb.IntegerProperty(default=0)
    game_losses = ndb.IntegerProperty(default=0)
    total_games_played = ndb.IntegerProperty(default=0)

    def to_form(self):
        form = UserForm(name=self.name,
                        email=self.email,
                        game_wins=self.game_wins,
                        total_games_played=self.total_games_played,
                        game_losses=self.game_losses)
        return form

    # Increment wins for every winning game
    def add_win(self):
        self.game_wins += 1
        self.total_games_played += 1
        self.put()

    # Increment losses for every losing game
    def add_loss(self):
        self.game_losses += 1
        self.total_games_played += 1
        self.put()


class Game(ndb.Model):
    """Game object"""
    player1 = ndb.KeyProperty(required=True, kind='User')
    player2 = ndb.KeyProperty(required=True, kind='User')
    # first player's word
    player1_word = ndb.StringProperty(required=True)
    # second player's word
    player2_word = ndb.StringProperty(required=True)
    # PickledProperty to store guessed letters in a list
    player1_letter_guess = ndb.PickleProperty()
    # PickledProperty to store guessed letters in a list
    player2_letter_guess = ndb.PickleProperty()
    # If guessed letter is correct, store in this list
    player1_word_right = ndb.PickleProperty()
    # If guessed letter is correct, store in this list
    player2_word_right = ndb.PickleProperty()
    attempts_remaining_player1 = ndb.IntegerProperty()
    attempts_remaining_player2 = ndb.IntegerProperty()
    game_over = ndb.BooleanProperty(required=True, default=False)
    winner = ndb.KeyProperty(kind='User')
    message = ndb.StringProperty()
    # determines who is next to play
    next_round = ndb.KeyProperty(kind='User')

    @classmethod
    def new_game(cls, player1, player2, player1_word, player2_word):
        """Creates and returns a new game"""
        game = Game(player1=player1,
                    player2=player2,
                    player1_word=player1_word,
                    player2_word=player2_word,
                    player1_letter_guess=[],
                    player2_letter_guess=[],
                    player1_word_right=[],
                    player2_word_right=[],
                    attempts_remaining_player1=10,
                    attempts_remaining_player2=10,
                    next_round=player1)
        game.put()
        return game

    def check_guess(self, right_word, guess, word_right):
        """Count repeated letters in the word and compare."""
        if guess in list(right_word):
            right_word_dict = {}
            for i in set(right_word):
                x = right_word.count(i, 0, len(right_word))
                right_word_dict[i] = x
            for key in right_word_dict:
                if key == guess:
                    t = right_word_dict[key]
            for m in range(0, t):
                word_right.append(guess)

    def to_form(self, message):
        """Returns a GameForm representation of the Game"""
        form = GameForm(urlsafe_key=self.key.urlsafe(),
                        player1_word=str(self.player1_word),
                        player2_word=str(self.player2_word),
                        player1=str(self.player1.get().name),
                        player2=str(self.player2.get().name),
                        player1_letter_guess=str(self.player1_letter_guess),
                        player2_letter_guess=str(self.player2_letter_guess),
                        attempts_remaining_player1=int(self.attempts_remaining_player1),
                        attempts_remaining_player2=int(self.attempts_remaining_player2),
                        player1_word_right=str(self.player1_word_right),
                        player2_word_right=str(self.player2_word_right),
                        game_over=self.game_over,
                        message=message
                        )

        return form

    def end_game(self, winner, loser):
        """Ends the game"""
        self.winner = winner
        self.game_over = True
        self.put()
        loser = loser
        score = Score(date=date.today(), winner=winner, loser=loser)
        score.put()

        # Update the user model
        winner.get().add_win()
        loser.get().add_loss()


class Score(ndb.Model):
    """Score object"""
    date = ndb.DateProperty(required=True)
    winner = ndb.KeyProperty(required=True)
    loser = ndb.KeyProperty(required=True)

    def to_form(self):
        return ScoreForm(date=str(self.date),
                         winner=self.winner.get().name,
                         loser=self.loser.get().name)


class GameForm(messages.Message):
    """GameForm for outbound game state information"""
    urlsafe_key = messages.StringField(1, required=True)
    player1_word = messages.StringField(2, required=True)
    player2_word = messages.StringField(3, required=True)
    player1_letter_guess = messages.StringField(4)
    player2_letter_guess = messages.StringField(5)
    attempts_remaining_player1 = messages.IntegerField(6)
    attempts_remaining_player2 = messages.IntegerField(7)
    player1 = messages.StringField(8, required=True)
    player2 = messages.StringField(9, required=True)
    game_over = messages.BooleanField(10, required=True)
    winner = messages.StringField(11)
    player1_word_right = messages.StringField(14)
    player2_word_right = messages.StringField(15)
    message = messages.StringField(13)


class GameForms(messages.Message):
    """Container for multiple GameForm"""
    items = messages.MessageField(GameForm, 1, repeated=True)


class NewGameForm(messages.Message):
    """Used to create a new game"""
    player1 = messages.StringField(1, required=True)
    player2 = messages.StringField(2, required=True)
    player1_word = messages.StringField(3, required=True)
    player2_word = messages.StringField(4, required=True)


class MakeMoveForm(messages.Message):
    """Used to make a move in an existing game"""
    user_name = messages.StringField(1, required=True)
    guess = messages.StringField(2, required=True)


class ScoreForm(messages.Message):
    """ScoreForm for outbound Score information"""
    date = messages.StringField(1, required=True)
    winner = messages.StringField(2, required=True)
    loser = messages.StringField(3, required=True)


class ScoreForms(messages.Message):
    """Return multiple ScoreForms"""
    items = messages.MessageField(ScoreForm, 1, repeated=True)


class StringMessage(messages.Message):
    """StringMessage-- outbound (single) string message"""
    message = messages.StringField(1, required=True)


class UserForm(messages.Message):
    """User Form for outbound User information"""
    name = messages.StringField(1, required=True)
    email = messages.StringField(2)
    game_wins = messages.IntegerField(3)
    game_losses = messages.IntegerField(4)
    total_games_played = messages.IntegerField(5)


class UserForms(messages.Message):
    """Return multiple UserForms"""
    items = messages.MessageField(UserForm, 1, repeated=True)
