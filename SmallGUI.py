#!/usr/bin/env python

import rospy
from std_msgs.msg import Float64
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool

from mavros_msgs.msg import State

import pygame
import sys
import time
import numpy as np

#color
RED 	= (250,  0,  0)
GREEN	= (  0,250,  0)
BLUE	= (  0,  0,255)
BLACK	= (  0,  0,  0)
WHITE	= (250,250,250)
GREY	= (175,175,175)

DARK_RED    = (175,  0,  0)
DARK_GREEN  = (  0,175,  0)
DARK_GREY   = (100,100,100)

LIGHT_GREY  = (200,200,200)

pygame.init()
controlWindowWidth  = 250
controlWindowHeight = 250
controlWindow = pygame.display.set_mode((controlWindowWidth,controlWindowHeight))
controlWindow.fill(GREY)

pygame.display.set_caption("Controller")

joystickWindowWidth = 150
joystickWindowHeight= 150
joystickMinBorder   = 50
joystickMaxBorder   = 200


#circle params
center=[controlWindowWidth/2,controlWindowHeight/2]
radius = 8

#tracking circle params
centerTrack=[controlWindowWidth/2,controlWindowHeight/2]
radiusTrack = 6

#line params
lineWidth = 3

run = True

vel_msg = Twist()
arm	= False
mavlinkArmed = False

def map(input, in_min, in_max, out_min, out_max):
	return (input - in_min)*(out_max-out_min)/(in_max-in_min)+out_min

def constraint(pos, min, max):
	posCalc = pos
	if pos > max: posCalc = max
	elif pos < min: posCalc = min

	return posCalc

class Text:
	def __init__(self, yourText, color, fontSize):
		self.myText = yourText
		self.textColor = color
		self.fontSize  = fontSize
		self.font = pygame.font.Font('freesansbold.ttf', self.fontSize)
		self.text = self.font.render(self.myText, True, self.textColor)
		self.textRect = self.text.get_rect()
		self.textRect.center = (controlWindowWidth/2,15)

	def drawText(self):
		controlWindow.blit(self.text, self.textRect)

	def setMyText(self, yourText):
		self.myText = yourText
		self.text = self.font.render(self.myText, True, self.textColor)
		self.textRect = self.text.get_rect()
		self.textRect.center = (controlWindowWidth/2,25)

	def setPos(self, xPos, yPos):
		self.textRect.center = (xPos,yPos)

class Slider:
	def __init__(self):
		self.color = LIGHT_GREY
		self.lineWidth = 2

		self.size = [30, 90]
		self.center = [controlWindowWidth/2, controlWindowHeight/2]
		self.datum = [200+self.size[0]/2, self.center[1]-self.size[1]/2]
		self.left  = self.datum[0]
		self.right = self.datum[0]+self.size[0]
		self.top   = self.datum[1]
		self.bottom= self.datum[1]+self.size[1]
		self.localCenterX = (self.left + self.right)/2

		self.sliderPosRad = 8
		self.sliderTop	  = self.top+10
		self.sliderBottom = self.bottom-10
		self.sliderPos	  = [self.localCenterX, self.sliderBottom]

	def drawSlider(self):
		pygame.draw.rect(controlWindow, self.color, (self.datum[0], self.datum[1], self.size[0], self.size[1]))
		pygame.draw.rect(controlWindow, BLACK, (self.datum[0], self.datum[1], self.size[0], self.size[1]), self.lineWidth)
		pygame.draw.line(controlWindow, BLACK, (self.localCenterX, self.sliderTop), (self.localCenterX, self.sliderBottom), self.lineWidth)
		pygame.draw.circle(controlWindow, RED  , (tuple(self.sliderPos)), self.sliderPosRad)

	def isInsideSlider(self, mousePos):
		xCond = self.left<mousePos[0]<self.right
		yCond =	self.top<mousePos[1]<self.bottom
		if(xCond and yCond):
			return True
		else: return False

	def isMoved(self, mousePos):
		tolerance = 4
		xCond = self.localCenterX-tolerance<mousePos[0]<self.localCenterX+tolerance
		yCond = self.sliderTop-tolerance<mousePos[1]<self.sliderBottom+tolerance

		if(xCond and yCond): return True
		else: return False

	def setColor(self, color):
		self.color = color

	def getValue(self):
		value = map(self.sliderPos[1], self.sliderBottom, self.sliderTop, 0, 100)
		return constraint(value, 0, 100)

