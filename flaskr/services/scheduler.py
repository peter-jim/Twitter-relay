from datetime import datetime, timedelta

from apscheduler.triggers.interval import IntervalTrigger

from ..extensions import scheduler, db
from .data_collector import fetch_and_store_xdata



def add_xsync_task(media_account: str,update_frequency: str, start_time: str):
    # 转换 start_time 和 end_time 为 datetime 对象
    start_time_dt = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S')

    # 解析 update_frequency，例如 "1 hour" 或 "1 day"
    frequency_unit = update_frequency.split()[1]  # 单位（hour, day 等）
    frequency_value = int(update_frequency.split()[0])  # 数量（1, 2, 3 等）

    if frequency_unit in ['second', 'seconds']:
        interval_params = {'seconds': frequency_value}
    elif frequency_unit in ['minute', 'minutes']:
        interval_params = {'minutes': frequency_value}
    elif frequency_unit in ['hour', 'hours']:
        interval_params = {'hours': frequency_value}
    elif frequency_unit in ['day', 'days']:
        interval_params = {'days': frequency_value}
    elif frequency_unit in ['week', 'weeks']:
        interval_params = {'weeks': frequency_value}
    else:
        raise ValueError(f"Unsupported frequency unit: {frequency_unit}")


    # 添加定时任务，按间隔执行任务
    scheduler.add_job(
        fetch_and_store_xdata,  # 需要执行的函数
        trigger=IntervalTrigger(**interval_params),  # 设置间隔触发器
        next_run_time=start_time_dt,  # 首次执行时间
        id=f"task_{media_account}",  # 设置任务的唯一 ID
        args=[media_account, start_time],  # 传递参数给 fetch_xdata 函数
        replace_existing=True  # 如果任务 ID 已经存在，替换它
    )
