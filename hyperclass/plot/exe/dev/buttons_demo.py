import matplotlib.pyplot as plt
from  matplotlib.widgets import Button
from mpl_toolkits.axes_grid1.inset_locator import InsetPosition

fig, ax= plt.subplots()

# button_ax1 = plt.axes([0, 0, 1, 1])
# ip = InsetPosition(ax, [0.4, 0.5, 0.2, 0.1]) #posx, posy, width, height
# button_ax1.set_axes_locator(ip)
# Button(button_ax1, 'Click me 1')
#
# button_ax2 = plt.axes([0, 0, 1, 1])
# ip = InsetPosition(ax, [0.1, 0.1, 0.2, 0.1]) #posx, posy, width, height
# button_ax2.set_axes_locator(ip)
# Button(button_ax2, 'Click me 2')

button_ax = plt.axes([0.4, 0.5, 0.2, 0.075])  #posx, posy, width, height
Button(button_ax, 'Click me')

button_ax = plt.axes([0.1, 0.1, 0.2, 0.075])  #posx, posy, width, height
Button(button_ax, 'Click me')

plt.show()