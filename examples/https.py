from pycitysim.sidecar import OnlyClientSidecar
from pycitysim.sim import CityClient
import logging

STEP = 10


async def main():
    logging.basicConfig(
        level=logging.DEBUG,
    )

    client = CityClient("https://api-opencity-2x.fiblab.net:58081")
    res = await client.clock_service.Now({})
    print("Now:", res)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
