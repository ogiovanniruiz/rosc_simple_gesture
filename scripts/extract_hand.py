#!/usr/bin/python
import rospy
import sys
import cv2
import imutils
import numpy as np
from sensor_msgs.msg import Image
from std_msgs.msg import String
from std_msgs.msg import Float64
from std_msgs.msg import Int32
from cv_bridge import CvBridge, CvBridgeError
import os
import glob


# noinspection PyPep8Naming
class HandGestures:
    def __init__(self):

        # Initialize ROS
        self.node_name = "hand_extraction"
        rospy.init_node(self.node_name)
        rospy.on_shutdown(self.cleanup)

        self.bridge = CvBridge()

        # Parameters for subscirbed and published topic
        filtered_image_topic = rospy.get_param('~/filtered_image_topic')
        gesture_detected = rospy.get_param('~/gesture_detected_topic')
	gesture_location = rospy.get_param('~/gesture_location_topic')
	gesture_depth = rospy.get_param('~/gesture_depth_topic')

        # Subscribe and publish to topics
        self.depth_sub = rospy.Subscriber(filtered_image_topic, Image, self.recog_callback)
        self.pub_gest = rospy.Publisher(gesture_detected, String, queue_size=10, latch=True)

        #Publisher for gesture location and depth
        self.pub_loc = rospy.Publisher(gesture_location, Float64, queue_size=10, latch=True)
        self.pub_dep = rospy.Publisher(gesture_depth, Int32, queue_size=10, latch=True)

        # Params are used to get path to gestures folders in simple_gesture package
        gesture_path = rospy.get_param('~/gesture_path')

        # A list of the gestures is generated
        self.list = os.listdir(gesture_path)

        # Arrays are initialized
        path = [None] * len(self.list)
        image_path = [None] * len(self.list)
        self.temp = [None] * len(self.list)

        # Search gesture folder for image path and read templates
        for i in range(len(self.list)):
            path[i] = str(gesture_path) + '/' + str(self.list[i])

            image_path[i] = glob.glob(str(path[i]) + '/*')[0]

            self.temp[i] = cv2.imread(image_path[i], 0)

        self.gesture_detected = ""

        rospy.loginfo("Loading Hand Extraction Node...")

    def recog_callback(self, ros_image):
        try:
            inImg = self.bridge.imgmsg_to_cv2(ros_image)
        except CvBridgeError, e:
            print e

        # Initialize Conditions
        detected = False
        displayText = "Not Detected"
        top_left = None
        bottom_right = None

        # Initialize Arrays
        resized_temp = [None] * len(self.list)
        h = [None] * len(self.list)
        w = [None] * len(self.list)
        res = [None] * len(self.list)
        min_val = [None] * len(self.list)
        min_loc = [None] * len(self.list)
        prob = [None] * len(self.list)

        # Calculate Camera Image Dimensions
        height, width = inImg.shape[:2]

        # Begin searching through gestures
        for i in range(len(self.list)):
            # Linspace creates array to scale image size
            for scale in np.linspace(1.0, 2.0, 20)[::1]:
                # resize the templates according to the scale and find their dimensions
                resized_temp[i] = imutils.resize(self.temp[i], width=int(self.temp[i].shape[0] * scale))
                h[i], w[i] = resized_temp[i].shape[:2]

                # Break the loop if the resized template is larger than the camera image.
                if inImg.shape[0] < h[i]:
                    break

                if inImg.shape[1] < w[i]:
                    break

                # Note: the matchTemplate is using a min function
                res[i] = cv2.matchTemplate(inImg, resized_temp[i], 1)
                min_val[i], _, min_loc[i], _ = cv2.minMaxLoc(res[i])
                prob[i] = 1 - float(min_val[i])

                #Calculate most probable and get parameters for probaility threshold
                most_prob_val = max(prob)
                prob_const = rospy.get_param('~/probability')

                # Find most probable gesture and locate on the image
                if most_prob_val > prob_const:
                    ind = prob.index(max(prob))
                    detected = True
                    self.gesture_detected = str(self.list[ind])
                    top_left = min_loc[ind]
                    bottom_right = (top_left[0] + w[ind], top_left[1] + h[ind])
                    temp_w = w[ind]
                    temp_h = h[ind]
                    break
                else:
                    self.gesture_detected = ""
                    break

        #Displays to HUD
        if detected:
            displayText = "Detected"

        #Publishes detected gesture
        self.pub_gest.publish(self.gesture_detected)

        #Analyze and Publish gesture location and depth
        if (top_left != None):
            x = 2*(top_left[0] + float(temp_w/2) - width/2)/width
            center = inImg[bottom_right[1] - temp_h: bottom_right[1], top_left[0]: top_left[0] + temp_w]
            depth = np.median(center)
        else:
            depth = 0
            x = 0

        self.pub_dep.publish(depth)
        self.pub_loc.publish(x)

        # Creates Viewable Image with HUD if param "show" is True
        show = rospy.get_param('~/show')
        if show == True:
            cv2.rectangle(inImg, top_left, bottom_right, 155, 1)
            cv2.putText(inImg, self.gesture_detected, top_left, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (122, 0, 255))
            cv2.putText(inImg, displayText, (width / 3, height / 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (122, 0, 255))
            cv2.imshow("Gesture Detection", inImg)
            cv2.waitKey(3)

    @staticmethod
    def cleanup():
        print "Shutting down recognition node."
        cv2.destroyAllWindows()


# noinspection PyUnusedLocal
def main(args):
    try:
        HandGestures()
        rospy.spin()
    except KeyboardInterrupt:
        print "Shutting down recognition node."
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main(sys.argv)
