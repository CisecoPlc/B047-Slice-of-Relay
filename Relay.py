#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" B047 - Slice of Relay Example GUI
    Copyright (c) 2013 Ciseco Ltd.
    
    Author: Matt Lloyd
    
    This code is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
    
    """
import Tkinter as tk
import argparse
import wiringpi2
import serial
import threading
import Queue

class Relay:
    """Relay Gui Class
    """
    _disableGPIO = False
    _relayAIO = 24
    _relayBIO = 25

    _debug = False
    _debugArg = False
    _version = 0.01

    _widthMain = 450
    #    _heightMain = 300
    _widthOffset = 150
    _heightOffset = 150
    _rowHeight = 100
    _rows = 6
    
    _lowAImageFile = "lowA.gif"
    _highAImageFile = "highA.gif"
    _lowBImageFile = "lowB.gif"
    _highBImageFile = "highB.gif"
    
    # Serial bits
    _port = '/dev/ttyAMA0'
    _baudrate = 9600
    _devID = '--'
    _llapA = 'D02'
    _llapB = 'D03'
    _llapHigh = 'HIGH'
    _llapLow = 'LOW'
    
    def __init__(self):
        """Initilaize
        """
        self._heightMain = self._rowHeight * self._rows
    
    def _debugPrint(self, msg):
        if self._debugArg or self._debug:
            print(msg)

    def on_execute(self):
        self._checkArgs()
        self._initIO()
        self._initSerial()
        self._runGUI()
        self._cleanIO()
        self._cleanSerial()
    
    def _runGUI(self):
        self._debugPrint("Run GUI")
        self._master = tk.Tk()
        self._master.protocol("WM_DELETE_WINDOW", self._on_end)
        self._master.title("B047 - Slice of Relay v{}".format(self._version))
        self._master.resizable(0,0)
    
        self._displayRelay()
        
        # start serial
        self._processQueue()
        
        self._master.mainloop()

    def _displayRelay(self):
        self._debugPrint("Displaying Relay GUI")
        self._rFrame = tk.Frame(self._master, name='relayFrame', relief=tk.RAISED,
                                borderwidth=2, width=self._widthMain,
                                height=self._heightMain
                                )
        self._rFrame.pack()
    
        canvas = tk.Canvas(self._rFrame, bd=0, width=self._widthMain-4,
                           height=self._rowHeight/2, highlightthickness=0)
        canvas.grid(row=1, column=0, columnspan=6)
    
        tk.Button(self._rFrame, text='Quit', command=self._on_end
                  ).grid(row=self._rows-1, column=0, sticky=tk.E)
    
    
        self._relayACanvas = tk.Canvas(self._rFrame,
                                       width=(self._widthMain-4)/2,
                                       height=self._rowHeight,
                                       bd=0, relief=tk.FLAT, highlightthickness=0
                                       )
        self._relayACanvas.grid(row=1, column=0, columnspan=3, sticky=tk.W+tk.E+tk.N+tk.S)
        
        self._relayAPhotoimageLow = tk.PhotoImage(file=self._lowAImageFile)
        self._relayAPhotoimageHigh = tk.PhotoImage(file=self._highAImageFile)
        self._relayAimg = self._relayACanvas.create_image(0, 0, anchor=tk.NW, image=self._relayAPhotoimageLow)
        
        tk.Label(self._rFrame, text="G{}".format(self._relayAIO)).grid(row=1, column=3, sticky=tk.E)
        tk.Button(self._rFrame, text="1", command=lambda:self._relayOn(self._relayAIO)).grid(row=1, column=4)
        tk.Button(self._rFrame, text="2", command=lambda:self._relayOff(self._relayAIO)).grid(row=1, column=5, sticky=tk.W)
                          
        self._relayBCanvas = tk.Canvas(self._rFrame,
                                       width=(self._widthMain-4)/2,
                                       height=self._rowHeight,
                                       bd=0, relief=tk.FLAT, highlightthickness=0
                                       )
        self._relayBCanvas.grid(row=3, column=0, columnspan=3, sticky=tk.W+tk.E+tk.N+tk.S)
        
        self._relayBPhotoimageLow = tk.PhotoImage(file=self._lowBImageFile)
        self._relayBPhotoimageHigh = tk.PhotoImage(file=self._highBImageFile)
        self._relayBimg = self._relayBCanvas.create_image(0, 0, anchor=tk.NW, image=self._relayBPhotoimageLow)
        
        tk.Label(self._rFrame, text="G{}".format(self._relayBIO)).grid(row=3, column=3, sticky=tk.E)
        tk.Button(self._rFrame, text="1", command=lambda:self._relayOn(self._relayBIO)).grid(row=3, column=4)
        tk.Button(self._rFrame, text="2", command=lambda:self._relayOff(self._relayBIO)).grid(row=3, column=5, sticky=tk.W)

                          
    def _relayOn(self, pin):
        self._debugPrint("Relay {} On".format(pin))
        if pin == self._relayAIO:
            self._relayACanvas.itemconfigure(self._relayAimg, image=self._relayAPhotoimageHigh)
            wiringpi2.digitalWrite(self._relayAIO, 1)
        elif pin == self._relayBIO:
            self._relayBCanvas.itemconfigure(self._relayBimg, image=self._relayBPhotoimageHigh)
            wiringpi2.digitalWrite(self._relayBIO, 1)
            
    def _relayOff(self, pin):
        self._debugPrint("Relay {} Off".format(pin))
        if pin == self._relayAIO:
            self._relayACanvas.itemconfigure(self._relayAimg, image=self._relayAPhotoimageLow)
            wiringpi2.digitalWrite(self._relayAIO, 0)
        elif pin == self._relayBIO:
            self._relayBCanvas.itemconfigure(self._relayBimg, image=self._relayBPhotoimageLow)
            wiringpi2.digitalWrite(self._relayBIO, 0)

    def _on_end(self):
        self._debugPrint("Clean up GUI")
        self._master.destroy()

    def _initSerial(self):
        self._debugPrint("Strting Serial connection")
        self._sDisconnect = threading.Event()
        self._sQueue = Queue.Queue()
        self._sThread = threading.Thread(target=self._serialThread)
        self._s = serial.Serial()
        self._s.baudrate = self._baudrate
        self._s.port = self._port
        try:
            self._s.open()
            self._sThread.start()
        except serial.SerialException, e:
            self._debugPrint("Could not open port %r: %s\n" % (self._port, e))

    def _serialThread(self):
        while not self._sDisconnect.isSet():
            if self._s.isOpen():
                if self._s.inWaiting():
                    llapMsg = self._s.read()
                    if llapMsg == 'a':
                        llapMsg += self._s.read(11)
                        self._sQueue.put({'devID': llapMsg[1:3],
                                          'data': llapMsg[3:].rstrip("-")}
                                         )
                        self._debugPrint("Got LLAP {}".format(llapMsg))
            self._sDisconnect.wait(0.01)
        self._s.close()
    
    def _processQueue(self):
        while self._sQueue.qsize():
            msg = self._sQueue.get()
            if msg['devID'] == self._devID:
                if msg['data'][0:3] == self._llapA:
                    if msg['data'][3:] == self._llapHigh:
                        self._relayOn(self._relayAIO)
                    elif msg['data'][3:] == self._llapLow:
                        self._relayOff(self._relayAIO)
                elif msg['deta'][0:3] == self._llapB:
                    if msg['data'][3:] == self._llapHigh:
                        self._relayOn(self._relayBIO)
                    elif msg['data'][3:] == self._llapLow:
                        self._relayOff(self._relayBIO)
            self._sQueue.task_done()
        self._master.after(100, self._processQueue)

    def _cleanSerial():
        self._debugPrint("Clean up Serial")
        self._sDisconnect.set()
        self._serialThread.join()

    def _initIO(self):
        self._debugPrint("Init IO")
        wiringpi2.wiringPiSetupGpio()
        wiringpi2.pinMode(self._relayAIO, 1)
        wiringpi2.pinMode(self._relayBIO, 1)

    def _cleanIO(self):
        self._debugPrint("Clean up IO")

    def _checkArgs(self):
        self._debugPrint("Parse Args")
        parser = argparse.ArgumentParser(description='Slice of Relay GUI')
        parser.add_argument('-d', '--debug',
                            help='Extra Debug Output',
                            action='store_true'
                            )
        
        self._args = parser.parse_args()
        
        if self._args.debug:
            self._debugArg = True
        else:
            self._debugArg = False


if __name__ == "__main__":
    app = Relay()
    app.on_execute()
