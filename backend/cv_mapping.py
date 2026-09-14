"""
cv_mapping.py
-------------
The frontend runs a pretrained MobileNet (via TensorFlow.js, in-browser)
on the webcam / uploaded photo. MobileNet was trained on ImageNet's 1000
generic object classes, so it never says "Power Bank" - it says things
like "cellular telephone" or "pop bottle".

This table maps those generic, real-world CV labels (substring match,
case-insensitive) to the 25 specific items that exist in our campus
waste catalog. The backend /api/lookup endpoint uses this to translate
"what the camera saw" into "what bin it goes in".

Keys are lowercase substrings to look for in the raw model label.
Values are the exact `item` name as it appears in the items table.
"""

LABEL_TO_ITEM = {
    # IT Equipment
    "laptop": "Laptop",
    "notebook computer": "Laptop",
    "desktop computer": "Monitor",
    "screen": "Monitor",
    "monitor": "Monitor",
    "crt": "Monitor",
    "printer": "Printer",
    "tablet": "Tablet",
    "ipad": "Tablet",

    # Peripherals / small electronics
    "computer keyboard": "Keyboard",
    "keyboard": "Keyboard",
    "mouse": "Mouse",
    "web cam": "Webcam",
    "webcam": "Webcam",
    "remote control": "Remote Control",
    "joystick": "Remote Control",
    "cellular telephone": "Mobile",
    "mobile phone": "Mobile",
    "smartphone": "Mobile",
    "iphone": "Mobile",
    "headphone": "Headphones",
    "earphone": "Earphones",
    "ear bud": "Earphones",

    # Networking
    "modem": "Router",
    "router": "Router",

    # Battery / charging
    "power bank": "Power Bank",
    "battery": "Battery",
    "charger": "Charger",
    "ac adapter": "Charger",

    # Storage
    "hard disc": "Hard Drive",
    "hard drive": "Hard Drive",
    "disk drive": "Hard Drive",
    "usb": "USB Drive",
    "flash drive": "USB Drive",

    # Cables
    "cable": "Electric Cable",
    "wire": "Electric Cable",
    "extension cord": "Electric Cable",

    # Lighting
    "cfl": "CFL",
    "light bulb": "CFL",
    "fluorescent": "CFL",

    # Plastic / glass / metal / paper / general
    "water bottle": "Plastic Bottle",
    "pop bottle": "Plastic Bottle",
    "plastic bag": "Plastic Bottle",
    "beer bottle": "Glass Bottle",
    "wine bottle": "Glass Bottle",
    "glass": "Glass Bottle",
    "pop can": "Aluminium Can",
    "beer can": "Aluminium Can",
    "tin can": "Aluminium Can",
    "carton": "Cardboard",
    "cardboard": "Cardboard",
    "box": "Cardboard",
    "envelope": "Paper",
    "paper towel": "Paper",
    "notebook": "Paper",
    "menu": "Paper",
    "wrapper": "Food Wrapper",
    "packet": "Food Wrapper",
    "plastic wrap": "Food Wrapper",
}
