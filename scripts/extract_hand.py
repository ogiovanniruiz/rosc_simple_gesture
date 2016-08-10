#!/usr/bin/python
import rospy
import sys
import cv2
import imutils
import numpy as np
from sensor_msgs.msg import Image
from std_msgs.msg import String
from cv_bridge import CvBridge, CvBridgeError
import os
import glob

class HandGestures:
    def __init__(self):
        # Initialize ROS
        self.node_name = "stratom_hand_extraction"
        rospy.init_node(self.node_name)
        rospy.on_shutdown(self.cleanup)

        self.bridge = CvBridge()

        # Subscribe to filtered image
        self.depth_sub = rospy.Subscriber("filtered_image", Image, self.recog_callback)

        #Params are used to get path to gestures folders in simple_gesture package
        gesture_path = rospy.get_param('~/gesture_path')

        #A list of the gestures is generated
        self.list = os.listdir(gesture_path)

        path = [None] *len(self.list)
        image_path = [None] * len(self.list)
        self.temp = [None] * len(self.list)

        for i in range(len(self.list)):
            path[i] = str(gesture_path) + '/' + str(self.list[i])

            image_path[i] = glob.glob(str(path[i]) + '/*')[0]

            self.temp[i] = cv2.imread(image_path[i], 0)


        # Publish detected hand gesture
        self.pub_gest = rospy.Publisher('gesture_detected', String, queue_size=10, latch=True)

        # Global Variables
        self.gesture_detected = ""
        self.count = 0

        rospy.loginfo("Loading Hand Extraction Node...")

    def recog_callback(self, ros_image):
        try:
            inImg = self.bridge.imgmsg_to_cv2(ros_image)
        except CvBridgeError, e:
            print e

        #Initialize Conditions
        detected = False
        displayText = "Not Detected"
        top_left = None
        bottom_right = None

        #Initialize Arrays
        resized_temp = [None] * len(self.list)
        h = [None] * len(self.list)
        w = [None] * len(self.list)
        res = [None] * len(self.list)
        min_val = [None] * len(self.list)
        min_loc = [None] * len(self.list)
        prob = [None] * len(self.list)

        for i in range(len(self.list)):
            for scale in np.linspace(1.0, 3.0, 10)[::1]:
                # resize the templates according to the scale and find their dimensions
                resized_temp[i] = imutils.resize(self.temp[i], width=int(self.temp[i].shape[0] * scale))
                h[i], w[i] = resized_temp[i].shape[:2]

                # Break the loop if the resized template is larger than the camera image.
                if inImg.shape[0] < h[i]:
                    break

                if inImg.shape[1] < w[i]:
                    break

                res[i] = cv2.matchTemplate(inImg, resized_temp[i], 1)
                min_val[i], _, min_loc[i], _ = cv2.minMaxLoc(res[i])
                prob[i] = 1 - float(min_val[i])

                most_prob_val = max(prob)

                if (most_prob_val > 0.7):
                    ind = prob.index(max(prob))
                    detected = True
                    self.gesture_detected = str(self.list[ind])
                    top_left = min_loc[ind]
                    bottom_right = (top_left[0] + w[ind], top_left[1] + h[ind])
                    break
                else:
                    self.gesture_detected = ""
                    break

        height, width = inImg.shape[:2]
        if detected == True:
            displayText = "Detected"

        self.pub_gest.publish(self.gesture_detected)

        # Creates Viewable Image with HUD
        cv2.rectangle(inImg, top_left, bottom_right, 155, 1)
        cv2.putText(inImg, self.gesture_detected, (top_left), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (122, 0, 255))
        cv2.putText(inImg, displayText, (width / 3, height / 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (122, 0, 255))
        cv2.imshow("Gesture Detection", inImg)
        cv2.waitKey(3)

    def cleanup(self):
        print "Shutting down recognition node."
        cv2.destroyAllWindows()


def main(args):
    try:
        HandGestures()
        rospy.spin()
    except KeyboardInterrupt:
        print "Shutting down recognition node."
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main(sys.argv)