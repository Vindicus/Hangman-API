"""Hangman API is a two player game where each player will guess each other's word within 10 attempts. Users will start off creating a game via 'new_game' endpoint which will provide the users a 'urlsafe_game_key'. Each game will have a unique 'urlsafe_game_key'. Users will be allowed to create several games indenpendent of other active games. Pass that key to 'make_move' endpoint and take turns guessing a letter trying to identify the correct word identified by the opposite player."""

import logging
import endpoints
import re
from google.appengine.ext import ndb
from protorpc import remote, messages
from google.appengine.api import memcache
from google.appengine.api import taskqueue
from models import (
    User,
    Game,
    Score,
)
from models import (
    StringMessage,
    NewGameForm,
    GameForm,
    GameForms,
    MakeMoveForm,
    ScoreForms,
    UserForm,
    UserForms,
)
from utils import get_by_urlsafe


NEW_GAME_REQUEST = endpoints.ResourceContainer(NewGameForm)
GET_GAME_REQUEST = endpoints.ResourceContainer(
        urlsafe_game_key=messages.StringField(1),)
MAKE_MOVE_REQUEST = endpoints.ResourceContainer(
    MakeMoveForm,
    urlsafe_game_key=messages.StringField(1),)
USER_REQUEST = endpoints.ResourceContainer(user_name=messages.StringField(1),
                                           email=messages.StringField(2))

MEMCACHE_MOVES_REMAINING = 'MOVES_REMAINING'


