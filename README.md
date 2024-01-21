This is a game resource tracking tool developed based on the Soulforged.

As it is intended for players to share in-game information, we recommend that you use our server and database for operations. 
This allows you to immediately enjoy the information already established by others and share your information with everyone. 
You can find the URL for the SF Resource map in the game settings > after joining Discord.

If you wish to use this code and set up your own database and server, you will first need to establish a MongoDB. 
Then, update the connection URL containing the username and password in the MongoClient variable in pagefile/init.py, and set your own app_secret_key.
