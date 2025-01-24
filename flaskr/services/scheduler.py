import time
from apscheduler.triggers.interval import IntervalTrigger
import os
import pathlib
from datetime import datetime, timezone, timedelta
import dotenv
from flask import current_app, app
from loguru import logger
import tweepy
from sqlalchemy.exc import IntegrityError
from flaskr.models import Interaction
from flaskr import db, scheduler

dotenv.load_dotenv(dotenv_path=pathlib.Path.home() / '.twitter_relay' / '.env')
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
        self.start_time = from_date
        self.end_time = datetime.now(tz=timezone.utc)
        # 检查是否是utc时间
        if not isinstance(from_date, datetime):
            raise TypeError('from_date must be of type datetime')
        if from_date.tzinfo != timezone.utc:
            raise ValueError('from_date must be in UTC')

        self.start_time_as_param = from_date.strftime('%Y-%m-%dT%H:%M:%SZ')

    def get_user_id(self):
        try:
            resp = self.client.get_user(username=self.media_account)
            if resp.get('errors'):
                raise
            return resp["data"]["id"]
        except tweepy.errors.TweepyException as e:
            logger.warning(f'failed to get user id by media account: {e}')
            remove_xsync_task(self.media_account)  # 加错了就删
            raise ValueError("Media account not found")

    def get_tweets(self, uid: int):
        tweets = []

        for resp in tweepy.Paginator(
                self.client.get_users_tweets,
                max_results=DataCollector.MAX_RESULTS,
                exclude=["replies"],  # 排除 replies
                id=uid,
                start_time=self.start_time_as_param,
                tweet_fields=['created_at', 'conversation_id']
        ):
            # logger.info("*" * 80)
            if resp.get('errors'):
                logger.error(
                    "Failed to get tweet for user id {} from {} to {}",
                    uid,
                    self.start_time,
                    self.end_time
                )
                continue
                # raise ValueError("tweet not found")

            for data in resp.get('data', []):
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
                    # logger.info("likes_interactions:{}", {
                    #     "media_account": self.media_account,
                    #     "user_id": data.id,
                    #     "username": data.username,
                    #     "avatar_url": data.profile_image_url,
                    #     "interaction_type": "likes",
                    #     "interaction_content": "",
                    #     "interaction_time": tweet_at,  # likes 没有创建时间
                    #     "post_id": tweet_id,
                    #     "post_time": tweet_at,
                    # })
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
                logger.error(
                    "Failed to get quote interaction from {} to {}",
                    self.start_time,
                    self.end_time
                )
                continue

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

    # Rate limit: 50 requests / 15 mins PER USER
    def get_retweet_interactions(self, tweet):
        tweet_id = tweet["tweet_id"]
        tweet_at = tweet["created_at"]
        retweets_interactions = []
        querystring = {"tweet.fields": "created_at", "expansions": "author_id",
                       "user.fields": "profile_image_url", "max_results": DataCollector.MAX_RESULTS, }
        while True:
            time.sleep(0.5)
            resp = self.client.request(
                "GET",
                f"/2/tweets/{tweet_id}/retweets",
                querystring,
            )
            resp.raise_for_status()
            resp_data = resp.json()

            if resp_data.get("errors"):
                logger.error(
                    "Failed to get retweet interactions from {} to {}",
                    self.start_time,
                    self.end_time
                )
                break

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

    # DEPRECATED
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

    # 2025-01-24 17:13:24.833 | ERROR    | flaskr.services.scheduler:_get_interaction_data:365 - Error in get_reply_interactions: 400 Bad Request
    # Invalid 'start_time':'2025-01-01T00:00Z'. 'start_time' must be on or after 2025-01-17T09:13Z
    # unavailable
    # def get_reply_interactions(self, tweet):
    #     tweet_id = tweet["tweet_id"]
    #     tweet_at = tweet["created_at"]
    #     reply_interactions = []
    #     query = f"conversation_id:{tweet_id} is:reply"
    #
    #     end_time = datetime.now(tz=timezone.utc)
    #     cur_start_time = self.start_time
    #     while cur_start_time < end_time:
    #         cur_end_time = min(cur_start_time + timedelta(days=7), end_time)
    #
    #         for resp in tweepy.Paginator(
    #                 self.client.search_recent_tweets,
    #                 query=query,
    #                 tweet_fields=["created_at"],
    #                 max_results=DataCollector.MAX_RESULTS,
    #                 expansions=["author_id"],
    #                 user_fields=['profile_image_url'],
    #                 start_time=self.start_time_as_param,
    #         ):
    #             # logger.info(f"resp:{resp}")
    #             if resp.get("errors"):
    #                 logger.error(
    #                     "Failed to get reply interactions from {} to {}",
    #                     self.start_time,
    #                     self.end_time
    #                 )
    #                 continue
    #
    #             for data in resp.get("data", []):
    #                 time_str = data["created_at"]
    #                 interaction_dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    #                 interaction = {
    #                     "media_account": self.media_account,
    #                     "user_id": data["author_id"],
    #                     "interaction_type": "reply",
    #                     "interaction_id": data["id"],
    #                     "interaction_content": data["text"],
    #                     "interaction_time": interaction_dt,
    #                     "post_id": tweet_id,
    #                     "post_time": tweet_at,
    #                 }
    #
    #                 for users in resp["includes"]["users"]:
    #                     if users["id"] == data["author_id"]:
    #                         interaction["username"] = users["username"]
    #                         interaction["avatar_url"] = users["profile_image_url"]
    #                 reply_interactions.append(interaction)
    #                 # logger.info("interaction:{}", interaction)
    #
    #         cur_start_time = cur_end_time
    #     return reply_interactions

    def get_interactions(self):
        uid = self.get_user_id()
        tweets = self.get_tweets(uid)

        all_interactions = []

        # https://docs.x.com/x-api/fundamentals/rate-limits
        for tweet in tweets:
            quotes = self._get_interaction_data(self.get_quote_interactions, tweet)
            retweets = self._get_interaction_data(self.get_retweet_interactions, tweet)
            replies = self._get_interaction_data(self.get_reply_interactions, tweet)

            # all_interactions.extend(likes + quotes + replies + retweets)
            all_interactions.extend(quotes + replies + retweets)

        current_app.logger.info(f"before dep: {len(all_interactions)}")
        # unique_interactions = list(set(all_interactions))
        # logger.info("after dep: ", len(unique_interactions))
        unique_interactions = []
        seen_ids = set()
        for interaction in all_interactions:
            interaction_id = interaction["interaction_id"]
            if interaction_id not in seen_ids:
                unique_interactions.append(interaction)
                seen_ids.add(interaction_id)

        current_app.logger.info(f"after dep: {len(unique_interactions)}")
        return unique_interactions

    @staticmethod
    def _get_interaction_data(method, *args):
        try:
            return method(*args)
        except tweepy.errors.TooManyRequests:
            logger.warning(f"Rate limit exceeded for {method.__name__}. Skipping this interaction type.")
            return []  # 返回空列表，表示跳过该类型数据
        except tweepy.errors.TweepyException as e:
            logger.error(f"Error in {method.__name__}: {str(e)}")
            return []  # 返回空列表，表示跳过该类型数据


