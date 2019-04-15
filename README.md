# Reddit email sender
> Send email based on researched keys

Reddit email sender will send emails, from mailgun, to the specify emails address.

The email is base on the reddit search (**[example](https://www.reddit.com/r/learnpython/search?q=aws%20OR%20docker&restrict_sr=1&t=month)**), it include by default one month old posts.

Reddit email sender will sent email only if new comments are present and it will remove from the database posts older then one month.


## Requirements
* [**Mailgun**](https://www.mailgun.com) - 300 free email per day, no credid card required - [Docs](https://documentation.mailgun.com/en/latest/user_manual.html#sending-via-api)
* [**Reddit-API**](https://github.com/reddit-archive/reddit/wiki/OAuth2) and [rules](https://www.reddit.com/wiki/api)

## Usage
* Create a Mailgun account
* Add Mailgun credentials to `mailgun_secrets.yml` file
* Register for reddit API
* Add reddit API secrets to `praw.ini` file, under `[bot1]`
* Define subreddit and search parameters on `subreddits_parameters.yml` file
* Setup Cron or TaskScheduler to run `main.py`

## Note
* This is a beginner project.
* A `db` folder will be created in the running directory
* Circular `logs` file in the running directory with traceback


## Example
<img src="https://i.imgur.com/nI4Fwsh.jpg" width="500"> 