@endpoints.api(name='hangman', version='v1')
class HangmanAPI(remote.Service):
    """Game API"""
    @endpoints.method(request_message=USER_REQUEST,
                      response_message=StringMessage,
                      path='user',
                      name='create_user',
                      http_method='POST')
    def create_user(self, request):
        """Create a User. Requires a unique username and an email"""
        if User.query(User.name == request.user_name).get():
            raise endpoints.ConflictException(
                    'User already exists!')
        if request.user_name is None or request.email is None:
            raise endpoints.BadRequestException('Enter a username and email')
        user = User(name=request.user_name, email=request.email)
        user.put()
        return StringMessage(message='User {} created!'.format(
                request.user_name))

    @endpoints.method(response_message=UserForms,
                      path='user/ranking',
                      name='get_user_rankings',
                      http_method='GET')
    def get_user_rankings(self, request):
        """Return all wins, losses, and games total played."""
        # Players with the most wins will be ranked first.
        users = User.query().order(-User.game_wins).fetch()
        return UserForms(items=[user.to_form() for user in users])

    @endpoints.method(request_message=NEW_GAME_REQUEST,
                      response_message=GameForm,
                      path='game',
                      name='new_game',
                      http_method='POST')
    def new_game(self, request):
        """Creates new game"""
        player1 = User.query(User.name == request.player1).get()
        player2 = User.query(User.name == request.player2).get()
        if not player1 or not player2:
            raise endpoints.NotFoundException(
                    'One or more of the player name does not exist!')
        try:
            player1_word = request.player1_word
            player2_word = request.player2_word
            game = Game.new_game(player1.key, player2.key,
                                 player1_word, player2_word)
            return game.to_form("Created game successfully")
        except:
            raise endpoints.BadRequestException('Failed to initiate new game')

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='get_game',
                      http_method='GET')
    def get_game(self, request):
        """Return the current game state."""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game:
            return game.to_form("Time to make a move!")
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=GameForms,
                      path='user/games',
                      name='get_user_games',
                      http_method='GET')
    def get_user_games(self, request):
        """Return a User's active games"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.BadRequestException('User not found!')
        games = Game.query(ndb.OR(Game.player1 == user.key,
                           Game.player2 == user.key)).\
                           filter(Game.game_over == False)
        return GameForms(items=[game.to_form("User games retrieved") for game in games])

    @endpoints.method(response_message=GameForms,
                      path='all_games',
                      name='get_all_games',
                      http_method='GET')
    def get_all_games(self, request):
        """Retrieve all games"""
        return GameForms(items=[game.to_form("All games \
                         retrieved") for game in Game.query()])

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=StringMessage,
                      path='game/{urlsafe_game_key}',
                      name='cancel_game',
                      http_method='DELETE')
    def cancel_game(self, request):
        """Delete a game where game_over is false"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if game and game.game_over is False:
            game.key.delete()
            return StringMessage(message='Game with key: {} deleted.'.format(request.urlsafe_game_key))
        elif game and game.game_over is True:
            raise endpoints.BadRequestException('Game is already over, cannot delete!')
        else:
            raise endpoints.NotFoundException('Game not found!')

    @endpoints.method(request_message=MAKE_MOVE_REQUEST,
                      response_message=GameForm,
                      path='game/{urlsafe_game_key}',
                      name='make_move',
                      http_method='PUT')
    def make_move(self, request):
        """Makes a move. Returns a game state with message"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if not game:
            raise endpoints.NotFoundException('Game not found')
        if game.game_over:
            raise endpoints.NotFoundException('Game already over')

        # Get user name
        user = User.query(User.name == request.user_name).get()
        if user is None:
            raise endpoints.NotFoundException('User not found')
        else:
            if user.key == game.player1:
                active_player = "player1"
            else:
                active_player = "player2"
        if user.key != game.next_round and \
           game.attempts_remaining_player1 != 0 and \
           game.attempts_remaining_player2 != 0:
            raise endpoints.BadRequestException('Not your turn yet!')

        guess = request.guess

        # Verify how many attempts left
        if game.attempts_remaining_player1 == 0:
            raise endpoints.BadRequestException('Player 1 have 0 attempts!')
        elif game.attempts_remaining_player2 == 0:
            raise endpoints.BadRequestException('Player 2 have 0 attempts!')

        validateGuess = re.compile('[a-zA-Z]')
        if not validateGuess.match(guess) or len(guess) > 1:
            raise endpoints.BadRequestException('Enter only 1 character!')

        # Validate if the guess was not guessed before by checking in the list
        if active_player == "player1":
            if guess in game.player1_letter_guess:
                raise endpoints.BadRequestException('You already guessed that letter!')
            else:
                game.player1_letter_guess.append(guess)
                # player guest switches to next player
                game.next_round = game.player2
                if game.attempts_remaining_player1 == 1:
                    game.attempts_remaining_player1 -= 1
                    game.message = "user was hanged"
                else:
                    game.attempts_remaining_player1 -= 1

        if active_player == "player2":
            if guess in game.player2_letter_guess:
                raise endpoints.BadRequestException('You already guessed that letter!')
            else:
                game.player2_letter_guess.append(guess)
                game.next_round = game.player1
                if game.attempts_remaining_player2 == 1:
                    game.attempts_remaining_player2 -= 1
                    game.message = "user was hanged"
                else:
                    game.attempts_remaining_player2 -= 1

        # Validate if guess exists in the player's word and store in a list
        if active_player == 'player1':
            game.check_guess(game.player2_word, guess, game.player1_word_right)

        if active_player == 'player2':
            game.check_guess(game.player1_word, guess, game.player2_word_right)

        # by default, both are set to False as non-winners
        player2_pass = False
        player1_pass = False

        if len(game.player1_word_right) == len(game.player2_word):
                player1_pass = True

        if len(game.player2_word_right) == len(game.player1_word):
                player2_pass = True

        if game.attempts_remaining_player1 == 0 and \
           game.attempts_remaining_player2 == 0:
            game.key.delete()
            raise endpoints.NotFoundException('Tie, no winner in this game!')

        if player1_pass:
            game.end_game(game.player1, game.player2)

        if player2_pass:
            game.end_game(game.player2, game.player1)

        game.put()

        if game.winner is None:
            game.message = "No winner at this time. Keep going!"
        else:
            game.message = "User {} wins".format(game.winner)

        return game.to_form(game.message)

        taskqueue.add(url='/tasks/cache_average_attempts')
        taskqueue.add(url='/tasks/send_move',
                      params={'user_key': game.next_round.urlsafe(),
                              'game_key': game.key.urlsafe()})

    @endpoints.method(request_message=GET_GAME_REQUEST,
                      response_message=StringMessage,
                      path='game/{urlsafe_game_key}/history',
                      name='get_game_history',
                      http_method='GET')
    def get_game_history(self, request):
        """Return a Game's move history"""
        game = get_by_urlsafe(request.urlsafe_game_key, Game)
        if not game:
            raise endpoints.NotFoundException('Game not found')
        return StringMessage(message=str("Player1 total moves: " +
                                         str(game.player1_letter_guess) +
                                         " Player1 guessed these letters correctly: " +
                                         str(game.player1_word_right) +
                                         " Correct word to guess was: " +
                                         str(game.player2_word) +
                                         " Player2 total moves: " +
                                         str(game.player2_letter_guess) +
                                         " Player2 guessed these letters correctly: " + str(game.player1_word_right) +
                                         " Correct word to guess was: " +
                                         str(game.player1_word)))
        

    @endpoints.method(response_message=ScoreForms,
                      path='scores',
                      name='get_scores',
                      http_method='GET')
    def get_scores(self, request):
        """Return all scores"""
        return ScoreForms(items=[score.to_form() for score in Score.query()])

    @endpoints.method(request_message=USER_REQUEST,
                      response_message=ScoreForms,
                      path='scores/user/{user_name}',
                      name='get_user_scores',
                      http_method='GET')
    def get_user_scores(self, request):
        """Returns all of an individual User's scores"""
        user = User.query(User.name == request.user_name).get()
        if not user:
            raise endpoints.NotFoundException(
                    'This user does not exist!')
        scores = Score.query(Score.winner == user.key or
                             Score.loser == user.key)
        return ScoreForms(items=[score.to_form() for score in scores])

    @endpoints.method(response_message=StringMessage,
                      path='games/average_attempts',
                      name='get_average_attempts_remaining',
                      http_method='GET')
    def get_average_attempts(self, request):
        """Get the cached average moves remaining"""
        taskqueue.add(url='/tasks/cache_average_attempts')
        return StringMessage(message=memcache.get(MEMCACHE_MOVES_REMAINING or ''))

    @staticmethod
    def _cache_average_attempts():
        """Populates memcache with the average moves remaining of Games"""
        games = Game.query(Game.game_over == False).fetch()
        if games:
            count = len(games)
            total_attempts_remaining = sum([game.attempts_remaining_player1 +
                                           game.attempts_remaining_player2
                                           for game in games])
            average = float(total_attempts_remaining)/count
            memcache.set(MEMCACHE_MOVES_REMAINING,
                         'The average moves remaining is {:.2f}'.format(average))

api = endpoints.api_server([HangmanAPI])
