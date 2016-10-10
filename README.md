Hangman Game API
===================

**Hangman Game API** is a two player game where each player will guess each other's word within 10 attempts. Users will start off creating a game via 'new_game' endpoint which will provide the users a 'urlsafe_game_key'. Each game will have a unique 'urlsafe_game_key'. Users will be allowed to create several games indenpendent of other active games. Pass that key to 'make_move' endpoint and take turns guessing a letter trying to identify the correct word identified by the opposite player. Every hour, an email will be sent out to users informing any active games they have participated in. The number of wins, losses, and total games played will be stored for score keeping.

### TABLE OF CONTENTS
-------------

1. How to use
2. Files
3. Models
4. Endpoints

#### HOW TO USE

1. Add these existing files/directory to Google App Engine.
2. Update the app ID in app.yaml.
2. Go to localhost:"your port number"/_ah/api/explorer.
3. First create two users using create_user endpoint.
4. Create a game using new_game endpoint.
5. Take turns by making a move using make_move endpoint.

#### FILES

- api.py: Contains all theendpoints and playing logic.
- app.yaml: App configuration. This is the file where you will need to add your app ID.
- cron.yaml: Cronjob configuration to send out reminder emails.
- main.py: Handler for taskqueue handler which contains body information.
- models.py: Entity and message definitions including helper methods.
- utils.py: Helper function for retrieving ndb.Models by urlsafe Key

#### MODEL

## User
 - Stores the user_name and email of the players

## Game
 - Stores the game current state such as the players' user_name.
 - Stores the letters players have guessed and the answer
 - Keeps track of how many attempts players have left.
 - Keeps track who's turn will be next to guess the letter.

## Score
 - Stores all games stats such as the winners and losers.

#### ENDPOINTS

### create_user
 - Path: 'user'
 - Method: POST
 - Parameters: user_name, email
 - Returns: Message confirming that the user has been created.
 - Description: Creates a new User. user_name provided must be unique.
User can also provide an email. It will raise a ConflictException 
if a User with that user_name already exists.

### get_user_rankings
 - Path: 'user/rankings'
 - Method: GET
 - Parameters: None
 - Returns: UserForms
 - Description: Returns all the user stats froms wins to losses for each user

### new_game
 - Path: 'game'
 - Method: POST
 - Parameters: player1, player1_word, player2, player2_word
 - Returns: GameForm.
 - Description: Creates a new Game. user_name provided must correspond to an
existing user. It will raise a NotFoundException if not. It will also raise an
BadRequestException if it fails to create a game.

### get_game
 - Path: 'game/{urlsafe_game_key}'
 - Method: GET
 - Parameters: urlsafe_game_key
 - Returns: GameForms.
 - Description: Returns the current state of a game. It will raise a NotFoundException
 if it cannot find the game.

### get_user_games
 - Path: 'user/games'
 - Method: GET
 - Parameters: email, user_name
 - Returns: GameForms.
 - Description: Returns the user's current active games. User_name must be validated
 otherwise it will raise a BadRequestException.

### get_all_games
 - Path: 'all_games'
 - Method: GET
 - Parameters: None
 - Returns: GameForms.
 - Description: Returns the all games and its current state.

### cancel_game
 - Path: 'game/{urlsafe_game_key}'
 - Method: DELETE
 - Parameters: urlsafe_game_key
 - Returns: Message confirming that the game is deleted.
 - Description: Deletes a specified game. The game can only be deleted if the game 
 was not completed otherwise raise a BadRequestException. If the game does not exist, it will raise
 a NotFoundException.

### make_move
 - Path: 'game/{urlsafe_game_key}'
 - Method: PUT
 - Parameters: urlsafe_game_key, RequestBody[user_name, guess]
 - Returns: GameForm.
 - Description: Accepts a 'guess' letter and returns the updated state of the game. Every letter
 that the player guesses will be stored and reduces the number of attempts by 1 otherwise raise a
 BadRequestException if attempts reaches 0. The game will first determine if it exists and has not 
 ended otherwise raise a NotFoundException. If the letter was guessed before it will raise a 
 BadRequestException. Pass the guessed letter and determine if the letter exists in the word and store
 the correct letter in a list. Whoever identifies the correct word will be identified as the winner. Once 
 the winner is identified, current game state will be set to 'True' as game is completed.

### get_game_history
 - Path: 'game/{urlsafe_game_key}/history'
 - Method: GET
 - Parameters: urlsafe_game_key
 - Returns: Message confirming the list of moves performed by each player vs. the letters that were guessed correctly.
 - Description: Displays each players total letters guessed and the letters that were guessed correctly.

### get_scores
- Path: 'scores'
- Method: GET
- Parameters: None
- Returns: ScoreForms.
- Description: Returns all Scores in the database.

### get_user_scores
- Path: 'scores/user/{user_name}'
- Method: GET
- Parameters: user_name, email
- Returns: ScoreForms.
- Description: Returns all Scores recorded by the user.
Will raise a NotFoundException if the User does not exist.

### get_average_attempts
- Path: 'games/average_attempts'
- Method: GET
- Parameters: None
- Returns: Message confirming the average attempts of all the games.
- Description: Returns the average attempts of all the games by player1 and player2.