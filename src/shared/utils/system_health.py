import time
import datetime
import logging
from typing import Dict, List, Any

class SystemHealth:
    """
    Module 6: SystemHealth
    Responsibility: Monitoring the 'vitals' of the bot including AI performance, API latency, and uptime.
    """
    def __init__(self):
        self.start_time = datetime.datetime.now()
        self.cycle_latencies = []
        self.ai_success_count = 0
        self.ai_total_calls = 0
        self.api_errors = 0
        self.last_ai_confidence = 0
        self.rate_limit_hits = 0

    def record_cycle(self, latency_ms: float):
        self.cycle_latencies.append(latency_ms)
        if len(self.cycle_latencies) > 100:
            self.cycle_latencies.pop(0)

    def record_ai_call(self, success: bool, confidence: int = 0):
        self.ai_total_calls += 1
        if success:
            self.ai_success_count += 1
        self.last_ai_confidence = confidence

    def record_api_error(self, is_rate_limit: bool = False):
        if is_rate_limit:
            self.rate_limit_hits += 1
        else:
            self.api_errors += 1

    def get_health_report(self) -> Dict[str, Any]:
        uptime = datetime.datetime.now() - self.start_time
        avg_latency = sum(self.cycle_latencies) / len(self.cycle_latencies) if self.cycle_latencies else 0
        ai_reliability = (self.ai_success_count / self.ai_total_calls * 100) if self.ai_total_calls > 0 else 100
        
        # System Health Score calculation
        score = 100
        score -= min(30, self.api_errors * 5)
        score -= min(20, self.rate_limit_hits * 2)
        if avg_latency > 5000: score -= 10
        
        return {
            "uptime_seconds": int(uptime.total_seconds()),
            "avg_cycle_latency_ms": round(avg_latency, 2),
            "ai_reliability_pct": round(ai_reliability, 2),
            "ai_last_confidence": self.last_ai_confidence,
            "api_errors": self.api_errors,
            "api_rate_limits": self.rate_limit_hits,
            "system_score": max(0, int(score)),
            "status": "HEALTHY" if score > 80 else ("WARNING" if score > 50 else "CRITICAL")
        }

# Singleton
system_health = SystemHealth()
