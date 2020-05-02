import matplotlib.pyplot as plt
import os, time
import numpy as np

plt.ion()
xpt, ypt = [], []
image_path = os.path.expanduser( "~/Desktop/sample_image.png")
im = plt.imread(image_path)

implot = plt.imshow(im)
points = plt.scatter(x=xpt, y=ypt, c='r', s=40)

def onMouseClick(event):
    xpt.append( event.xdata )
    ypt.append( event.ydata )
    print( f"Point {event.x} {event.y}: {event.xdata} {event.ydata}")
    points.set_offsets(np.c_[xpt, ypt])

cidpress = implot.figure.canvas.mpl_connect('button_press_event', onMouseClick )

plt.show()

keyboardClick = False
while keyboardClick != True:
    keyboardClick = plt.waitforbuttonpress()
