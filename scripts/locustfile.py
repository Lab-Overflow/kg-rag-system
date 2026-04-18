"""压力测试。目标 P95 < 2.5s @ hybrid mode。"""
from locust import HttpUser, between, task


class KGRAGUser(HttpUser):
    wait_time = between(0.3, 1.5)

    @task(8)
    def hybrid_query(self):
        self.client.post("/api/query", json={
            "q": "What is Claude and who makes it?", "mode": "hybrid", "top_k": 10,
        })

    @task(3)
    def agentic_query(self):
        self.client.post("/api/query", json={
            "q": "Compare OpenAI and Anthropic on funding and products",
            "mode": "agentic", "top_k": 15,
        })

    @task(1)
    def subgraph(self):
        self.client.post("/api/graph/subgraph", json={
            "seed": "Anthropic", "hops": 2, "limit": 150,
        })
