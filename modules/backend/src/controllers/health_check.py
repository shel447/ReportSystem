from runtime.server import router
from tornado.web import RequestHandler


class HealthCheckController:
    @router.GET("/rest/chatbi/healthcheck")
    async def health_check(self, req: RequestHandler, **query):
        return {"retCode": 0, "retInfo": "chatbi works well"}
