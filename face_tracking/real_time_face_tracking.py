import cv2
import numpy as np
import os

from detectron2 import model_zoo
from detectron2.config import get_cfg
from detectron2.data import MetadataCatalog
from detectron2.engine import DefaultPredictor
from detectron2.utils.visualizer import ColorMode, Visualizer

from djitellopy import Tello

# fbRange = [6200, 6800]
fbRange = [4200,4800]

pid = [0.4, 0.4, 0]

pError = 0


def get_frame(drone: Tello, width, height):
    img = drone.get_frame_read().frame
    img_resize = cv2.resize(img, (width, height))
    return img_resize


def face_detection_setup():
    MetadataCatalog.get("df_train").set(thing_classes="face")

    cfg = get_cfg()
    cfg.merge_from_file(model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml"))
    cfg.MODEL.WEIGHTS = os.path.join(cfg.OUTPUT_DIR, "model_final.pth")
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 1
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.85
    cfg.MODEL.DEVICE = "cpu"

    predictor = DefaultPredictor(cfg)

    return predictor


def face_detection(predictor, frame):
    outputs = predictor(frame)
    tensor = outputs["instances"]
    coordinates = tensor.pred_boxes.tensor

    v = Visualizer(
        frame[:, :, ::-1],
        metadata={"thing_classes": ['face']},
        scale=1.,
        instance_mode=ColorMode.IMAGE
    )

    instances = outputs["instances"].to("cpu")
    # instances.remove('pred_masks')
    v = v.draw_instance_predictions(instances)
    result = v.get_image()[:, :, ::-1]

    myFaceListC = []

    myFaceListArea = []
    # x, y, w, h = coordinates[0][0].item(), coordinates[0][1].item(), coordinates[0][2].item(), coordinates[0][3].item()
    if len(coordinates) != 0:
        print(coordinates)
        x, y, w, h = coordinates[0][0].item(), coordinates[0][1].item(), coordinates[0][2].item(), coordinates[0][3].item()

        cx = x + w // 2
        cy = y + h // 2
        area = w * h

        myFaceListC.append([cx, cy])

        myFaceListArea.append(area)

        if len(myFaceListArea) != 0:
            i = myFaceListArea.index(max(myFaceListArea))
            return result, [myFaceListC[i], myFaceListArea[i]]
        else:
            return result, [[0, 0], 0]

    return result, [[0,0],0]


def trackFace(info,w,pid, pError):
    face_area = info[1]
    center_x, center_y = info[0]
    center_y = center_y - 20

    # solve this
    if center_x != 0:
        error = center_x - w // 2
        speed = pid[0] * error + pid[1] * (error - pError)
        speed = int(np.clip(speed, -100, 100))
        yaw_velocity = speed

        if fbRange[0] < face_area < fbRange[1]:
            fb = 0
        elif face_area > fbRange[1]:
            fb = -20
        elif face_area < fbRange[0] and face_area != 0:
            fb = 20
    else:
        fb = 0
        yaw_velocity = 0
        error = 0

    if center_y != 0:
        if 50 < center_y < 170:
            ud = 0
        elif center_y > 170:
            ud = -20
        elif center_y < 50 and center_y != 0:
            ud = 20
    else:
        ud = 0

    # print(myDrone.for_back_velocity, myDrone.up_down_velocity, myDrone.yaw_velocity)
    tello.send_rc_control(0, fb, ud, yaw_velocity)
    return error


if __name__ == "__main__":

    predictor = face_detection_setup()

    tello = Tello()
    tello.connect()

    tello.streamon()
    tello.takeoff()
    print(tello.get_battery())

    exit = 0
    width, height = 640, 480
    counter = 0
    while not exit:

        frame = get_frame(tello, width, height)
        # keep drone alive

            # print(frame)
        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #     tello.land()
        #     break
        # else:
            # tello.send_command_without_return('Stay_alive')


        # annotated_frame, info = face_detection(predictor, frame)
        # pError = trackFace(info,width,pid,pError)

        cv2.imshow("Real-time Face Detection", frame)

        # cv2.imshow("Real-time Face Detection", annotated_frame)
        cv2.waitKey(10)
            
            # exit = int(input("Type 0 if you want to stop; else 1: "))
        if cv2.waitKey(1) & 0xFF == ord('q'):
            tello.land()
            break

    tello.streamoff()