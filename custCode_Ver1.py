import cv2
import numpy as np
import fireStoreHandler as fs
import controlEsp32Cam as espcam
import argparse

def handleArgs():
    global URL
    global IP
    parser = argparse.ArgumentParser(description="Free parking spot identifier using image processing",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-c", "--cameraIP", action="store", help="camera module ip address")

    args = parser.parse_args()
    config = vars(args)

    #if the args has provided
    if config['cameraIP'] is not None:
        IP = "http://"+config['cameraIP']
        URL = 'http://' + config['cameraIP']+ ":81/stream"
    else:
        URL="http://192.168.1.3:81/stream" #if not args provided stay default
def setup():
    global cap
    # init firebase
    fs.init()

    # set resolution of the cam
    espcam.set_resolution(IP, index=10)
    # Face recognition and opencv setup
    try:
        cap = cv2.VideoCapture(URL)
    except Exception as e:
        print(f"Cannot find the camera feed:{e}")


def loop():
    global cap

    # x,y,width,height of the 6 rectangles
    rectanglesDict = {1: (80, 40, 250, 160),  # position 1
                      2: (80, 220, 250, 160),  # position 2
                      3: (75, 420, 250, 170),  # position 3
                      4: (510, 15, 250,160),  # position 4
                      5: (520,210, 250, 160),  # position 5
                       6: (540, 400, 250, 170)}  # position 6
    # after counting 100 times the average of the parking spots we send that to firebase

    count = 0
    total = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
    avgColorRect = {1:0,2:0,3:0,4:0,5:0,6:0}
    while True:

        if cap.isOpened():
            ret, frame = cap.read()

            if ret:
                # Convert the image to grayscale
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # blurr image to remove noise
                blured = cv2.medianBlur(gray, 5)

                for key ,(x, y, w, h) in rectanglesDict.items():
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2) #blue,green,red
                    #get avrage color inside the rectangle
                    roi = frame[y:y + h, x:x + w]
                    avg_color = np.asarray(cv2.mean(roi))
                    avg_color = round(np.sum(avg_color))

                    avgColorRect[key] = avg_color
                    cv2.putText(frame, f"{avg_color}", (x + 10, y + 50), cv2.FONT_HERSHEY_PLAIN, 1,
                                (255, 255, 255), 1, cv2.LINE_AA)
                    
                    freeList = []

                   

                        # Apply Hough circle detection to find circles in the image
                    circles = cv2.HoughCircles(blured, cv2.HOUGH_GRADIENT, 1, 10, param1=10, param2=34, minRadius=15,
                                                maxRadius=30)

                        

                    # If circles are found
                    if circles is not None:
                        # round the circle count
                        circles = np.round(circles[0, :]).astype("int")
                        # foreach circles center location and radius
                        for (x, y, r) in circles:

                            # above we have 6 rectangles with their positions as key stored inside a dictionary
                            for key, item in rectanglesDict.items():

                                # unbox the rectangle bounding box left top position x and y coordinates and width and
                                # height
                                (xr, yr, wr, hr) = item

                                # take rectangle position from the key
                                rectanglePosition = key

                                # if circle center is inside the rectangle bounding box we can take that
                                if xr < x < xr + wr and yr < y < yr + hr:
                                    
                                    
                                    #if average color is lower than the value that means it is free
                                    
                                    # if we can see the circle that means the space is empty
                                    cv2.rectangle(frame, (xr, yr), (xr + wr, yr + hr), (0, 255, 0), 2)

                                    # add that rectangle key which acts as the position to the free list
                                    freeList.append(key)

                                    # show text implementing the position
                                    cv2.putText(frame, f"position:={rectanglePosition}", (x, y - 30),
                                                cv2.FONT_HERSHEY_PLAIN, 1, (255, 255, 255), 1, cv2.LINE_AA)
                                    # show circle inside the frame
                                    cv2.circle(frame, (x, y), r, (0, 255, 0), 2)

                                    # show text inside the frame mentioning the x and y coordinates of the circle center
                                    cv2.putText(frame, f"x:={x},y={y}", (x, y + 30), cv2.FONT_HERSHEY_PLAIN, 1,
                                        (255, 255, 255), 1, cv2.LINE_AA)
                            
                                    

                                    
                    

                        freeSpotsCount = len(freeList)

                        # show text on the image that how many free spots are there
                        cv2.putText(frame, f"Free:={freeSpotsCount}", (100,750), cv2.FONT_HERSHEY_PLAIN, 5, (0, 255, 0), 1,
                                    cv2.LINE_AA)
                    # we count 100 times parking spots and average them before sending to fire base
                    if count < 100:
                        for value in freeList:
                            total[value] += 1
                        count+=1
                    else:
                        count = 0

                        for key, value in total.items():
                            if value > 50:
                                total[key] = 1
                            else:
                                total[key] = 0
                        # update the free positions to firebase
                        fs.writeFreeSpotsToDocs(total)

                        total = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}


            # show frame to the user
            cv2.imshow("Park Free spots", frame)
            key = cv2.waitKey(1)
    # destroy the frame showing window
    cv2.waitKey(0)
    cv2.destroyAllWindows()


if __name__ == "__main__":
    global cap
    global URL
    handleArgs()
    setup()
    loop()