class Button:
	def __init__(self, size, color, lineWidth):
		self.color = color
		self.lineWidth = lineWidth

		self.size = size
		self.center = [controlWindowWidth/2, controlWindowHeight/2]
		self.datum = [self.center[0]-self.size[0]/2, 200+self.size[1]/2]
		self.left  = self.datum[0]
		self.right = self.datum[0]+self.size[0]
		self.top   = self.datum[1]
		self.bottom= self.datum[1]+self.size[1]
		self.localCenter = [(self.left+self.right)/2, (self.top+self.bottom)/2]

		self.isArmed = False
		self.text = Text("Arm/Disarm", BLACK, 12)
		self.text.setPos(self.localCenter[0], self.localCenter[1])

	def drawBox(self):
		pygame.draw.rect(controlWindow, self.color, (self.datum[0], self.datum[1], self.size[0], self.size[1]))

	def drawBorder(self):
		pygame.draw.rect(controlWindow, BLACK, (self.datum[0], self.datum[1], self.size[0], self.size[1]), self.lineWidth)

	def isClicked(self, mousePosition):
		xCond = self.left<mousePosition[0]<self.right
		yCond =	self.top<mousePosition[1]<self.bottom
		if(xCond and yCond): return True
		else: return False

	def setColor(self, color):
		self.color = color

	def isInsideBox(self, mousePos):
		xCond = self.left<mousePos[0]<self.right
		yCond =	self.top<mousePos[1]<self.bottom
		if(xCond and yCond):
			return True
		else: return False

	def setIsArmed(self, cond):
		self.isArmed = cond

class joystickBackground:
	def __init__(self, width, height):
		self.size   = [width, height]
		self.center = [controlWindowWidth/2, controlWindowHeight/2]
		self.datum  = [(controlWindowWidth-width)/2, (controlWindowHeight-height)/2]

		self.left  = self.datum[0]
		self.right = self.datum[0]+self.size[0]
		self.top   = self.datum[1]
		self.bottom= self.datum[1]+self.size[1]

		self.color = BLACK
		self.backgroundColor = GREY
		self.lineWidth = 4

		self.lineColor = RED
		self.lineLength = 30

	def drawBackground(self):
		pygame.draw.rect(controlWindow, self.backgroundColor, (self.datum[0], self.datum[1], self.size[0], self.size[1]))

	def drawBorder(self):
		pygame.draw.rect(controlWindow, self.color, (self.datum[0], self.datum[1], self.size[0], self.size[1]), self.lineWidth)

	def drawMidLine(self):
		#vertical line
		pygame.draw.line(controlWindow, self.lineColor, (self.center[0], self.top), (self.center[0], self.top+self.lineLength), lineWidth)
		pygame.draw.line(controlWindow, self.lineColor, (self.center[0], self.bottom-self.lineLength), (self.center[0], self.bottom), lineWidth)
		pygame.draw.line(controlWindow, self.lineColor, (self.center[0], self.center[1]-self.lineLength/2), (self.center[0], self.center[1]+self.lineLength/2), lineWidth)

		#horizontal line
		pygame.draw.line(controlWindow, self.lineColor, (self.left, self.center[1]), (self.left+self.lineLength, self.center[1]), lineWidth)
		pygame.draw.line(controlWindow, self.lineColor, (self.right-self.lineLength, self.center[1]), (self.right, self.center[1]), lineWidth)
		pygame.draw.line(controlWindow, self.lineColor, (self.center[0]-self.lineLength/2, self.center[1]), (self.center[0]+self.lineLength/2, self.center[1]), lineWidth)

	def isInsideBox(self, mousePos):
		xCond = self.left<mousePos[0]<self.right
		yCond =	self.top<mousePos[1]<self.bottom
		if(xCond and yCond):
			return True
		else: return False

	def setColor(self, color):
		self.color = color

	def setBackgroundColor(self, color):
		self.backgroundColor = color

def drawBackground():
	joystick.drawBackground()
	joystick.drawMidLine()
	joystick.drawBorder()

	arming.drawBox()
	arming.text.drawText()

	armingText.drawText()

	screenSlider.drawSlider()
	#pygame.draw.circle(controlWindow, RED, (controlWindowWidth/2,controlWindowHeight/2), controlWindowWidth/2, lineWidth)

def drawOutputCircle():
	pygame.draw.circle(controlWindow, RED  , (center[0],center[1]), radius)

def drawTrackingCircle():
	pygame.draw.circle(controlWindow, BLACK, (centerTrack[0],centerTrack[1]), radiusTrack)
	pygame.draw.line  (controlWindow, BLACK, (controlWindowWidth/2, controlWindowHeight/2), (centerTrack[0], centerTrack[1]), 4)	

def drawToScreen():
	drawBackground()
	drawOutputCircle()
	drawTrackingCircle()

def globalToLocal(posX, posY):
	return posX-(controlWindowWidth-joystickWindowWidth)/2,  posY-(controlWindowHeight-joystickWindowHeight)/2

