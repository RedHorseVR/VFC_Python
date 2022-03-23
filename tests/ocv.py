import cv2
import numpy as np
import screeninfo
from matplotlib import pyplot as plt
# TRY SOME OPENCV FUNCTIONS ___________________________________
imgL = cv2.imread('OBJ_L_7.png', 0)
#plt.imshow(imgL, cmap = 'gray', interpolation = 'bicubic')
#plt.show( )
#imgR = cv2.imread('OBJ_R_7.png', 0)

#cv2.imshow('image R', imgR)




screen_id = 0
is_color = False

# get the size of the screen
screen = screeninfo.get_monitors()[screen_id]
width, height = screen.width, screen.height
print( width )
print( height)

# create image
if is_color:
    image = np.ones((height, width, 3), dtype=np.float32)
    image[:10, :10] = 0# black at top-left corner
    image[height - 10:, :10] = [1, 0, 0]# blue at bottom-left
    image[:10, width - 10:] = [0, 1, 0]# green at top-right
    image[height - 10:, width - 10:] = [0, 0, 1]# red at bottom-right
else:
    image = np.ones((height, width), dtype=np.float32)
    image[0, 0] = 0# top-left corner
    image[height - 2, 0] = 0# bottom-left
    image[0, width - 2] = 0# top-right
    image[height - 2, width - 2] = 0# bottom-right

window_name = 'projector'
cv2.namedWindow(window_name, cv2.WND_PROP_FULLSCREEN)
cv2.moveWindow(window_name, screen.x - 1, screen.y - 1)
cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN)

cv2.imshow(window_name, imgL)




#cv2.namedWindow("image L", cv2.WINDOW_NORMAL )
#cv2.namedWindow("image R", cv2.WINDOW_FREERATIO)
#cv2.imshow('image L', imgL)
key = 0
while( key != ' ' ):#////
    key = cv2.waitKey() & OxFF
cv2.destroyAllWindows()
#  Export  Date: 02:53:54 AM - 20:Mar:2019.
#  Export  Date: 06:24:26 PM - 20:Mar:2019.

