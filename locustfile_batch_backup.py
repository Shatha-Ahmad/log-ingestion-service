from locust import HttpUser, task, between
from datetime import datetime, timezone


class LogIngestionUser(HttpUser):
    wait_time = between(0, 0)

    @task
    def send_logs_batch(self):
        logs = []

        for i in range(500):
            logs.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "info",
                "service": "load-test",
                "message": f"Test log {i}",
                "attributes": {
                    "test": True,
                    "user_id": i,
                },
            })

        self.client.post(
            "/logs/batch",
            json={"logs": logs},
            name="/logs/batch",
        )