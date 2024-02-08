import asyncio

from pycitysim.routing import RoutingClient


async def main():
    client = RoutingClient("localhost:52101")
    async_coroutine0 = client.GetRoute(
        {
            "type": 2,
            "start": {"aoi_position": {"aoi_id": 500000000}},
            "end": {"aoi_position": {"aoi_id": 500000001}},
        }
    )
    async_coroutine1 = client.GetRoute(
        {
            "type": 1,
            "start": {"aoi_position": {"aoi_id": 500000000}},
            "end": {"lane_position": {"lane_id": 100, "s": 1.2}},
        }
    )
    schedule0 = await async_coroutine0
    schedule1 = await async_coroutine1
    print(schedule0)
    print(schedule1)


if __name__ == "__main__":
    asyncio.run(main())
