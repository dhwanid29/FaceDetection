from deepface import DeepFace
import cv2
import pandas as pd
from google.colab.patches import cv2_imshow
out1 = DeepFace.verify("/content/modi1.jpg" , "/content/modi2.jpg")
out2 = DeepFace.verify("/content/modi1.jpg" , "/content/trump.jpg")
print(out1, "OUT 1")
x , y , w , h = out1["facial_areas"]["img1"].values()
print(x , y , w , h)

ig = cv2.imread("/content/modi1.jpg")
ig = cv2.rectangle(ig , (x , y) , (x + w , y + h) , (0 , 0 , 255) , 3)
cv2_imshow(ig)

out3 = DeepFace.find("/content/modi1.jpg" , "/content/fold")
print(out3[0])

