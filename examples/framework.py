from pycitysim.sidecar import OnlyClientSidecar
from pycitysim.sim import CityClient
import logging

STEP = 10


async def main():
    logging.basicConfig(
        level=logging.DEBUG,
    )

    s = OnlyClientSidecar("py1", "localhost:53001")
    traffic_client = CityClient.from_sidecar(s)

    # 进行前期准备工作
    s.init()
    for i in range(100, -1, -1):
        logging.info("step %d", i)
        # prepare阶段
        s.notify_step_ready()
        # update阶段
        if i == 90:
            resp = await traffic_client.lane_service.GetLane({"lane_ids": [0]})
            print("GetLane:", resp)
            resp = await traffic_client.lane_service.SetLaneMaxV(
                {"lane_id": 0, "max_v": 10}
            )
            print("SetMaxV:", resp)
            resp = await traffic_client.person_service.GetPerson({"person_id": 0})
            print("GetPerson:", resp)
            resp = await traffic_client.road_service.GetRoad(
                {"road_ids": [2_0000_0000, 2_0000_0001]}
            )
            print("GetRoad:", resp)
            resp = await traffic_client.aoi_service.GetAoi(
                {"aoi_ids": [5_0000_0000, 5_0000_0001]}
            )
            print("GetAoi:", resp)
        if i != 0:
            close = s.step(STEP)  # Update阶段完成，通知模拟了STEP个tick
        else:
            close = s.close()  # 退出
        if close:
            break


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
