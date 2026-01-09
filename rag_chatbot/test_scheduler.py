"""
Test script to verify scheduler starts correctly
"""
import asyncio
import logging
import os
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Setup
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Mock check function
async def check_pending_cases():
    logger.info("✅ Scheduler tick - checking cases...")
    # This will be called every 5 minutes in production
    # For test, we just verify it can be called

async def test_scheduler():
    logger.info("=" * 60)
    logger.info("🧪 Testing Scheduler Setup")
    logger.info("=" * 60)
    
    scheduler = AsyncIOScheduler()
    
    # Add job that runs every 10 seconds for testing
    scheduler.add_job(
        check_pending_cases,
        "interval",
        seconds=10,  # Short interval for testing
        id="check_support_cases",
        name="Check pending support cases"
    )
    
    logger.info("📅 Scheduler configured")
    logger.info("   Job: Check pending support cases")
    logger.info("   Interval: 10 seconds (test mode)")
    
    scheduler.start()
    logger.info("✅ Scheduler started successfully!")
    logger.info(f"   Running: {scheduler.running}")
    logger.info(f"   Jobs: {len(scheduler.get_jobs())}")
    
    # Let it run for 35 seconds to see multiple ticks
    logger.info("\n⏳ Running scheduler for 35 seconds...")
    logger.info("   (Watch for scheduler ticks every 10 seconds)\n")
    
    await asyncio.sleep(35)
    
    logger.info("\n📊 Scheduler test complete!")
    scheduler.shutdown()
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_scheduler())
