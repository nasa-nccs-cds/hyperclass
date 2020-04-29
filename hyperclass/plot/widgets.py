import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Rectangle, Ellipse
from matplotlib.widgets import AxesWidget
from matplotlib.text import Text

class ColoredRadioButtons(AxesWidget):
    """
    A GUI neutral radio button.

    For the buttons to remain responsive you must keep a reference to this
    object.

    Connect to the RadioButtons with the :meth:`on_clicked` method.

    Attributes
    ----------
    ax
        The containing `~.axes.Axes` instance.
    activecolor
        The color of the selected button.
    labels
        A list of `~.text.Text` instances containing the button labels.
    circles
        A list of `~.patches.Circle` instances defining the buttons.
    value_selected : str
        The label text of the currently selected button.
    """
    default_colors = [[0, 0, 1], [0, 1, 0], [1, 0, 0], [0, 1, 1], [1, 0, 1], [1, 1, 0], [0, 0, 0], [0, 0, .5], [0, .5, 0], [.5, 0, 0], [0, .5, .5], [.5, 0, .5],
                      [.5, .5, 0], [.5, .5, .5]]

    def __init__(self, ax, labels, active=0, colors=None ):
        """
        Add radio buttons to an `~.axes.Axes`.

        Parameters
        ----------
        ax : `~matplotlib.axes.Axes`
            The axes to add the buttons to.
        labels : list of str
            The button labels.
        active : int
            The index of the initially selected button.
        colors : list of [ r, g, b ]  where r,g,b -> (0,1)
            The colors of the buttons.
        """
        AxesWidget.__init__(self, ax)
        self.colors = colors if colors is not None else self.default_colors
        self.value_selected = None
        self.deactive_alpha = 0.2
        self.active_index = active

        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_navigate(False)
        dy = 1. / (len(labels) + 1)
        ys = np.linspace(1 - dy, dy, len(labels))
        cnt = 0

        # scale the radius of the circle with the spacing between each one
        circle_radius = dy / 2 - 0.01
        # default to hard-coded value if the radius becomes too large
        circle_radius = min(circle_radius, 0.05)

        self.labels = []
        self.circles = []
        for y, label in zip(ys, labels):
            t: Text  = ax.text(0.25, y, label, transform=ax.transAxes, horizontalalignment='left', verticalalignment='center')
            classcolor = self.colors[ cnt ]

            if cnt == active:
                self.value_selected = label
                facecolor = classcolor + [ 1 ]
                edgecolor = "black"
                t.set_fontweight( 'bold' )
            else:
                facecolor = classcolor + [ self.deactive_alpha ]
                edgecolor = "grey"
                t.set_fontweight( 'regular' )

            p = Circle(xy=(0.15, y), radius=circle_radius, edgecolor=edgecolor, facecolor=facecolor, transform=ax.transAxes)

            self.labels.append(t)
            self.circles.append(p)
            ax.add_patch(p)
            cnt += 1

        self.connect_event('button_press_event', self._clicked)

        self.cnt = 0
        self.observers = {}

    @property
    def activecolor(self):
        return self.colors[ self.active_index ]

    def _clicked(self, event):
        if self.ignore(event) or event.button != 1 or event.inaxes != self.ax:
            return
        pclicked = self.ax.transAxes.inverted().transform((event.x, event.y))
        distances = {}
        for i, (p, t) in enumerate(zip(self.circles, self.labels)):
            if (t.get_window_extent().contains(event.x, event.y) or np.linalg.norm(pclicked - p.center) < p.radius):
                distances[i] = np.linalg.norm(pclicked - p.center)
        if len(distances) > 0:
            closest = min(distances, key=distances.get)
            self.set_active(closest)

    def set_active(self, index):
        """
        Select button with number *index*.

        Callbacks will be triggered if :attr:`eventson` is True.
        """
        if 0 > index >= len(self.labels):
            raise ValueError("Invalid RadioButton index: %d" % index)

        self.value_selected = self.labels[index].get_text()
        self.active_index = index

        for i, p in enumerate(self.circles):
            classcolor = self.colors[i]
            t = self.labels[i]
            if i == index:
                color = classcolor + [ 1 ]
                p.set_facecolor(color)
                p.set_edgecolor( "black" )
                t.set_fontweight('bold')
            else:
                color = classcolor + [ self.deactive_alpha ]
                p.set_facecolor(color)
                p.set_edgecolor( "grey" )
                t.set_fontweight('regular')

        if self.drawon:
            self.ax.figure.canvas.draw()

        if not self.eventson:
            return
        for cid, func in self.observers.items():
            func(self.labels[index].get_text())

    def on_clicked(self, func):
        """
        Connect the callback function *func* to button click events.

        Returns a connection id, which can be used to disconnect the callback.
        """
        cid = self.cnt
        self.observers[cid] = func
        self.cnt += 1
        return cid

    def disconnect(self, cid):
        """Remove the observer with connection id *cid*."""
        try:
            del self.observers[cid]
        except KeyError:
            pass
