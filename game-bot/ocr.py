import easyocr

TEXT_DETECTION_THRESHOLD = 0.25

reader = easyocr.Reader(['en', 'la'], gpu=True, verbose=False)