def fetch_and_store_xdata(media_account, from_dt: datetime):
    current_app.logger.info(
        f"start fetching xdata from {from_dt} to {datetime.now(tz=timezone.utc)} for {media_account}")
    client = tweepy.Client(BEARER_TOKEN, API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET, return_type=dict)

    dc = DataCollector(client, media_account, from_dt)
    interactions_data = dc.get_interactions()
    interactions = [
        Interaction(**interaction_data)
        for interaction_data in interactions_data
    ]
    try:
        db.session.add_all(interactions)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        for interaction in interactions:
            try:
                db.session.add(interaction)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                # current_app.logger.error(f"duplicate interaction, {interaction.interaction_id}")
    current_app.logger.info("success to fetch data")


def fetch_and_store_xdata_with_context(media_account, from_dt: datetime):
    with scheduler.app.app_context():  # 手动创建上下文
        fetch_and_store_xdata(media_account, from_dt)


def add_xsync_task(media_account: str, frequency_unit: str, frequency_value: int):
    now = datetime.now(tz=timezone.utc)
    if frequency_unit in ['second', 'seconds']:
        interval_params = {'seconds': frequency_value}
        next_run_time = now + timedelta(seconds=frequency_value)
    elif frequency_unit in ['minute', 'minutes']:
        interval_params = {'minutes': frequency_value}
        next_run_time = now + timedelta(minutes=frequency_value)
    elif frequency_unit in ['hour', 'hours']:
        interval_params = {'hours': frequency_value}
        next_run_time = now + timedelta(hours=frequency_value)
    elif frequency_unit in ['day', 'days']:
        interval_params = {'days': frequency_value}
        next_run_time = now + timedelta(days=frequency_value)
    elif frequency_unit in ['week', 'weeks']:
        interval_params = {'weeks': frequency_value}
        next_run_time = now + timedelta(weeks=frequency_value)
    else:
        raise ValueError(f"Unsupported frequency unit: {frequency_unit}")

    # 添加定时任务，按间隔执行任务
    scheduler.add_job(
        func=fetch_and_store_xdata_with_context,  # 需要执行的函数
        trigger=IntervalTrigger(**interval_params),  # 设置间隔触发器
        next_run_time=next_run_time,  # 首次执行时间
        id=f"task_{media_account}",  # 设置任务的唯一 ID
        args=[media_account, now],  # 传递参数给 fetch_xdata 函数
        replace_existing=True  # 如果任务 ID 已经存在，替换它
    )


def remove_xsync_task(media_account: str):
    if scheduler.get_job(id=f"task_{media_account}"):
        scheduler.remove_job(id=f"task_{media_account}")
    else:
        raise ValueError(f"no such task: {media_account}")