def transform(posX, posY):
	#transform from frame coordinate to "remote control" coordinate
	return posX-joystickWindowWidth, -(posY-joystickWindowHeight)

def subscriber():
	rospy.Subscriber("mavros/state", State, getState)

def getState(msg):
	global mavlinkArmed
	mavlinkArmed = msg.armed

#def disarm():
#	ropsy.wait_for_service('/mavros/cmd/arming')
#	try:
#		armService = rospy.ServiceProxy('/mavros/cmd/arming', CommandBool)
#		armResponse = armService(False)
#		rospy.loginfo(armResponse)
#	except rospy.ServiceException as e:
#		print("Service call failsed: %s" %e)

def display():
	pygame.time.delay(100)
	mousePos = pygame.mouse.get_pos()
	for e in pygame.event.get():
		if e.type == pygame.QUIT:
			run = False
			pygame.quit()
			sys.exit()
		if e.type == pygame.MOUSEBUTTONDOWN:
			if(joystick.isInsideBox(mousePos)):
				center[0] = mousePos[0]
				center[1] = mousePos[1]
				myPosX, myPosY = globalToLocal(center[0], center[1])
				myPosX, myPosY = transform(myPosX, myPosY)
				vel_msg.angular.z = myPosX
				vel_msg.linear.x = myPosY
			elif(arming.isClicked(mousePos)):
				if(not arming.isArmed):
					arming.setIsArmed(True)
					myPublisher.pubArm.publish(arming.isArmed)
				else:
					arming.setIsArmed(False)
					myPublisher.pubArm.publish(arming.isArmed)

			elif(screenSlider.isMoved(mousePos)):
				screenSlider.sliderPos[0] = screenSlider.localCenterX
				screenSlider.sliderPos[1] = mousePos[1]
				vel_msg.linear.z=screenSlider.getValue()

	if(joystick.isInsideBox(mousePos)):
		joystick.setBackgroundColor(WHITE)
		controlWindow.fill(DARK_GREY)
		centerTrack[0] = mousePos[0]
		centerTrack[1] = mousePos[1]
	else:
		joystick.setBackgroundColor(LIGHT_GREY)
		controlWindow.fill(WHITE)

	if(arming.isInsideBox(mousePos) and not arming.isArmed):
		arming.setColor(RED)
		arming.drawBorder()
	elif(arming.isInsideBox(mousePos) and arming.isArmed):
		arming.setColor(GREEN)
		arming.drawBorder()
	elif(not arming.isInsideBox(mousePos) and arming.isArmed):
		arming.setColor(DARK_GREEN)
	elif(not arming.isInsideBox(mousePos) and not arming.isArmed):
		arming.setColor(DARK_RED)

	if(screenSlider.isInsideSlider(mousePos)):
		screenSlider.setColor(WHITE)
		controlWindow.fill(DARK_GREY)
	else: screenSlider.setColor(LIGHT_GREY)

	if(mavlinkArmed): armingText.setMyText("Armed")
	elif(not mavlinkArmed):	armingText.setMyText("Disarmed")

	drawToScreen()
	pygame.display.update()

class publisher():
	def __init__(self):
		rospy.init_node('controller', anonymous = True)
		self.pubControl = rospy.Publisher('/positionControl', Twist, queue_size=1)
		self.pubArm     = rospy.Publisher('/armCommand'	, Bool , queue_size=1)

		vel_msg.linear.y = 0
		vel_msg.linear.z = 0
		vel_msg.angular.x = 0
		vel_msg.angular.y = 0


if __name__ == '__main__':
	arming = Button([80,30], DARK_RED, 3)
	joystick = joystickBackground(joystickWindowWidth, joystickWindowHeight)
	armingText = Text("Disarmed", RED, 25)
	screenSlider = Slider()
	subscriber()
	myPublisher = publisher()

	while not rospy.is_shutdown():
		display()
		myPublisher.pubControl.publish(vel_msg)

	rospy.on_shutdown(disarmRobot)
	rospy.spin()

###Below here are probably useful functions, "probably"

#def getDistance(posX, posY):
#	return np.sqrt(posX*posX + posY*posY)

#def maxPos(posX, posY):
#	radiusMax = 250
#
#	posX = posX - 250
#	posY = -(posY - 250)
#	middleX = controlWindowWidth/2 - 250
#	middleY = controlWindowHeight/2 - 250
#	angle = np.arctan2(middleY - posY, middleX - posX)

	#print(np.rad2deg(angle))
#	radiusReal = getDistance(posX,posY)
#
#	if (radiusReal > 250):
#		nowX = (-radiusMax * np.cos(angle)) +250
#		nowY = (-radiusMax * np.sin(angle)) - 250
#	else:
#		nowX = posX + 250
#		nowY = (posY -250)
#
#	return int(nowX), -int(nowY)
