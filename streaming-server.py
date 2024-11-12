from flask import Flask, Response
import win32gui
import mss
from PIL import Image
from io import BytesIO
import time

# Flask app initialization
app = Flask(__name__)

# This image is needed because screen capture removes cursor
# so the only way to get it back is to draw it
overlay_image = Image.open("cursor.png").convert("RGBA")

def capture_specific_monitor(monitor_number):
    '''
    Take screenshot of specific monitor using mss
    '''
    with mss.mss() as sct:
        if monitor_number < len(sct.monitors):
            mon = sct.monitors[monitor_number]
            monitor = {
                "top": mon["top"],
                "left": mon["left"],
                "width": mon["width"],
                "height": mon["height"],
                "include_cursor": True,
                "mon": monitor_number
            }
        else:
            raise ValueError("Invalid monitor number")
        screenshot = sct.grab(monitor)
        return screenshot

def generate():
    '''
    Prepare image to be sent over the network
    '''
    while True:
        try:
            # Select monitor here
            monitor_number = 1

            # Take a screenshot
            screenshot = capture_specific_monitor(monitor_number)
            
            # Convert the screenshot to PIL Image
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)

            # Calculate where to place cursor image
            flags, hcursor, (x,y) = win32gui.GetCursorInfo()
            with mss.mss() as sct:
                mon = sct.monitors[monitor_number]
                x -= mon['left']
                y -= mon['top']
            img.paste(overlay_image, (x, y), overlay_image)

            # Convert the image to JPEG format
            img_data = ''
            with BytesIO() as buffer:
                img.save(buffer, format="JPEG")
                img_data = buffer.getvalue()
                
            # Forming one frame data to be sent over the network
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + img_data + b'\r\n')

            FRAMES_PER_SECOND = 30
            time.sleep(1.0/FRAMES_PER_SECOND)

        except KeyboardInterrupt:
            print('Exception in generate')
            exit(2)
            
@app.route('/video_feed')
def video_feed():
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
        <title>Stream my screen</title>
    </head>
    <body>
        <img id="fullscreen-img" src="/video_feed" alt="Video Stream" style="cursor: pointer; width: 70%; height: auto">

        <script>
            // Get a reference to the img element
            var img = document.getElementById('fullscreen-img');

            // Function to toggle full screen mode for the img element
            function toggleFullScreen() {
                if (img.requestFullscreen) {
                    img.requestFullscreen();
                } else if (img.mozRequestFullScreen) { /* Firefox */
                    img.mozRequestFullScreen();
                } else if (img.webkitRequestFullscreen) { /* Chrome, Safari and Opera */
                    img.webkitRequestFullscreen();
                } else if (img.msRequestFullscreen) { /* IE/Edge */
                    img.msRequestFullscreen();
                }
            }

            // Attach the toggleFullScreen function to the click event of the img element
            img.addEventListener('click', toggleFullScreen);
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5123, debug=True)
