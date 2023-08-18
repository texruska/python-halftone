from halftone import halftone

halftone_image_bytes = halftone.make(path="./examples/original.jpg")

with open("./examples/original_test.jpg", "wb") as f:
    f.write(halftone_image_bytes.getbuffer())
