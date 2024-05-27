from pycitysim.sidecar import OnlyClientSidecar
from pycitysim.sim import CityClient
import logging

STEP = 1

# TODO: 目前未能通知客户端车辆行程结束


async def main():
    logging.basicConfig(
        level=logging.DEBUG,
    )

    # 启动命令
    # ./simulet-go -config configs/config.yml -job test -syncer http://localhost:53001 -listen :51102
    # ./syncer -app city -app py1
    s = OnlyClientSidecar("py1", "localhost:53001")
    traffic_client = CityClient.from_sidecar(s)

    # 进行前期准备工作
    # Prepare
    s.init()
    for i in range(50, -1, -1):
        logging.info("step %d", i)
        # prepare
        s.notify_step_ready()
        if i == 30:
            # 1. 获取所有车辆信息，从中挑选待控制的车辆
            res = await traffic_client.person_service.GetAllVehicles({}, True)
            logging.info("GetAllVehicles: %s", res)
            ids = [motion["id"] for motion in res["motions"][:2]]
            # 2. 设置Controlled
            await traffic_client.person_service.SetControlledVehicleIDs(
                {"vehicle_ids": ids}
            )
            logging.info("SetControlledVehicleIDs: %s", ids)
        if 20 <= i < 30:
            # 3. 控制车辆
            envs = await traffic_client.person_service.FetchControlledVehicleEnvs({})
            logging.info("FetchControlledVehicleEnvs: %s", envs)
            actions = []
            for env in envs["vehicle_envs"]:
                # 车辆的控制逻辑包含以下操作
                # 1. acc: 加速度，单位m/s^2，控制纵向速度
                # 2. lc_target_id（可选）: 设定变道目标车道，不设置代表不变道或保持变道状态，允许覆盖现有变道状态
                # 3. angle: 变道过程的转向角度（弧度，非负值），间接控制横向速度，车辆横向位移达到车道宽度后完成变道
                actions.append({"id": env["id"], "acc": 10, "angle": 0})
            await traffic_client.person_service.SetControlledVehicleActions(
                {"vehicle_actions": actions}
            )
            logging.info("ControlVehicles: %s", actions)
        if i == 20:
            # 4. 退出控制
            await traffic_client.person_service.SetControlledVehicleIDs(
                {"vehicle_ids": []}
            )
            logging.info("SetControlledVehicleIDs: %s", [])
        if i != 0:
            close = s.step(STEP)  # Update阶段完成，通知模拟了STEP个tick
        else:
            close = s.close()  # 退出
        if close:
            break


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
