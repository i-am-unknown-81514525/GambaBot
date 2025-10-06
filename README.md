# GambaBot
Gamble! Gamble! Gamble everything with cryptographically verifiable fairness and that I definitiely didn't and cannot rig the game 

Try it out [here](https://discord.com/oauth2/authorize?client_id=1424521785772212344)

### How it work
This work by having the server pre-generate a secret for a game, and provide you the hash of the secret (so you can verify that I am not cheating by changing it), and you provide a client secret which the server and client secret is mixed as defined in the code that you can read. *If you implement it correctly, which for the UI, it doesn't actually show the server secret first although the API make it possible to do so*

### How to setup
This project wouldn't be possible to be run by packaging into a executable or Pypi as you need to run 2 process which 1 of them is the discord bot and another is the webserver (If you want to try it, check out the demo which is the discord bot invite link [here](https://discord.com/oauth2/authorize?client_id=1424521785772212344), which you can run it anywhere with User Install or in the server by anyone if you do server install):

1. Setup the `.env`
```
DISCORD_TOKEN=... # Go to discord developer portal and create a application, then get the bot token from bot panel
JWT_SECRET=verysecretjwtsecret # A random secret
DISCORD_CLIENT_ID= # Go to discord developer portal and create a application, then get the client ID from OAuth2 panel
DISCORD_CLIENT_SECRET= # Same as above
DISCORD_REDIRECT_URI= # Just put localhost:8000/auth/discord/callback for now, not used
INTERNAL_LINK=http://server:8000 # Or any other way the bot can send request to server
```
2. Run `docker compose up -d --build`

### Video Demo

https://github.com/user-attachments/assets/afc191e4-4c10-4db1-b7bc-49666351d243
