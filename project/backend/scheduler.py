"""定时任务调度 — 爬虫定时执行、数据同步"""
import json
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()


def job_scrape():
    """定时爬取任务"""
    print(f"[Scheduler] 执行爬取任务: {datetime.now()}")
    try:
        from scraper import run_scraper
        result = run_scraper()
        print(f"[Scheduler] 爬取完成: {json.dumps(result, ensure_ascii=False)}")
    except Exception as e:
        print(f"[Scheduler] 爬取失败: {e}")


def job_sync_orders():
    """定时同步订单状态"""
    print(f"[Scheduler] 同步订单: {datetime.now()}")
    try:
        from delivery import batch_process_pending
        results = batch_process_pending()
        delivered = sum(1 for r in results if r.get("success"))
        if delivered > 0:
            print(f"[Scheduler] 自动发货 {delivered} 单")
    except Exception as e:
        print(f"[Scheduler] 同步失败: {e}")


def start_scheduler():
    """启动定时任务"""
    # 每6小时执行一次爬取
    scheduler.add_job(job_scrape, 'interval', hours=6, id='scrape_job', next_run_time=None)
    # 每5分钟检查一次待发货订单
    scheduler.add_job(job_sync_orders, 'interval', minutes=5, id='sync_orders')
    scheduler.start()
    print("[Scheduler] 定时任务已启动")
    print("  - 爬虫: 每6小时执行一次")
    print("  - 订单同步: 每5分钟检查一次")


def stop_scheduler():
    scheduler.shutdown()


def get_scheduler_status():
    jobs = scheduler.get_jobs()
    return [{
        "id": j.id,
        "name": j.name or j.id,
        "next_run": str(j.next_run_time) if j.next_run_time else "未调度",
        "trigger": str(j.trigger),
    } for j in jobs]


def trigger_scrape():
    """手动触发爬取"""
    scheduler.add_job(job_scrape, 'date', id=f'manual_scrape_{datetime.now().timestamp()}')
    return {"success": True, "msg": "爬取任务已触发"}
