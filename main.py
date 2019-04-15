"""
Send an email for each subreddit with all the topic found base on the search string.
"""

import logging
from logging.handlers import RotatingFileHandler
import sys
import yaml
import praw
import requests

from datetime import datetime
from typing import List, Dict
from jinja2 import Environment
from tinydb import TinyDB, Query

logger = logging.getLogger(__name__)

handler = RotatingFileHandler('logs.log', maxBytes=20000, backupCount=1, encoding='utf-8')  # 40KB
handler.setLevel(logging.DEBUG)
file_format = '%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)d] %(module)s: %(message)s'
handler.setFormatter(logging.Formatter(file_format))
logger.addHandler(handler)

# traceback should only go to the file
traceback_log = logging.getLogger('traceback')
traceback_log.propagate = True
traceback_log.setLevel(logging.ERROR)  # print traceback only for errors messages
traceback_log.addHandler(handler)


def log_exception(exc_type, exc_value, traceback):
    logging.getLogger(__name__).error(exc_value)
    logging.getLogger('traceback').error(
        exc_value,
        exc_info=(exc_type, exc_value, traceback), )  # log traceback


sys.excepthook = log_exception


def reddit_post(sub_reddit: praw, search_par: str) -> List[Dict]:
    # Search for posts
    posts = []
    for submission in sub_reddit.search(search_par, sort='relevance', syntax='lucene', time_filter='month'):
        posts.append({
            'id': submission.id,
            'title': submission.title,
            'link': submission.shortlink
            }
        )
    return posts


def post_update(reddit: praw, posts: List[Dict]) -> List[Dict]:
    # comments for posts
    ids = []
    for post in posts:
        submission = reddit.submission(id=f"{post['id']}")
        submission.comments.replace_more(limit=0)
        submission.comment_sort = 'new'
        if submission.comments.list():
            last_comment = submission.comments.list()[-1]
        else:
            continue
        ids.append({
            "sub_id": post['id'],
            "com_id": last_comment.id,
            "title": post['title'],
            "link": post['link']
        })
    logger.warning(f'Posts: {len(ids)}\nEXAMPLE:\n{ids[0]}')
    return ids


def new_posts(ids: List[Dict], db: TinyDB, article: Query) -> List[Dict]:
    # new post/comment to be emailed
    return [result for result in ids if not db.search(
        (article.sub_id.matches(result["sub_id"])) & (article.com_id.matches(result["com_id"])))
            ]


def update_db(new_results: List[Dict], db: TinyDB, ids: List[Dict], article: Query) -> None:
    for result in new_results:
        # if sub present, update it, else insert it
        db.upsert(result, article.sub_id == result["sub_id"])

    # copy all db
    all_db = db.all()
    logger.warning(f'DB original length: {len(all_db)}')
    # remove old db entry not present in the last search
    filtered_db = [x for x in all_db if x in ids]
    db.purge()
    for db_id in filtered_db:
        # reinitialize db
        db.insert(db_id)
    logger.warning(f'DB final length: {len(db.all())}')


def template(posts_data: List[Dict], title: str) -> str:
    # Create a str-html message from a rendered template
    TEMPLATE = '''
    <!DOCTYPE html>
    <html LANG="EN">
    <body>
    <h3>Reddit search "{{ par }}"</h3>
    Posts found: {{ posts|length }}
    <ul>
    {% for post in posts %}
        <li>{{ post['title'] }}</li>
        <li><a href="{{ post['link'] }}">{{ post['link'] }}</a></li>
        <p></p>
    {% endfor %}
    </ul>
    </body>
    </html>
    '''
    return Environment().from_string(TEMPLATE).render(posts=posts_data, par=title)


def send_message(html: str, date_now: str, sub_data: Dict, mailgun: Dict) -> requests:
    return requests.post(
        mailgun['url'],
        auth=("api", mailgun['api-key']),
        data={"from": mailgun['from'],
              "to": mailgun['email-to'],
              "subject": f"Reddit-{sub_data['subreddit'].capitalize()}-{date_now}",
              "html": f"{html}",
              "o:require-tls": True
              }
    )


def data_file() -> List[Dict]:
    with open('subreddits_parameters.yml', 'r') as f:
        return yaml.load(f)


def mailgun_secrets() -> Dict:
    with open('mailgun_secrets.yml', 'r') as f:
        return yaml.load(f)


def main():
    logger.warning(f'---------------NEW_LOGs---------------')
    reddit = praw.Reddit('bot1')
    subreddits = data_file()
    mailgun_credential = mailgun_secrets()
    for sub in subreddits:
        search = sub['search']
        print(f"Processing subreddit {sub['subreddit'].upper()}...")
        logger.warning(f"Processing subreddit {sub['subreddit'].upper()}...")
        # reddit read-only instance
        subreddit = reddit.subreddit(sub['subreddit'])

        date = datetime.today().strftime("%y-%m-%d")
        db = TinyDB(f"db/posts_data-{sub['subreddit']}.json", indent=4)
        db_query = Query()
        reddit_posts = reddit_post(subreddit, search)
        posts = post_update(reddit, reddit_posts)
        data = new_posts(posts, db, db_query)

        if data:
            msg = template(data, search)
            response = send_message(msg, date, sub, mailgun_credential)
            update_db(data, db, posts, db_query)
            if response.status_code == requests.codes.ok:
                print(f'Email --SENT-- New updates: {len(data)}')
                logger.warning(f'Email --SENT-- New updates: {len(data)}')
            else:
                print('Email --FAILED--')
                response.raise_for_status()
        else:
            print(f'--No new post/comment--')
            logger.warning(f'--No new post/comment--')


if __name__ == "__main__":
    main()
