import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen
from PyQt5.QtCore import Qt, QTimer
import cv2
from ultralytics import YOLO
from datetime import datetime, timedelta
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import firebase_admin
from firebase_admin import credentials, storage
from firebase_admin import db
import concurrent.futures
from LoadReports import *
import pytz
from playsound import playsound
import threading
import pygame

class FYPCode(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Vision-Based Robbery Detection System")
        # Remove the initial fixed size setting
        self.setGeometry(100, 100, 1200, 800)  # Set your preferred initial size

        self.showMaximized()
        self.init_ui()
        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        # Initialize the YOLO model here
        self.model = YOLO("./best12.pt")
        # Initialize Pygame mixer

        # Initialize Pygame mixer in the main thread
        pygame.mixer.init()
        # Flag to indicate weapon detection
        self.weapon_detected = False
        self.alarm_playing = False
        self.alarm_lock = threading.Lock()
        self.is_crime_detected = False
        self.is_weapon_detected = False
        self.last_sent_time = ""
        self.do_need_to_play = False
        self.second_window = None  # Reference to the second window
        self.last_sent_time = datetime.now()

        # Apply background theme to widgets
        self.applyBackgroundTheme()

        cred = credentials.Certificate("crime-detection-2be57-firebase-adminsdk-8g2rj-9c5d3b1b87.json")
        firebase_admin.initialize_app(cred, {
            "storageBucket": "crime-detection-2be57.appspot.com",
            "databaseURL": "https://crime-detection-2be57-default-rtdb.firebaseio.com"

        }, name='main_apps')
        # })

    def init_ui(self):
        # Create main layout
        main_layout = QVBoxLayout(self)

        # Image label
        self.img_label = QLabel(self)
        self.img_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.img_label, 1)  # Adjust the stretch factor to allocate more space to the image view

        # Information label
        self.info_label = QLabel('Kindly Press "Show" to connect with the webcam.', self)
        self.info_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.info_label)

        # Buttons
        self.show_button = QPushButton('SHOW', self)
        self.capture_button = QPushButton('View Report', self)

        # Connect buttons to slots
        self.show_button.clicked.connect(self.on_show_clicked)
        self.capture_button.clicked.connect(self.open_report_window)

        # Add buttons to layout
        button_layout = QVBoxLayout()
        button_layout.addWidget(self.show_button)
        button_layout.addWidget(self.capture_button)
        main_layout.addLayout(button_layout)

        # Add a logout button
        self.logout_button = QPushButton('Logout', self)
        self.logout_button.clicked.connect(self.logout)

        # Add the logout button to the main layout
        main_layout.addWidget(self.logout_button)

        self.setLayout(main_layout)

    def logout(self):
        # Add your logout logic here
        # For example, you can close the current window and show a login window
        self.close()
        # login_window = LoginWindow()  # Replace with your login window class
        # login_window.show()

    def applyBackgroundTheme(self):
        theme_style = """
                     QLabel {
                         background-color: qlineargradient(spread:pad, x1:0, y1:0.505682, x2:1, y2:0.477, 
                                                         stop:0 rgba(20, 47, 78, 219), stop:1 rgba(85, 98, 112, 226));
                        color:rgba(255, 255, 255, 210);
                        border-radius:5px;
                     }
                     """
        self.setStyleSheet(theme_style)
    def on_show_clicked(self):
        # Open webcam
        # self.cap = cv2.VideoCapture("abc.mp4")
        self.cap = cv2.VideoCapture(0)
        self.timer.start(30)  # Update every 30 milliseconds

        # Maximize the window
        # self.showMaximized()

        # Disable resizing after maximizing
        # self.setFixedSize(self.size())

    def on_capture_clicked(self):
        # Capture and process the current frame (You can add your logic here)
        if self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                self.display_image(frame)
    def open_report_window(self):
        self.second_window = MainWindow()
        self.second_window.show()


    config_of_installation = {
            'camera_id': 0,
            'camera_source': 0,
            'camera_location_name': 'XYZ Bank',
            'bank_phone': '+92-3100-1111111',
            'address': {
                'street': '123 Main St',
                'city': 'Talagang',
                'state': 'Punjab'
            }
        }
    camera_list = [config_of_installation]

    def update_frame(self):
        alarm_thread = threading.Thread(target=self.alarm_thread)
        alarm_thread.start()
        # Read the current frame from the webcam and display it
        if self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                img, crime_detected, weapon_detected = self.detection(frame)
                status = crime_detected or weapon_detected
                self.do_need_to_play = status
                self.check_and_resend_email(status, frame)
                self.display_image(img)

    def play_alarm(self):
        global alarm_playing
        with self.alarm_lock:
            if not self.alarm_playing:
                print("Playing Alarm...")
                pygame.mixer.music.load("alert_2.mp3")  # Replace with the correct filename
                pygame.mixer.music.play()
                alarm_playing = True

    def alarm_thread(self):
        print("thread started 1")
        while True:
            print(f"thread started 2 {self.do_need_to_play}")
            if self.do_need_to_play:
                self.play_alarm()
            else:
                # Reset the alarm status when no crime is detected
                with self.alarm_lock:
                    self.alarm_playing = False

            # Sleep for a short interval to avoid continuous checking
            time.sleep(3)

    alarm_playing = False

    def check_and_resend_email(self, status, frame):
        if status:
            current_time = datetime.now()
            time_difference = current_time - self.last_sent_time

            # Check if the time difference is more than 2 minutes
            if time_difference > timedelta(seconds=10):
                self.upload_image(frame)
                self.last_sent_time = current_time
                print("Sent")
                # return current_time  # Update the last sent time
            else:
                print(f"Not enough time ({time_difference.total_seconds()}) has passed. No need to resend.")
    def display_image(self, frame):
        # Calculate the size to fit the image within the available space
        img_height, img_width, _ = frame.shape
        label_width = self.img_label.width()
        label_height = self.img_label.height()

        # Choose the scaling factor to fit the image within the label
        scale_factor_width = label_width / img_width
        scale_factor_height = label_height / img_height
        scale_factor = min(scale_factor_width, scale_factor_height)

        # Resize the image with the calculated scale factor
        resized_img = cv2.resize(frame, (int(img_width * scale_factor), int(img_height * scale_factor)))

        # Convert OpenCV image (BGR) to QImage
        height, width, channel = resized_img.shape
        bytes_per_line = 3 * width
        q_image = QImage(resized_img.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()

        # Convert QImage to QPixmap and display it
        pixmap = QPixmap.fromImage(q_image)
        self.img_label.setPixmap(pixmap)

    def upload_image(self, frame):
        def upload():
            encode_param = [cv2.IMWRITE_JPEG_QUALITY, 20]
            tagged_image1 = cv2.imencode('.jpg', frame, encode_param)[1]

            new_timestamp = datetime.now()
            filename = f"Image/{new_timestamp}.jpg"

            bucket = storage.bucket()
            blob = bucket.blob(filename)
            blob.upload_from_string(tagged_image1.tobytes(),
                                    content_type='image/jpeg')
            # Realtime database
            # Incident information

            #     ref1.child(timestamp).set({
            #         'filename': filename,
            #         'timestamp': timestamp
            #     })

            # if self.im == 0:
            url = blob.generate_signed_url(timedelta(minutes=60), method='GET')

            incident_info = {
                'camera_id': self.camera_list[0]['camera_id'],
                'incident_time': new_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'image_url': url,
                'bank_phone': self.camera_list[0]['bank_phone'],
                'address': self.camera_list[0]['address'],
                'incident_description': 'Suspicious activity detected',
                'additional_notes': 'No further details'
            }
            print(incident_info)
            incident_ref = db.reference(f"/incidents/{self.camera_list[0]['camera_id']}")
            incident_ref.push().set(incident_info)

            # ref = db.reference("users")
            # sender_email = ref.child("email").get()
            sender_email = "iffatxahra0@gmail.com"
            receiver_emails = ["sunnyabbas50999@gmail.com"]
            password = "cfoldelqyzrylvhp"
            # password = "mxwjsdljdeawiyde"

            # Create the MIME object
            message = MIMEMultipart()
            message["From"] = sender_email
            message["To"] = ", ".join(receiver_emails)
            message["Subject"] = "The Crime Detected"

            # Get the current time in the specified time zone
            timezone = pytz.timezone("Asia/Karachi")
            current_time = datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S %Z")

            # Create the HTML content for the email
            # Create the HTML content for the email
            html_content = f"""
            <html>
                <head>
                    <style>
                        body {{
                            font-family: 'Arial', sans-serif;
                            background-color: #f5f5f5;
                            margin: 0;
                            padding: 0;
                        }}
                        .container {{
                            max-width: 600px;
                            margin: 20px auto;
                            padding: 20px;
                            background-color: #fff;
                            border-radius: 8px;
                            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                        }}
                        h2 {{
                            color: #007BFF;
                            text-align: center;
                        }}
                        p {{
                            font-size: 16px;
                            line-height: 1.6;
                            margin-bottom: 15px;
                            text-align: left;
                        }}
                        strong {{
                            font-weight: bold;
                        }}
                        a {{
                            color: #007BFF;
                            text-decoration: none;
                        }}
                        a:hover {{
                            text-decoration: underline;
                        }}
                        .button {{
                            display: inline-block;
                            padding: 10px 20px;
                            background-color: #959696;
                            color: #fff;  /* Corrected property name from text to color */
                            text-decoration: none;
                            border-radius: 5px;
                            transition: background-color 0.3s;
                        }}
                        .button:hover {{
                            background-color: #455859;
                        }}
                       .footer {{
                margin-top: 20px;
                font-size: 0.9em;
                color: #777;
                text-align: center;
                border-top: 1px solid #ddd;
                padding-top: 10px;
            }}
            .footer a {{
                color: #455859;
                text-decoration: none;
                font-weight: bold;
            }}
            .footer a:hover {{
                color: #007BFF;
            }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h2>🚨 Crime Detection Alert</h2>
                        <p>Dear Police Station,</p>
                        <p>We have detected a potential crime incident at {self.config_of_installation['address']}.</p>
                        <p><strong>Crime Scene:</strong> Pakistan</p>
                        <p><strong>Incident Time (Asia/Karachi):</strong> {current_time}</p>
                        <p><strong>Local Authority Contact:</strong> {self.config_of_installation['bank_phone']}</p>

                        <p>You can view the details of the evidence by clicking the following button:</p>
                        <a class="button" href="{url}" target="_blank">View Evidence</a>
                        <p>We kindly request you to review the information at your earliest convenience.</p>
                        <div class="footer">
                            <p>For immediate assistance, contact: +92-311-1111111</p>
                            <p>Best regards,<br>Iffat Zahra</p>
                            <p class="privacy-notice">This message is intended for the designated recipient. Please be mindful of privacy and legal guidelines regarding this information.</p>
                        </div>
                    </div>
                </body>
            </html>
            """

            # Attach the HTML content to the message
            message.attach(MIMEText(html_content, "html"))

            # Attach an image or any other file if needed
            # attachment = open("path/to/your/image.jpg", "rb")
            # image_attachment = MIMEImage(attachment.read(), name="image.jpg")
            # attachment.close()
            # message.attach(image_attachment)

            # Set up the SMTP server
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(sender_email, password)
                server.sendmail(sender_email, receiver_emails, message.as_string())
            server.quit()

        # Use ThreadPoolExecutor for background execution
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(upload)

    def closeEvent(self, event):
        # Release the camera when the window is closed
        if self.cap and self.cap.isOpened():
            self.cap.release()

    def detection(self, image):
        results = self.model(image)
        self.is_crime_detected = False
        self.is_weapon_detected = False
        if len(results) > 0:
            for result in results:
                for object_data in result.boxes.data:
                    x0, y0, x1, y1, confi, clas = object_data

                    if confi > 0.4:
                        box = [int(x0), int(y0), int(x1 - x0), int(y1 - y0)]
                        box2 = [int(x0), int(y0), int(x1), int(y1)]
                        if clas == 0:
                            cv2.rectangle(image, box, (0, 0, 255), 1)

                            cv2.putText(image, "Criminal {:.2f}".format(confi), (box[0], box2[1] - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 1)
                            self.is_crime_detected = True
                        elif clas == 1:
                            cv2.rectangle(image, box, (255, 0, 0), 1)

                            cv2.putText(image, "Person {:.2f}".format(confi), (box[0], box2[1] - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 1)
                        elif clas == 2:
                            cv2.rectangle(image, box, (255, 255, 0), 1)

                            cv2.putText(image, "Weapon {:.2f}".format(confi), (box[0], box2[1] - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 1)
                            self.is_weapon_detected = True

        if self.is_crime_detected or self.is_weapon_detected:
            cv2.putText(image, "UnSafe Activity Detected", (10, 22), cv2.FONT_HERSHEY_SIMPLEX, .8, (255, 0, 0), 1)

        return image, self.is_crime_detected, self.is_weapon_detected

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FYPCode()
    window.show()
    sys.exit(app.exec_())
