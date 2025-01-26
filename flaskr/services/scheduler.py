import time
import uuid
from apscheduler.triggers.interval import IntervalTrigger
import os
import pathlib
from datetime import datetime, timezone, timedelta
import dotenv
from coincurve.utils import sha256
from loguru import logger
import tweepy
from sqlalchemy.exc import IntegrityError
from flaskr.models import Interaction
from flaskr import db, scheduler
from flaskr.utils import datetime_as_db_format

dotenv.load_dotenv(dotenv_path=pathlib.Path.home() / '.twitter_relay' / '.env')
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv("API_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_SECRET = os.getenv("ACCESS_SECRET")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")


class DataCollector:
    MAX_RESULTS = 100

    def __init__(self, client: tweepy.Client, media_account: str, from_date: datetime = None):
        self.client = client
        self.media_account = media_account
        self.interactions = []
        self.start_time = from_date
        self.end_time = datetime.now(tz=timezone.utc)
        # 检查是否是utc时间
        if from_date:
            if not isinstance(from_date, datetime):
                raise TypeError('from_date must be of type datetime')
            if from_date.tzinfo != timezone.utc:
                raise ValueError('from_date must be in UTC')
            self.start_time_as_param = from_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        else:
            self.start_time = datetime.now(tz=timezone.utc) - timedelta(weeks=1)

    @classmethod
    def default(cls, media_account: str):
        client = tweepy.Client(BEARER_TOKEN, API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET, return_type=dict)
        return cls(
            client=client,
            media_account=media_account,
        )

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
                tweet = {
                    "tweet_id": data["id"],
                    "created_at": datetime_as_db_format(data["created_at"]),  # datetime.datetime utc
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
                interaction = {
                    "media_account": self.media_account,
                    "user_id": data["author_id"],
                    # "username": data.username,
                    # "avatar_url": "",
                    "interaction_id": data["id"],
                    "interaction_type": "quote",
                    "interaction_content": data["text"],
                    "interaction_time": datetime_as_db_format(data["created_at"]),  # likes 没有创建时间
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
                interaction = {
                    "media_account": self.media_account,
                    "user_id": data["author_id"],
                    # "username": data["username"],
                    # "avatar_url": data["profile_image_url"],
                    "interaction_id": data["id"],
                    "interaction_type": "retweet",
                    "interaction_content": data["text"],  # retweet 没有任何回复
                    "interaction_time": datetime_as_db_format(data["created_at"]),  # likes 没有创建时间
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
                interaction = {
                    "media_account": self.media_account,
                    "user_id": data["author_id"],
                    "interaction_type": "reply",
                    "interaction_id": data["id"],
                    "interaction_content": data["text"],
                    "interaction_time": datetime_as_db_format(data["created_at"]),
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

    def get_user_recent_quotes(self, username: str):
        query_quote = f"from:{username} is:quote"
        quote_interactions = []
        for resp in tweepy.Paginator(
                self.client.search_recent_tweets,
                query=query_quote,
                tweet_fields=["created_at"],
                max_results=DataCollector.MAX_RESULTS,
                expansions=["referenced_tweets.id.author_id"],
                user_fields=['profile_image_url'],
        ):
            # logger.info(f"resp: {resp}")
            if resp.get("errors"):
                raise ValueError("user's interactions not found")

            if not resp.get("includes", None):
                raise ValueError("includes fields not found")

            includes: dict = resp.get("includes")

            author_id = ""
            avatar_url = ""
            for user in includes.get("users", []):
                if user["username"] == self.media_account:
                    author_id = user["id"]
                if user["username"] == username:
                    avatar_url = user["profile_image_url"]

            tweet_ids_with_ts = {}
            for tweet in includes.get("tweets", []):
                if tweet["author_id"] == author_id:
                    tweet_id = tweet["id"]
                    tweet_ids_with_ts[tweet_id] = tweet["created_at"]

            for data in resp.get("data", []):
                post_id = data["referenced_tweets"][0]["id"]
                if post_id in tweet_ids_with_ts.keys():
                    interaction = {
                        "avatar_url": avatar_url,
                        "media_account": self.media_account,
                        "user_id": data["author_id"],
                        "interaction_type": "quote",
                        "interaction_id": data["id"],
                        "interaction_content": data["text"],
                        "interaction_time": datetime_as_db_format(data["created_at"]),
                        "post_id": post_id,
                        "post_time": datetime_as_db_format(tweet_ids_with_ts[post_id]),
                    }
                    quote_interactions.append(interaction)

        return quote_interactions

    def get_user_recent_replies_and_retweets(self, username: str):
        query_reply_or_retweet = f"from:{username} @{self.media_account}"
        interactions = []
        for resp in tweepy.Paginator(
                self.client.search_recent_tweets,
                query=query_reply_or_retweet,
                tweet_fields=["created_at"],
                expansions=["referenced_tweets.id.author_id"],
                user_fields=['profile_image_url'],
                max_results=DataCollector.MAX_RESULTS,
        ):
            # logger.info(f"resp: {resp}")
            if resp.get("errors"):
                raise ValueError("user's interactions not found")

            for data in resp.get("data", []):
                avatar_url = ""
                for user in resp["includes"]["users"]:
                    if user["username"] == username:
                        avatar_url = user["profile_image_url"]

                content: str = data["text"]
                interaction_type = "retweet" if content.startswith("RT") else "reply"

                post_id = data["referenced_tweets"][0]["id"]
                for tweet in resp["includes"]["tweets"]:
                    if tweet["id"] == post_id:
                        interaction = {
                            "avatar_url": avatar_url,
                            "media_account": self.media_account,
                            "user_id": data["author_id"],
                            "interaction_type": interaction_type,
                            "interaction_id": data["id"],
                            "interaction_content": data["text"],
                            "interaction_time": datetime_as_db_format(data["created_at"]),
                            "post_id": post_id,
                            "post_time": datetime_as_db_format(tweet["created_at"]),
                        }
                        interactions.append(interaction)
            return interactions

    def get_user_recent_interactions(self, username: str):
        return self.get_user_recent_replies_and_retweets(username) + self.get_user_recent_quotes(username)

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


RAW_SECRET = os.getenv("NOSTR_SECRET")

from pynostr.relay_manager import RelayManager
from pynostr.key import PrivateKey
from pynostr.event import Event
from pynostr.filters import Filters, FiltersList
from flask import current_app


class NostrPublisher:
    def __init__(self):
        self.relay_manager = RelayManager(timeout=6)
        self.private_key = PrivateKey.from_nsec(RAW_SECRET)

        self.relay_manager.add_relay(
            "ws://144.126.138.135:10548",
            close_on_eose=False
        )
        current_app.logger.info("Added relay to manager")

        # 添加订阅，只监听从现在开始的新消息
        current_time = int(datetime.now(timezone.utc).timestamp())
        filters = FiltersList([
            Filters(
                authors=[self.private_key.public_key.hex()],
                since=current_time  # 只接收从现在开始的新消息
            )
        ])
        subscription_id = uuid.uuid1().hex
        current_app.logger.info(
            f"Adding subscription for new messages since {current_time}, pubkey: {self.private_key.public_key.hex()}")
        self.relay_manager.add_subscription_on_all_relays(subscription_id, filters)

    def close(self):
        try:
            self.relay_manager.close_all_relay_connections()
            current_app.logger.info("NostrPublisher closed successfully")
        except Exception as e:
            current_app.logger.error(f"Error closing NostrPublisher: {e}")

    def __del__(self):
        if hasattr(self, 'relay_manager'):
            self.relay_manager.close_all_relay_connections()

    @staticmethod
    def _get_event_id(interaction_data: Interaction):
        return sha256(interaction_data.interaction_content.encode()).hex()

    @staticmethod
    def _get_tags(interaction_data: Interaction):
        return [
            ["t", "twitter"],
            ["account", interaction_data.media_account],
            ["user_id", interaction_data.user_id],
            ["username", interaction_data.username],
            ["created_at", interaction_data.interaction_time.isoformat()],
            ["post_id", interaction_data.post_id],
            # ["e", ""]
        ]

    @staticmethod
    def _get_kind(interaction_data: Interaction):
        if interaction_data.interaction_type == "reply" or interaction_data.interaction_type == "quote":
            return 1
        elif interaction_data.interaction_type == "retweet":
            return 6
        else:
            current_app.logger.error("Unknown interaction type")
            return 0

    @staticmethod
    def _get_content(interaction_data: Interaction):
        return interaction_data.interaction_content

    def publish(self, interaction_data, timeout=30) -> tuple[bool, str, str]:
        """
        Publish event to nostr relay

        Returns:
            tuple: (success, message, event_id)
        """
        try:
            event = Event(
                id=self._get_event_id(interaction_data),
                pubkey=self.private_key.public_key.hex(),
                created_at=int(datetime.now(timezone.utc).timestamp()),
                kind=self._get_kind(interaction_data),
                tags=self._get_tags(interaction_data),
                content=self._get_content(interaction_data),
            )
            event.sign(self.private_key.hex())
            current_app.logger.info(f"Publishing event {event.id} to nostr relay")

            self.relay_manager.publish_event(event)
            self.relay_manager.run_sync()
            # 等待并检查消息池中的响应
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.relay_manager.message_pool.has_ok_notices():
                    ok_msg = self.relay_manager.message_pool.get_ok_notice()
                    current_app.logger.info(f"Received OK notice: {ok_msg.event_id}, status: {ok_msg.ok}")
                    if ok_msg.event_id == event.id:
                        if ok_msg.ok:
                            return True, "Successfully published", event.id
                        else:
                            return False, f"Publication failed: {ok_msg.message}", ""
                time.sleep(0.1)

            return False, "Response timeout", ""

        except Exception as e:
            current_app.logger.error(f"Error publishing to nostr: {e}")
            return False, f"Error occurred: {str(e)}", ""


def fetch_and_store_xdata(media_account, from_dt: datetime):
    current_app.logger.info(
        f"Start fetching xdata from {from_dt} to {datetime.now(tz=timezone.utc)} for {media_account}")

    client = tweepy.Client(BEARER_TOKEN, API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET, return_type=dict)

    nostr_publisher = NostrPublisher()
    try:
        dc = DataCollector(client, media_account, from_dt)
        interactions_data = dc.get_interactions()

        for interaction_data in interactions_data:
            interaction = Interaction(**interaction_data)
            try:
                # Publish to nostr
                success, message, event_id = nostr_publisher.publish(interaction)

                # Update nostr publication status
                interaction.nostr_published = success
                if success:
                    interaction.nostr_event_id = event_id
                    current_app.logger.info(f"Success to publish event: {event_id}")
                else:
                    current_app.logger.warning(f"Failed to publish event {event_id}")

                # Save to database
                db.session.merge(interaction)
                db.session.commit()

                if success:
                    current_app.logger.info(
                        f"Interaction {interaction.interaction_id} published to nostr and saved to database"
                    )
                else:
                    current_app.logger.warning(
                        f"Interaction {interaction.interaction_id} saved to database but failed to publish to nostr: {message}"
                    )

            except IntegrityError:
                db.session.rollback()
                current_app.logger.error(f"Duplicate interaction: {interaction.interaction_id}")
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error processing interaction {interaction.interaction_id}: {str(e)}")

    finally:
        nostr_publisher.close()

    current_app.logger.info("Completed fetching and processing data")


# def fetch_and_store_xdata(media_account, from_dt: datetime):
#     current_app.logger.info(
#         f"start fetching xdata from {from_dt} to {datetime.now(tz=timezone.utc)} for {media_account}")
#     client = tweepy.Client(BEARER_TOKEN, API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET, return_type=dict)
#
#     dc = DataCollector(client, media_account, from_dt)
#     interactions_data = dc.get_interactions()
#     interactions = [
#         Interaction(**interaction_data)
#         for interaction_data in interactions_data
#     ]
#     try:
#         db.session.add_all(interactions)
#         db.session.commit()
#     except IntegrityError:
#         db.session.rollback()
#         for interaction in interactions:
#             try:
#                 db.session.add(interaction)
#                 db.session.commit()
#             except IntegrityError:
#                 db.session.rollback()
#                 # current_app.logger.error(f"duplicate interaction, {interaction.interaction_id}")
#     current_app.logger.info("success to fetch data")


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
        replace_existing=True,  # 如果任务 ID 已经存在，替换它
        misfire_grace_time=None
    )


def add_xsync_once_task(media_account: str, from_dt: datetime):
    scheduler.add_job(
        func=fetch_and_store_xdata_with_context,
        trigger='date',  # 使用date触发器实现一次性任务
        next_run_time=datetime.now(tz=timezone.utc),  # 立即执行
        id=f"init_task_{media_account}",
        args=[media_account, from_dt],
        replace_existing=True,
        misfire_grace_time=None
    )


def remove_xsync_task(media_account: str):
    if scheduler.get_job(id=f"task_{media_account}"):
        scheduler.remove_job(id=f"task_{media_account}")
    else:
        raise ValueError(f"no such task: {media_account}")


if __name__ == '__main__':
    client = tweepy.Client(BEARER_TOKEN, API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET, return_type=dict)
    from run import app

    with app.app_context():
        dc = DataCollector(client, "hetu_protocol", datetime.now(tz=timezone.utc))
        interactions = dc.get_user_recent_replies_and_retweets("Sky201805")
        print(interactions)
