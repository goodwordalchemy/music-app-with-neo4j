To run local dev server on OSX:

1.) Make sure you have docker intalled.  If you don't know what docker is, just do the [tutorial on the site](https://docs.docker.com/mac/).  That will be more than enough to get you up and running with this dev environment.  In a word, docker is used here so that it is super easy for you to get a dev server up and running.

1.) a.) make sure your docker machine is started (osx).  `$ docker-machine start`.

2.) Setup your spotify credentials.  Follow the instructions in the [user guide for the spotify api](https://developer.spotify.com/web-api/tutorial/).  Particularly up to the heading "Getting the Client ID and Secret Key."  For the redirect uri, you should use `http://localhost:5000/callback/spotify`, but it doesn't actually matter

3.) get the ip address for your docker machine.  Just run `docker-machine ip` and the ip will be printed.

4.) set up your environment file.  make a file called `.env`.  (`touch .env`).  The contents of the file should look like this (where anything inside of angled braces (<>) is for you to replace as guided.:

```bash
NEO4J_AUTH=neo4j:<password of your choosing>
NEO4J_HOSTPORT=http://<ip address returned from "docker-machine ip" that you ran above:7474
SPOTIFY_CLIENT_ID=<Client Id that spotify assigns to you when you created the app in step 2>
SPOTIFY_CLIENT_SECRET=<Client secret that spotify assigns to you in step 2>
```

4.) to start the machine, copy and paste the following into your command line `docker-compose run -d --service-ports web python -m run`

5.) go to <the ip address returned from `docker-machine ip`>:5000.  You can run `open http://$(docker-machine ip):5000` if you want to be fancy.

6.) to kill the server or if you get an error about port 5000 being occupied, run `docker-compose stop`.  You can restart by repeating step 4.