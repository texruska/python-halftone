from halftone import halftone_original

halftone_image_bytes = halftone_original.make(path="./examples/original.jpg")

with open("./examples/original_test.jpg", "wb") as f:
    f.write(halftone_image_bytes.getbuffer())
