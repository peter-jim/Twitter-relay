import os
import pathlib
from datetime import datetime, timezone

import dotenv
from loguru import logger
import tweepy
from sqlalchemy.exc import IntegrityError

from flaskr.models import Interaction
from flaskr import db, create_app

dotenv.load_dotenv(dotenv_path=pathlib.Path.home() / '.x_sync' / '.env')
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")

BEARER_TOKEN = os.getenv("BEARER_TOKEN")


class DataCollector:
    MAX_RESULTS = 100

    def __init__(self, client: tweepy.Client, media_account: str, from_date: datetime):
        self.client = client
        self.media_account = media_account
        self.interactions = []

        # 检查是否是utc时间
        if not isinstance(from_date, datetime):
            raise TypeError('from_date must be of type datetime')
        if from_date.tzinfo != timezone.utc:
            raise ValueError('from_date must be in UTC')

        self.start_time = from_date.strftime('%Y-%m-%dT%H:%M:%SZ')

    def get_user_id(self):
        resp = self.client.get_user(username=self.media_account)
        # logger.info(f'get_user_id: {resp}')

        if resp.get('errors'):
            raise ValueError("user not found")
        return resp["data"]["id"]

    def get_tweets(self, uid: int):
        tweets = []
        # 排除 replies
        for resp in tweepy.Paginator(
                self.client.get_users_tweets,
                max_results=DataCollector.MAX_RESULTS,
                exclude=["replies"],
                id=uid,
                start_time=self.start_time,
                tweet_fields=['created_at', 'conversation_id']
        ):
            # logger.info("*" * 80)
            if resp.get('errors'):
                raise ValueError("tweet not found")

            for data in resp["data"]:
                time_str = data["created_at"]
                tweet_dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                tweet = {
                    "tweet_id": data["id"],
                    "created_at": tweet_dt,  # datetime.datetime utc
                    "conversation_id": data["conversation_id"],
                }
                # logger.info("text: {}, id: {}, created_at: {}, conversation_id: {}", data["text"], data["id"],
                #             data["created_at"], data["conversation_id"])
                tweets.append(tweet)

        return tweets

    def get_like_interactions(self, tweet):
        # 获取不到点赞行为的时间点
        likes_interactions = []
        tweet_id = tweet["tweet_id"]
        tweet_at = tweet["created_at"]
        for resp in tweepy.Paginator(
                self.client.get_liking_users,
                max_results=DataCollector.MAX_RESULTS,
                id=tweet_id,
                user_auth=True,
                # user_fields=['id', 'username', 'profile_image_url'],
        ):
            # logger.info(f"resp:{resp}")
            if resp.data:
                for data in resp.data:
                    likes_interactions.append({
                        "media_account": self.media_account,
                        "user_id": data.id,
                        "username": data.username,
                        "avatar_url": data.profile_image_url,
                        "interaction_type": "likes",
                        "interaction_content": "",
                        "interaction_time": tweet_at,  # likes 没有创建时间
                        "post_id": tweet_id,
                        "post_time": tweet_at,
                    })
                    logger.info("likes_interactions:{}", {
                        "media_account": self.media_account,
                        "user_id": data.id,
                        "username": data.username,
                        "avatar_url": data.profile_image_url,
                        "interaction_type": "likes",
                        "interaction_content": "",
                        "interaction_time": tweet_at,  # likes 没有创建时间
                        "post_id": tweet_id,
                        "post_time": tweet_at,
                    })
            else:
                logger.warning(f"No more likes data found for tweet {tweet_id}")

        return likes_interactions

    def get_quote_interactions(self, tweet):
        tweet_id = tweet["tweet_id"]
        tweet_at = tweet["created_at"]

        # 包含replies和retweets
        quote_interactions = []
        for resp in tweepy.Paginator(
                self.client.get_quote_tweets,
                max_results=DataCollector.MAX_RESULTS,
                id=tweet_id,
                exclude=["retweets"],
                user_auth=True,
                tweet_fields=['created_at'],
                expansions=["author_id"],
                user_fields=['profile_image_url'],
        ):
            # logger.info(f"resp:{resp}")
            if resp.get("errors"):
                raise ValueError("quotes not found")

            for data in resp.get("data", []):
                time_str = data["created_at"]
                interaction_dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))

                interaction = {
                    "media_account": self.media_account,
                    "user_id": data["author_id"],
                    # "username": data.username,
                    # "avatar_url": "",
                    "interaction_id": data["id"],
                    "interaction_type": "quote",
                    "interaction_content": data["text"],
                    "interaction_time": interaction_dt,  # likes 没有创建时间
                    "post_id": tweet_id,
                    "post_time": tweet_at,
                }

                for users in resp["includes"]["users"]:
                    if users["id"] == data["author_id"]:
                        interaction["username"] = users["username"]
                        interaction["avatar_url"] = users["profile_image_url"]
                quote_interactions.append(interaction)

        return quote_interactions

    # {'data': [{'username': 'ibikio46662', 'name': 'Tiro.G🇿🇦', 'id': '1876505524805787648', 'profile_image_url': 'https://pbs.twimg.com/profile_images/1881966641728172032/gFB92YEf_normal.jpg'}, {'username': 'myartbar', 'name': 'MyArtBar ∞', 'id': '1812886987407302656', 'profile_image_url': 'https://pbs.twimg.com/profile_images/1827433632601890816/JdgV6v9z_normal.jpg'}, {'username': 'motokoins', 'name': 'MOTOKO-PALS', 'id': '1698554726197985280', 'profile_image_url': 'https://pbs.twimg.com/profile_images/1875921267393490944/r5JZWaBp_normal.jpg'}, {'username': 'JunkFarm', 'name': 'benchmouse', 'id': '1113640082', 'profile_image_url': 'https://pbs.twimg.com/profile_images/1878843935407108096/HyN134ge_normal.jpg'}, {'username': 'OnlyoneabdulB', 'name': 'De_Web3_Bee(Ø,G)', 'id': '1840795221896151042', 'profile_image_url': 'https://pbs.twimg.com/profile_images/1840795341760700417/lXxvDF7t_normal.png'}, {'username': 'KLV_Hunter', 'name': 'KLV_Hunter', 'id': '1769873902493143040', 'profile_image_url': 'https://pbs.twimg.com/profile_images/1882235710368776192/yoq33KNA_normal.jpg'}], 'meta': {'result_count': 6, 'next_token': '7140dibdnow9c7btw4b0pn0yy4hq4ktr9xtuk0kp8b4ts'}}
    def get_retweet_interactions(self, tweet):
        tweet_id = tweet["tweet_id"]
        tweet_at = tweet["created_at"]
        retweets_interactions = []
        querystring = {"tweet.fields": "created_at", "expansions": "author_id",
                       "user.fields": "profile_image_url"}
        while True:
            resp = self.client.request(
                "GET",
                f"/2/tweets/{tweet_id}/retweets",
                querystring,
            )
            resp.raise_for_status()
            resp_data = resp.json()

            # 分页查询
            meta = resp_data["meta"]
            if meta["result_count"] == 0:
                break
            querystring["pagination_token"] = meta["next_token"]

            for data in resp_data.get("data", []):
                time_str = data["created_at"]
                interaction_dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                interaction = {
                    "media_account": self.media_account,
                    "user_id": data["author_id"],
                    # "username": data["username"],
                    # "avatar_url": data["profile_image_url"],
                    "interaction_id": data["id"],
                    "interaction_type": "retweet",
                    "interaction_content": data["text"],  # retweet 没有任何回复
                    "interaction_time": interaction_dt,  # likes 没有创建时间
                    "post_id": tweet_id,
                    "post_time": tweet_at,
                }

                for users in resp_data["includes"]["users"]:
                    if users["id"] == data["author_id"]:
                        interaction["username"] = users["username"]
                        interaction["avatar_url"] = users["profile_image_url"]

                retweets_interactions.append(interaction)

        return retweets_interactions

    def get_reply_interactions(self, tweet):
        tweet_id = tweet["tweet_id"]
        tweet_at = tweet["created_at"]
        reply_interactions = []
        query = f"conversation_id:{tweet_id} is:reply"
        for resp in tweepy.Paginator(
                self.client.search_all_tweets,
                query=query,
                tweet_fields=["created_at"],
                max_results=DataCollector.MAX_RESULTS,
                expansions=["author_id"],
                user_fields=['profile_image_url'],
                start_time=self.start_time,
        ):
            # logger.info(f"resp:{resp}")
            if resp.get("errors"):
                raise ValueError("retweets not found")

            for data in resp.get("data", []):
                time_str = data["created_at"]
                interaction_dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                interaction = {
                    "media_account": self.media_account,
                    "user_id": data["author_id"],
                    "interaction_type": "reply",
                    "interaction_id": data["id"],
                    "interaction_content": data["text"],
                    "interaction_time": interaction_dt,
                    "post_id": tweet_id,
                    "post_time": tweet_at,
                }

                for users in resp["includes"]["users"]:
                    if users["id"] == data["author_id"]:
                        interaction["username"] = users["username"]
                        interaction["avatar_url"] = users["profile_image_url"]
                reply_interactions.append(interaction)
                # logger.info("interaction:{}", interaction)

        return reply_interactions

    def get_interactions(self):
        uid = self.get_user_id()
        tweets = self.get_tweets(uid)

        all_interactions = []
        for tweet in tweets:
            # likes = self.get_like_interactions(tweet)
            quotes = self.get_quote_interactions(tweet)
            retweets = self.get_retweet_interactions(tweet)
            replies = self.get_reply_interactions(tweet)
            # all_interactions.extend(likes + quotes + replies + retweets)
            all_interactions.extend(quotes + replies + retweets)

        logger.info("before dep: {}", len(all_interactions))
        # unique_interactions = list(set(all_interactions))
        # logger.info("after dep: ", len(unique_interactions))
        unique_interactions = []
        seen_ids = set()
        for interaction in all_interactions:
            interaction_id = interaction["interaction_id"]
            if interaction_id not in seen_ids:
                unique_interactions.append(interaction)
                seen_ids.add(interaction_id)

        logger.info("after dep: {}", len(unique_interactions))
        return unique_interactions


def fetch_and_store_xdata(media_account, start_time: datetime):
    client = tweepy.Client(BEARER_TOKEN, API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET, return_type=dict)

    dc = DataCollector(client, media_account, start_time)
    interactions_data = dc.get_interactions()
    interactions = [
        Interaction(**interaction_data)
        for interaction_data in interactions_data
    ]
    try:
        db.session.add_all(interactions)
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        for interaction in interactions:
            try:
                db.session.add(interaction)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                logger.error("duplicate interaction, {}", {interaction.interaction_id})


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        fetch_and_store_xdata("ICPSwap", datetime(2025, 1, 23, tzinfo=timezone.utc))
