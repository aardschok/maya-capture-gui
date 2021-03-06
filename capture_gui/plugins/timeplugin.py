import sys
import logging

import maya.OpenMaya as om
from capture_gui.vendor.Qt import QtCore, QtWidgets

import capture_gui.lib
import capture_gui.plugin

log = logging.getLogger("Time Range")


class TimePlugin(capture_gui.plugin.Plugin):
    """Widget for time based options"""

    id = "Time Range"
    section = "app"
    order = 30

    RangeTimeSlider = "Time Slider"
    RangeStartEnd = "Start/End"
    CurrentFrame = "CurrentFrame"

    def __init__(self, parent=None):
        super(TimePlugin, self).__init__(parent=parent)

        self._event_callbacks = list()

        self._layout = QtWidgets.QHBoxLayout()
        self._layout.setContentsMargins(5, 0, 5, 0)
        self.setLayout(self._layout)

        self.mode = QtWidgets.QComboBox()
        self.mode.addItems([self.RangeTimeSlider,
                            self.RangeStartEnd,
                            self.CurrentFrame])

        self.start = QtWidgets.QSpinBox()
        self.start.setRange(-sys.maxint, sys.maxint)
        self.end = QtWidgets.QSpinBox()
        self.end.setRange(-sys.maxint, sys.maxint)

        self._layout.addWidget(self.mode)
        self._layout.addWidget(self.start)
        self._layout.addWidget(self.end)

        self.on_mode_changed()  # force enabled state refresh

        self.mode.currentIndexChanged.connect(self.on_mode_changed)
        self.start.valueChanged.connect(self.on_mode_changed)
        self.end.valueChanged.connect(self.on_mode_changed)

    def on_mode_changed(self, emit=True):
        """
        Update the GUI when the user updated the time range or settings
        
        :param emit: Whether to emit the options changed signal
        :type emit: bool

        :return: None 
        """

        mode = self.mode.currentText()
        if mode == self.RangeTimeSlider:
            start, end = capture_gui.lib.get_time_slider_range()
            self.start.setEnabled(False)
            self.end.setEnabled(False)
            mode_values = int(start), int(end)
        elif mode == self.RangeStartEnd:
            self.start.setEnabled(True)
            self.end.setEnabled(True)
            mode_values = self.start.value(), self.end.value()
        else:
            self.start.setEnabled(False)
            self.end.setEnabled(False)
            mode_values = "({})".format(
                int(capture_gui.lib.get_current_frame()))

        # Update label
        self.label = "Time Range {}".format(mode_values)
        self.label_changed.emit(self.label)

        if emit:
            self.options_changed.emit()

    def get_outputs(self, panel=""):
        """
        Get the options of the Time Widget
        :param panel: 
        :return: the settings in a dictionary
        :rtype: dict
        """

        mode = self.mode.currentText()

        if mode == self.RangeTimeSlider:
            start, end = capture_gui.lib.get_time_slider_range()

        elif mode == self.RangeStartEnd:
            start = self.start.value()
            end = self.end.value()

        elif mode == self.CurrentFrame:
            frame = capture_gui.lib.get_current_frame()
            start = frame
            end = frame

        else:
            raise NotImplementedError("Unsupported time range mode: "
                                      "{0}".format(mode))

        return {"start_frame": start,
                "end_frame": end}

    def get_inputs(self, as_preset):
        return {"time": self.mode.currentText(),
                "start_frame": self.start.value(),
                "end_frame": self.end.value()}

    def apply_inputs(self, settings):
        # get values
        mode = self.mode.findText(settings.get("time", self.RangeTimeSlider))
        startframe = settings.get("start_frame", 1)
        endframe = settings.get("end_frame", 120)

        # set values
        self.mode.setCurrentIndex(mode)
        self.start.setValue(int(startframe))
        self.end.setValue(int(endframe))

    def initialize(self):
        self._register_callbacks()

    def uninitialize(self):
        self._remove_callbacks()

    def _register_callbacks(self):
        """
        Register callbacks to ensure Capture GUI reacts to changes in
        the Maya GUI in regards to time slider and current frame
        :return: None
        """

        callback = lambda x: self.on_mode_changed(emit=False)

        # this avoid overriding the ids on re-run
        currentframe = om.MEventMessage.addEventCallback("timeChanged",
                                                         callback)
        timerange = om.MEventMessage.addEventCallback("playbackRangeChanged",
                                                      callback)

        self._event_callbacks.append(currentframe)
        self._event_callbacks.append(timerange)

    def _remove_callbacks(self):
        """Remove callbacks when closing widget"""
        for callback in self._event_callbacks:
            try:
                om.MEventMessage.removeCallback(callback)
            except RuntimeError, error:
                log.error("Encounter error : {}".format(error))
