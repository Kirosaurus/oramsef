import cv2
import numpy as np
import matplotlib.pyplot as plt

eyeCascade = cv2.CascadeClassifier("/cascade/haarcascade_eye.xml")
faceCascade = cv2.CascadeClassifier("/cascade/haarcascade_frontalface_default.xml")

def adjusted_detect_face(img):
    face_img = img.copy()
    face_rect = faceCascade.detectMultiScale(face_img, scaleFactor=1.2, minNeighbors=5)

    for (x, y, w, h) in face_rect:
        cv2.rectangle(face_img, (x, y), (x + w, y + h), (255, 255, 255), 10)

    return face_img

def detect_eyes(img):
    eye_img = img.copy()
    eye_rect = eyeCascade.detectMultiScale(eye_img, scaleFactor=1.2, minNeighbors=5)

    for (x, y, w, h) in eye_rect:
        cv2.rectangle(eye_img, (x, y), (x + w, y + h), (255, 255, 255), 10)
        
    return eye_img


cameraInit = cv2.VideoCapture(0)

while True :
    success, camera = cameraInit.read()
    cv2.imshow("Camera 1", camera)
    adjusted_detect_face(camera)
    if cv2.waitKey(1) & 0xFF == ord('q') :
        break